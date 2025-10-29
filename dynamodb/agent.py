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
                instruction=f"Use {stage_name}-{app_name}-frameworks table to scan and retrieve data. CRITICAL: Always use proper parameter binding in FilterExpression with ExpressionAttributeValues to avoid ValidationException errors. " + FRAMEWORKS_PROMPT,
                agent_type="",
                tools=[frameworks_mcp_toolset],
            )
    
    fusefy_controls_agent = create_sub_agent(
                    agent_name="Fusefy_Controls_Agent",
                    instruction=f"Use {stage_name}-{app_name}-controls table to scan and retrieve data. CRITICAL: Always use proper parameter binding in FilterExpression with ExpressionAttributeValues to avoid ValidationException errors. " + CONTROLS_PROMPT,
                    agent_type="",
                    tools=[controls_mcp_toolset],
    )
    
    fusefy_frameworkControls_agent = create_sub_agent(
                agent_name="Fusefy_FrameworkControls_Agent",
                instruction=f"""You are the Framework-Controls Mapping Specialist. Your PRIMARY table is {stage_name}-{app_name}-frameworkControls.

                4. Process for framework-control queries:
                - Step 1: SCAN {stage_name}-{app_name}-frameworkControls with proper FilterExpression
                - Step 2: Count results or extract controlId values
                - Step 3: If needed, reference other tables for details

                REMEMBER: You can only directly access the frameworkControls table. For framework or control details, you work with the controlId and frameworkId values you retrieve.

                """ + FRAMEWORKCONTROLS_PROMPT,
                agent_type="",
                tools=[frameworkControls_mcp_toolset],
    )

    
    
    return Agent( 
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