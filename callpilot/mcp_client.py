from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

DEFAULT_MCP_URL = "http://localhost:8000/mcp"


async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any], mcp_url: str = DEFAULT_MCP_URL) -> Dict[str, Any]:
    """
    Calls an MCP tool and returns structuredContent (JSON).
    """
    async with streamable_http_client(mcp_url) as (read_stream, write_stream, _):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            result = await session.call_tool(tool_name, arguments=arguments)
            # structuredContent is the JSON return from tools when json_response=True
            return result.structuredContent or {}
