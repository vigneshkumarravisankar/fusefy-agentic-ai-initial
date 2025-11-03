import json
import os
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
openai_key = os.getenv("OPENAI_API_KEY")

if not google_api_key:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")
if not aws_access_key:
    raise ValueError("AWS_ACCESS_ID environment variable is not set")
if not aws_secret_key:
    raise ValueError("AWS_SECRET_ACCESS_KEY environment variable is not set")
if not openai_key:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

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
def create_master_agent(stage_name: str, app_name: str, cloud_id: str) -> Agent:    
    # Configure MCP toolset
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
    
    return LlmAgent(
        name="Fusefy_Usecase_Generator_Agent",
        model=LiteLlm(model="openai/gpt-4o"),
        instruction=f"""
        You are an expert AI Usecase extractor and risk assessor for Fusefy.
        
        Use DynamoDB MCP in order to store the data in the tables. Follow till final process of uploading the usecase into the respective dynamodb table..

        Your goal:
        1. Accept an uploaded AI Usecase requirements document (PDF, DOCX, TXT).
        2. Read and understand the document content.
        4. Generate a structured JSON for the AI usecase in this exact format:
        {{
          "id": ""(analyze existing usecase ids, and frame incremental counter from those - starting with AI-UC-AST-00x(number)),
          "ai_approach": "",
          "ai_category": ""(as specified in the document - either Machine Learning/AI Workflow Agents/Agentic AI),
          "ai_cloud_provider": ""(either GCP/AWS/Azure based on the requirements),
          "AIMethodologyType": ""(AI Workflow Agents/Agentic AI),
          "baseModelName": ""(LLM Model Name),
          "businessUsage": ""(where exactly this usecase is used),
          "category": "AI Inventory(by default)",
          "cloudProvider": ""(GCP/AWS/Azure),
          "createdAt": ""(ISO Hash),
          "department": ""(the department where it is used - Real Estate/Human Resources/EdTech/Finance-team accordingly),
          "disableModelProcess":false(by default),
          "designDocument": "",
          "documentHash": "",
          "documentSummary": "",
          "impact": "",
          "jiraStoryId":"",
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
          "useFrequency": ""(frequent/continuous(24/7)/weekly/batch)
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

# Create the agent
root_agent = create_master_agent(
    stage_name="staging",
    app_name="fusefy",
    cloud_id="d66cb7c7-04ac-4634-927f-06d91afa39bf"
)