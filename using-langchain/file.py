from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
import asyncio
from langchain_google_genai import ChatGoogleGenerativeAI
import os


model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash"
)

server_params = StdioServerParameters(
    command="node",
                    args=[
                        "D:\\dev\\mcp\\dynamomcp\\dynamodb-mcp-server\\dist\\index.js"
                    ],
)

async def run_agent():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            tools = await load_mcp_tools(session)
            agent = create_react_agent(model, tools)
            agent_response = await agent.ainvoke({"messages": "Hi"})
            return agent_response

# Run the async function
if __name__ == "__main__":
    try:
        result = asyncio.run(run_agent())
        print(result)
    except:
        pass