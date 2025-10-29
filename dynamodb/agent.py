import json
import os 
from typing import Optional
from .mcp_toolsets.mcp_toolset import create_mcp_toolset

from google.adk.agents import Agent, LlmAgent, SequentialAgent, BaseAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.adk.models.lite_llm import LiteLlm
from .prompt import *
from .sub_agents.create_subagent import create_sub_agent

google_api_key = os.getenv("GOOGLE_API_KEY")
if google_api_key is None:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")

def create_master_agent(stage_name: str, app_name: str) -> Agent:
    frameworks_mcp_toolset = create_mcp_toolset(f"{stage_name}-{app_name}-frameworks")
    controls_mcp_toolset = create_mcp_toolset(f"{stage_name}-{app_name}-controls")
    frameworkControls_mcp_toolset = create_mcp_toolset(f"{stage_name}-{app_name}-frameworkControls")
               
    
    fusefy_frameworks_agent = create_sub_agent(
                agent_name="Fusefy_Frameworks_Agent",
                instruction=f"Use {stage_name}-{app_name}-frameworks table to scan and retrieve data." + FRAMEWORKS_PROMPT,
                agent_type="",
                tools=[frameworks_mcp_toolset],
            )
    
    fusefy_controls_agent = create_sub_agent(
                    agent_name="Fusefy_Controls_Agent",
                    instruction=f"Use {stage_name}-{app_name}-controls table to scan and retrieve data." + CONTROLS_PROMPT,
                    agent_type="",
                    tools=[controls_mcp_toolset],
    )
    
    fusefy_frameworkControls_agent = create_sub_agent(
                agent_name="Fusefy_FrameworkControls_Agent",
     instruction=f"""
               Strictly consider only {stage_name}-{app_name}-frameworks, {stage_name}-{app_name}-controls and {stage_name}-{app_name}-frameworkControls for your reference.
                
                """ + FRAMEWORKCONTROLS_PROMPT,
                agent_type="",
                tools=[frameworkControls_mcp_toolset],
    )

    
    
    return LlmAgent( 
        name="Fusefy_Root_Agent",
        model="gemini-2.5-flash",
        instruction= 
        DYNAMODB_PROMPT + 
        FUSEFY_GREETING + f"""
            Strictly consider only {stage_name}-{app_name}-frameworks, {stage_name}-{app_name}-controls and {stage_name}-{app_name}-frameworkControls for your reference.
        """,
        tools=[
            MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="node",
                    args=[
                        "D:\\dev\\mcp\\dynamomcp\\dynamodb-mcp-server\\dist\\index.js"
                    ],
                    env={
                        "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_ID"),
                        "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
                        "AWS_REGION": "us-east-1",
                    },
                )
            )
        )
        ]
    )
    
root_agent = create_master_agent("staging", "fusefy")