import json
import os
import hashlib
from typing import Optional
from datetime import datetime
from google.adk.agents import Agent, LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

# Environment validation
google_api_key = os.getenv("GOOGLE_API_KEY")
aws_access_key = os.getenv("AWS_ACCESS_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")

if not google_api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")
if not aws_access_key:
    raise ValueError("AWS_ACCESS_ID environment variable is not set")
if not aws_secret_key:
    raise ValueError("AWS_SECRET_ACCESS_KEY environment variable is not set")

# === DOCUMENT RISK GUIDANCE TEXT ===
DOCUMENT_RISK_GUIDANCE = """
DOCUMENT-BASED RISK ASSESSMENT CRITERIA:

LOW-RISK AI:
- Basic automation or efficiency improvements
- Limited data processing scope
- No personal/sensitive data involved
- Simple business process enhancement
- Minimal regulatory implications

MEDIUM-RISK AI:
- Moderate business process automation
- Some personal data processing
- Industry-specific compliance considerations
- Moderate technical complexity
- Potential for operational impact

HIGH-RISK AI:
- Critical business decision automation
- Extensive personal/sensitive data processing
- High regulatory compliance requirements (GDPR, HIPAA, financial regulations)
- Safety-critical applications
- Significant operational or financial impact
- Public-facing AI systems
- AI systems affecting individual rights or opportunities

PROHIBITED AI:
- Biometric identification in public spaces
- AI systems for social scoring
- Subliminal techniques to manipulate behavior
- Exploitation of vulnerabilities (age, disability)
- Real-time emotion recognition in workplace/education
"""

# === MAIN AGENT CREATOR ===
def create_master_agent(stage_name: str, app_name: str, cloud_id: str) -> tuple[Agent, MCPToolset]:
    """
    Returns both the agent and the toolset so you can properly clean up the session later
    """
    
    # Configure MCP toolset with error handling
    try:
        mcp_toolset = MCPToolset(
            connection_params=StdioConnectionParams(
                server_params=StdioServerParameters(
                    command="node",
                    args=[
                        "D:\\dev\\mcp\\dynamomcp\\dynamodb-mcp-server\\dist\\index.js"
                    ],
                    env={
                        "AWS_ACCESS_KEY_ID": os.getenv("AWS_ACCESS_ID"),
                        "AWS_SECRET_ACCESS_KEY": os.getenv("AWS_SECRET_ACCESS_KEY"),
                        "AWS_REGION": "us-east-1"
                    },
                )
            )
        )
    except Exception as e:
        print(f"Failed to initialize MCP toolset: {e}")
        raise
    
    # # Initialize the model properly
    # model = LiteLlm(
    #     model_name="gemini/gemini-2.0-flash-exp",
    #     api_key=google_api_key
    # )
    
    agent = LlmAgent(
        name="Fusefy_Usecase_Generator_Agent",
        model="gemini-2.5-flash",
        instruction=f"""
        You are an expert AI Usecase extractor and risk assessor for Fusefy.
        
        Use DynamoDB MCP to store data in tables. Follow the complete process of uploading the usecase into the respective DynamoDB table.

        Your goal:
        1. Accept an uploaded AI Usecase requirements document (PDF, DOCX, TXT).
        2. Read and understand the document content.
        3. Query existing usecases to determine the next incremental ID.
        4. Generate a structured JSON for the AI usecase in this exact format:
        {{
          "id": "(analyze existing usecase ids, and frame incremental counter from those)",
          "ai_approach": "",
          "ai_category": "",
          "ai_cloud_provider": "(either GCP/AWS/Azure based on the requirements)",
          "AIMethodologyType": "",
          "baseModelName": "",
          "businessUsage": "",
          "category": "",
          "cloudProvider": "",
          "createdAt": "",
          "department": "",
          "designDocument": "",
          "documentHash": "",
          "documentSummary": "",
          "impact": "",
          "isProposalGenerated": false,
          "keyActivity": "",
          "level": 0,
          "metrics": [],
          "modelDescription": "",
          "modelInput": "",
          "modelName": "",
          "modelOutput": "",
          "modelPurpose": "",
          "modelSummary": "",
          "modelUsage": "",
          "overallRisk": "",
          "platform": "",
          "priorityType": "",
          "processingStatus": "",
          "questions": [],
          "riskframeworkid": "",
          "searchAttributesAsJson": "",
          "sector": "",
          "sourceDocURL": "",
          "status": "",
          "updatedAt": "",
          "usecaseCategory": "",
          "useFrequency": "(frequent/continuous(24/7)/weekly/batch)"
        }}

        Then:
        - Use the following guidance to classify the overallRisk:
        {DOCUMENT_RISK_GUIDANCE}

        Rules for Risk Evaluation:
        - Determine the most fitting category (LOW, MEDIUM, HIGH, or PROHIBITED)
          based on document context (AI type, sensitivity, scope, compliance impact).
        - Provide clear reasoning for the risk classification.

        Finally:
        - Generate a unique documentHash using the document content
        - Add the documentSummary (3-5 sentence summary)
        - Add timestamps for 'createdAt' and 'updatedAt' in ISO 8601 format
        - Store the final structured JSON object into the DynamoDB table:
          {stage_name}-{app_name}-usecaseAssessments-{cloud_id}

        Always respond with the generated JSON and confirmation of storage.
        """,
        tools=[mcp_toolset]
    )
    
    return agent, mcp_toolset

# Usage example with proper cleanup:
def run_agent_with_cleanup(stage_name: str, app_name: str, cloud_id: str, query: str):
    agent = None
    mcp_toolset = None
    
    try:
        agent, mcp_toolset = create_master_agent(stage_name, app_name, cloud_id)
        response = agent.run(query)
        return response
    except Exception as e:
        print(f"Error running agent: {e}")
        raise
    finally:
        # Cleanup MCP session
        if mcp_toolset:
            try:
                # Close the MCP session properly
                if hasattr(mcp_toolset, 'cleanup') or hasattr(mcp_toolset, 'close'):
                    mcp_toolset.cleanup() if hasattr(mcp_toolset, 'cleanup') else mcp_toolset.close()
            except Exception as cleanup_error:
                print(f"Warning: Error during MCP cleanup: {cleanup_error}")