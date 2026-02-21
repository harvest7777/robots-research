import pytest
from fastmcp import Client
from mcp_server.server import mcp


@pytest.fixture
async def client():
    async with Client(mcp) as c:
        yield c


async def test_ping(client):
    result = await client.call_tool("ping", {})
    assert result[0].text == "pong"


async def test_hello(client):
    result = await client.call_tool("hello", {"name": "world"})
    assert result[0].text == "Hello, world!"


async def test_tools_are_listed(client):
    tools = await client.list_tools()
    names = [t.name for t in tools]
    assert "ping" in names
    assert "hello" in names
