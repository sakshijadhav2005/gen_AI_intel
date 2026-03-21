import asyncio
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from typing import Optional

async def scrape_url_mcp(url: str) -> str:
    # Use npx to run the fetch MCP server
    # The server expects to be run with `npx @modelcontextprotocol/server-fetch`
    server_params = StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-fetch"],
        env=None
    )

    try:
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                # Initialize the connection
                await session.initialize()

                # The fetch MCP provides a tool named "fetch"
                # Call it with the URL argument
                result = await session.call_tool("fetch", arguments={"url": url})

                if result.isError:
                     raise Exception(f"MCP Tool Error: {result}")

                # Result usually contains 'content' which is a list of text/image objects
                text_content = ""
                for content_block in result.content:
                    if content_block.type == "text":
                        text_content += content_block.text + "\n"

                return text_content.strip()
    except Exception as e:
        print(f"MCP Scraping Error: {e}")
        raise e
