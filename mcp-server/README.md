# Docker Port Hub MCP

Standalone read-only MCP server for Docker and Ubuntu host port allocation.
It does not depend on or modify the existing Flask backend and frontend.

## Tools

- `check_port`: check one TCP or UDP host port.
- `list_port_allocations`: list occupied ports and their owners.
- `find_free_ports`: find multiple currently unused ports.
- `get_unused_port`: return one unused port, optionally preferring a port.

An available port is a recommendation, not a reservation. Check again before use.

## Run with Docker

```bash
cd mcp-server
docker compose up -d --build
```

Default endpoint: `http://127.0.0.1:38083/mcp`.

The container uses host networking to read Ubuntu TCP/UDP listeners and mounts
the Docker socket to identify published container ports. The service code only
performs a Docker Engine GET request, but a read-only filesystem mount does not
make the Docker API itself read-only. Treat access to this container as
root-equivalent access to the Docker host. For remote
clients, keep the default loopback binding and use an SSH tunnel:

```bash
ssh -L 38083:127.0.0.1:38083 user@your-server
```

## Test

```bash
python -m unittest discover -s tests -v
```

Do not expose this MCP endpoint directly to the public Internet.
