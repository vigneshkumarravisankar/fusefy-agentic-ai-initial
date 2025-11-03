from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
import os

async def run_client():
        server_params = StdioServerParameters(
            command="node",
            args=[
                "D:\\dev\\mcp\\dynamomcp\\dynamodb-mcp-server\\dist\\index.js"
            ],
        )
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                # Interact with prompts, resources, and tools
                tools = await session.list_tools()
                print(f"Available tools: {tools}")
                
                # with open("tools.txt","w") as f:
                #     f.write(str(tools))
                result = await session.call_tool("create_table", arguments={"expression": "Hi"})
                # print(f"Expression result: {result}")

if __name__ == "__main__":
        asyncio.run(run_client())