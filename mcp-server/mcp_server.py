"""Standalone MCP server for Docker and Ubuntu host port allocation."""

from __future__ import annotations

import os
from typing import Any

from mcp.server.mcpserver import MCPServer

from port_detector import PortDetector

DEFAULT_START = int(os.environ.get("PORT_RANGE_START", "38080"))
DEFAULT_END = int(os.environ.get("PORT_RANGE_END", "38579"))

mcp = MCPServer(
    "Docker Port Hub MCP",
    instructions=(
        "Read-only tools for checking Docker/Ubuntu host port allocations and "
        "recommending currently unused ports. Recommendations are not reservations."
    ),
)
detector = PortDetector(
    docker_socket=os.environ.get("DOCKER_SOCKET", "/var/run/docker.sock"),
    proc_root=os.environ.get("PROC_ROOT", "/proc"),
)


@mcp.tool()
def check_port(port: int, protocol: str = "tcp") -> dict[str, Any]:
    """Check whether one TCP or UDP host port is currently unoccupied."""
    return detector.check(port, protocol)


@mcp.tool()
def list_port_allocations(
    start: int = DEFAULT_START,
    end: int = DEFAULT_END,
) -> dict[str, Any]:
    """List occupied Docker/Ubuntu host ports within an inclusive range."""
    detector.validate_port(start)
    detector.validate_port(end)
    if start > end:
        raise ValueError("start must be less than or equal to end")
    if end - start > 10000:
        raise ValueError("range cannot contain more than 10001 ports")
    allocations = detector.allocations()
    items = [
        {
            "port": port,
            "owners": [owner.as_dict() for owner in allocations[port]],
        }
        for port in sorted(port for port in allocations if start <= port <= end)
    ]
    return {
        "start": start,
        "end": end,
        "count": len(items),
        "allocations": items,
    }


@mcp.tool()
def find_free_ports(
    start: int = DEFAULT_START,
    end: int = DEFAULT_END,
    count: int = 5,
    protocol: str = "tcp",
) -> dict[str, Any]:
    """Find one or more currently unused ports in an inclusive range."""
    ports = detector.find_free(start, end, count, protocol)
    return {
        "protocol": protocol.lower(),
        "start": start,
        "end": end,
        "requested": count,
        "ports": ports,
        "warning": "Ports are recommendations, not reservations; recheck before use.",
    }


@mcp.tool()
def get_unused_port(
    preferred: int | None = None,
    start: int = DEFAULT_START,
    end: int = DEFAULT_END,
    protocol: str = "tcp",
) -> dict[str, Any]:
    """Return one unused port, preferring a requested port when available."""
    protocol = detector.validate_protocol(protocol)
    if preferred is not None and detector.check(preferred, protocol)["available"]:
        return {
            "port": preferred,
            "protocol": protocol,
            "preferred": True,
            "warning": "This port is not reserved; recheck before use.",
        }
    ports = detector.find_free(start, end, 1, protocol)
    return {
        "port": ports[0] if ports else None,
        "protocol": protocol,
        "preferred": False,
        "requested_preferred": preferred,
        "warning": "This port is not reserved; recheck before use.",
    }


if __name__ == "__main__":
    transport = os.environ.get("MCP_TRANSPORT", "streamable-http")
    if transport not in {"stdio", "streamable-http"}:
        raise ValueError("MCP_TRANSPORT must be stdio or streamable-http")
    if transport == "stdio":
        mcp.run()
    else:
        mcp.run(
            transport="streamable-http",
            host=os.environ.get("MCP_HOST", "127.0.0.1"),
            port=int(os.environ.get("MCP_PORT", "38083")),
            streamable_http_path="/mcp",
            stateless_http=True,
            json_response=True,
        )
