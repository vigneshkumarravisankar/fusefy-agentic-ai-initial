from google.adk.agents import LlmAgent, SequentialAgent, BaseAgent, Agent
import os
from google.adk.models.lite_llm import LiteLlm
from typing import List


def create_sub_agent(agent_name:str, instruction:str, tools: List, agent_type: str, sub_agents=List) -> LlmAgent:
        return LlmAgent(
            name=f"{agent_name}",
            model=LiteLlm(model="openai/gpt-4o"),
            instruction=f"{instruction}",
            tools=tools,
        )