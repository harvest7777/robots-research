"""
Run the LLM robot coordinator against the MCP server.

Usage:
    python -m llm.run
"""

import asyncio
import sys

from mcp import ClientSession
from mcp.client.stdio import StdioServerParameters, stdio_client

from llm.mcp_client import MCPClient
from llm.providers.anthropic import AnthropicProvider
from llm.session import Session


async def main() -> None:
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", "mcp_server.server"],
    )

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as mcp_session:
            await mcp_session.initialize()

            mcp = MCPClient(mcp_session)
            provider = AnthropicProvider()  # swap provider here to change LLMs
            session = Session(provider=provider, mcp=mcp)

            print("Robot coordinator ready. Ctrl-C or type 'quit' to exit.\n")

            while True:
                try:
                    user_input = input("You: ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    break

                if not user_input or user_input.lower() == "quit":
                    break

                response = await session.send(user_input)
                print(f"Assistant: {response}\n")


if __name__ == "__main__":
    asyncio.run(main())
