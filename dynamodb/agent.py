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

openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key is None:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

def create_master_agent(stage_name: str, app_name: str) -> Agent:
    frameworks_mcp_toolset = create_mcp_toolset(f"{stage_name}-{app_name}-frameworks")
    controls_mcp_toolset = create_mcp_toolset(f"{stage_name}-{app_name}-controls")
    frameworkControls_mcp_toolset = create_mcp_toolset(f"{stage_name}-{app_name}-frameworkControls")
    
    
    fusefy_frameworks_agent = create_sub_agent(
                agent_name="Fusefy_Frameworks_Agent",
                model_name="openai/gpt-4o",
                instruction=f"Use {stage_name}-{app_name}-frameworks table to scan and retrieve datas" + FRAMEWORKS_PROMPT,
                agent_type="",
                tools=[frameworks_mcp_toolset],
            )
    
    fusefy_controls_agent = create_sub_agent(
                    agent_name="Fusefy_Controls_Prompt",
                    model_name="openai/gpt-4o",
                    instruction=f"Use {stage_name}-{app_name}-controls table to scan and retrieve datas" + CONTROLS_PROMPT,
                    agent_type="",
                    tools=[controls_mcp_toolset],
    )
    
    fusefy_frameworkControls_agent = create_sub_agent(
                agent_name="Fusefy_FrameworkControls_Agent",
                model_name="openai/gpt-4o",
                instruction=f"Use {stage_name}-{app_name}-frameworkControls first to check both the frameworkId and controlId. To check the framework related details, with the frameworkId from the {stage_name}-{app_name}-frameworkControls, refer to the {stage_name}-{app_name}-frameworks and for the matched controlIds in with this frameworkId, refer to controls table({stage_name}-{app_name}-controls) for control specific details. " + FRAMEWORKCONTROLS_PROMPT,
                agent_type="",
                tools=[frameworkControls_mcp_toolset],
    )

    
    
    return LlmAgent( 
        name="Fusefy_Root_Agent",
        model=LiteLlm(model="openai/gpt-4o"),
        instruction= DYNAMODB_PROMPT + FUSEFY_GREETING,
        sub_agents=[
            fusefy_frameworks_agent,
            fusefy_controls_agent,
            fusefy_frameworkControls_agent
        ]    
    )
    
root_agent = create_master_agent("staging", "fusefy")