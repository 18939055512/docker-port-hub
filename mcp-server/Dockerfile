FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY mcp_server.py port_detector.py ./

ENV MCP_TRANSPORT=streamable-http \
    MCP_HOST=127.0.0.1 \
    MCP_PORT=38083 \
    PORT_RANGE_START=38080 \
    PORT_RANGE_END=38579

EXPOSE 38083
CMD ["python", "mcp_server.py"]
