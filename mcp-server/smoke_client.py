"""Connect to a running MCP server and list its tools."""

import anyio
from mcp.client import Client


async def main() -> None:
    async with Client("http://127.0.0.1:38083/mcp") as client:
        tools = await client.list_tools()
        print([tool.name for tool in tools.tools])
        result = await client.call_tool(
            "get_unused_port",
            {"start": 38080, "end": 38085, "protocol": "tcp"},
        )
        print(result.structured_content)


if __name__ == "__main__":
    anyio.run(main)
