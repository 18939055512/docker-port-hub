"""Read-only Docker and Linux host port allocation detection."""

from __future__ import annotations

import http.client
import json
import os
import socket
from dataclasses import dataclass
from typing import Any, Iterable

VALID_PROTOCOLS = {"tcp", "udp"}


class UnixHTTPConnection(http.client.HTTPConnection):
    """Minimal HTTP client for the Docker Engine Unix socket."""

    def __init__(self, socket_path: str, timeout: float = 5.0):
        super().__init__("localhost", timeout=timeout)
        self.socket_path = socket_path

    def connect(self) -> None:
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        self.sock.settimeout(self.timeout)
        self.sock.connect(self.socket_path)


@dataclass(frozen=True)
class PortOwner:
    source: str
    protocol: str
    name: str = ""
    image: str = ""
    private_port: int | None = None
    bind_ip: str = ""

    def as_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {"source": self.source, "protocol": self.protocol}
        for key in ("name", "image", "bind_ip"):
            value = getattr(self, key)
            if value:
                result[key] = value
        if self.private_port is not None:
            result["private_port"] = self.private_port
        return result


class DockerSocketClient:
    def __init__(self, socket_path: str = "/var/run/docker.sock"):
        self.socket_path = socket_path

    def list_port_owners(self) -> dict[int, list[PortOwner]]:
        if not os.path.exists(self.socket_path):
            return {}
        connection = UnixHTTPConnection(self.socket_path)
        try:
            connection.request("GET", "/v1.41/containers/json")
            response = connection.getresponse()
            body = response.read()
            if response.status != 200:
                raise RuntimeError(f"Docker API returned HTTP {response.status}")
            containers = json.loads(body)
        finally:
            connection.close()

        owners: dict[int, list[PortOwner]] = {}
        for container in containers:
            names = container.get("Names") or []
            name = names[0].lstrip("/") if names else container.get("Id", "")[:12]
            for mapping in container.get("Ports") or []:
                public_port = mapping.get("PublicPort")
                private_port = mapping.get("PrivatePort")
                protocol = str(mapping.get("Type", "tcp")).lower()
                if not public_port or protocol not in VALID_PROTOCOLS:
                    continue
                owner = PortOwner(
                    source="docker",
                    protocol=protocol,
                    name=name,
                    image=container.get("Image", ""),
                    private_port=int(private_port) if private_port is not None else None,
                    bind_ip=str(mapping.get("IP", "")),
                )
                bucket = owners.setdefault(int(public_port), [])
                if owner not in bucket:
                    bucket.append(owner)
        return owners


def parse_proc_net(lines: Iterable[str], protocol: str) -> dict[int, list[PortOwner]]:
    """Parse /proc/net/{tcp,tcp6,udp,udp6} rows."""
    owners: dict[int, list[PortOwner]] = {}
    for line in lines:
        fields = line.split()
        if len(fields) < 4 or fields[0] == "sl":
            continue
        try:
            port = int(fields[1].rsplit(":", 1)[1], 16)
            state = fields[3]
        except (IndexError, ValueError):
            continue
        if protocol == "tcp" and state != "0A":
            continue
        if protocol == "udp" and state not in {"07", "0A"}:
            continue
        owner = PortOwner(source="host", protocol=protocol)
        bucket = owners.setdefault(port, [])
        if owner not in bucket:
            bucket.append(owner)
    return owners


class PortDetector:
    PROC_FILES = {
        "tcp": ("net/tcp", "net/tcp6"),
        "udp": ("net/udp", "net/udp6"),
    }

    def __init__(
        self,
        docker_socket: str = "/var/run/docker.sock",
        proc_root: str = "/proc",
    ):
        self.docker = DockerSocketClient(docker_socket)
        self.proc_root = proc_root

    def allocations(self) -> dict[int, list[PortOwner]]:
        result = self.docker.list_port_owners()
        for protocol, paths in self.PROC_FILES.items():
            for relative_path in paths:
                try:
                    with open(
                        os.path.join(self.proc_root, relative_path),
                        "r",
                        encoding="ascii",
                        errors="replace",
                    ) as handle:
                        detected = parse_proc_net(handle, protocol)
                except OSError:
                    continue
                for port, owners in detected.items():
                    bucket = result.setdefault(port, [])
                    for owner in owners:
                        if owner not in bucket:
                            bucket.append(owner)
        return result

    @staticmethod
    def validate_port(port: int) -> int:
        if not 1 <= port <= 65535:
            raise ValueError("port must be between 1 and 65535")
        return port

    @staticmethod
    def validate_protocol(protocol: str) -> str:
        normalized = protocol.lower()
        if normalized not in VALID_PROTOCOLS:
            raise ValueError("protocol must be tcp or udp")
        return normalized

    def check(self, port: int, protocol: str = "tcp") -> dict[str, Any]:
        port = self.validate_port(port)
        protocol = self.validate_protocol(protocol)
        owners = [
            owner.as_dict()
            for owner in self.allocations().get(port, [])
            if owner.protocol == protocol
        ]
        return {
            "port": port,
            "protocol": protocol,
            "available": not owners,
            "owners": owners,
        }

    def find_free(
        self,
        start: int,
        end: int,
        count: int = 1,
        protocol: str = "tcp",
    ) -> list[int]:
        start = self.validate_port(start)
        end = self.validate_port(end)
        protocol = self.validate_protocol(protocol)
        if start > end:
            raise ValueError("start must be less than or equal to end")
        if not 1 <= count <= 100:
            raise ValueError("count must be between 1 and 100")
        allocations = self.allocations()
        free: list[int] = []
        for port in range(start, end + 1):
            if not any(
                owner.protocol == protocol for owner in allocations.get(port, [])
            ):
                free.append(port)
                if len(free) == count:
                    break
        return free
