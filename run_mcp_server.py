"""
CallPilot - MCP Server Entry Point
Run this file to start the MCP server for CallPilot tools
"""

import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from callpilot.mcp_server import mcp

if __name__ == "__main__":
    # Start the MCP server with streamable HTTP transport
    print("🚀 Starting CallPilot MCP Server at http://localhost:8000/mcp")
    mcp.run(transport="streamable-http")
