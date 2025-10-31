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

# === DYNAMODB QUERY BEST PRACTICES ===
DYNAMODB_QUERY_BEST_PRACTICES = """
**🔧 DynamoDB Query Best Practices - CRITICAL FOR SUCCESS**

**Parameter Binding Rules (MUST FOLLOW):**
1. NEVER use direct values in FilterExpression - always use placeholders
2. ALWAYS provide ExpressionAttributeValues for every placeholder
3. Use ExpressionAttributeNames for reserved keywords

**Correct Examples:**
✅ FilterExpression="id = :itemId", ExpressionAttributeValues={":itemId": "UC-001"}
✅ FilterExpression="contains(#name, :searchTerm)", ExpressionAttributeNames={"#name": "name"}, ExpressionAttributeValues={":searchTerm": "AI"}
✅ FilterExpression="overallRisk = :risk", ExpressionAttributeValues={":risk": "HIGH-RISK AI"}

**WRONG Examples (Will cause ValidationException):**
❌ FilterExpression="id = 'UC-001'" (missing parameter binding)
❌ FilterExpression="id = :itemId" (missing ExpressionAttributeValues)
❌ FilterExpression="name = AI" (missing quotes and parameter binding)

**Common Operations:**
- Exact match: attribute = :value
- Contains search: contains(attribute, :searchTerm)
- Multiple conditions: attribute1 = :val1 AND attribute2 = :val2
- Array contains: contains(arrayAttribute, :element)

**Reserved Keywords requiring ExpressionAttributeNames:**
- name, status, level, count, category (use #name, #status, etc.)
"""

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
                        "AWS_REGION": "us-east-1",
                        "DDB_MCP_READONLY": "false",  # Allow write operations
                        "PRIMARY_TABLE": f"{stage_name}-{app_name}-usecaseAssessments-{cloud_id}",
                        "MCP_TIMEOUT": "60",
                        "CONNECTION_TIMEOUT": "10"
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
        
        **CRITICAL DynamoDB Query Guidelines:**
        - When using FilterExpression, ALWAYS include ExpressionAttributeValues for parameter binding
        - Example: FilterExpression="id = :itemId", ExpressionAttributeValues={{":itemId": "UC-001"}}
        - Never use direct values in FilterExpression without parameter placeholders (:paramName)
        - Use SCAN operation for filtering by non-key attributes
        - For string searches, use contains() function: FilterExpression="contains(#name, :searchTerm)"
        - Use ExpressionAttributeNames for reserved keywords: {{"#name": "name"}}
        
        **Process Flow:**
        1. **Document Processing**: Accept uploaded AI Usecase requirements document (PDF, DOCX, TXT)
        2. **Content Analysis**: Read and understand the complete document content
        3. **ID Generation**: Query existing usecases to determine the next incremental ID
           - Use SCAN operation on table: {stage_name}-{app_name}-usecaseAssessments-{cloud_id}
           - Extract existing IDs and generate next sequential ID (e.g., UC-001, UC-002, etc.)
        4. **AI Category & Approach Detection**: Analyze document to determine:
           - AI Category: "Machine Learning", "AI Workflow Agents", or "Agentic AI"
           - AI Approach: "Next.js with ADK", "MCP-Oriented Orchestration", or "Custom AI Stack"
        5. **Risk Assessment**: Classify overallRisk using the guidance below
        6. **Data Generation**: Create structured JSON with all required fields
        7. **Storage**: Store in DynamoDB table with proper parameter binding

        **AI Category Classification Logic:**
        - **Machine Learning**: Prediction, classification, regression, forecasting, optimization, neural networks
        - **AI Workflow Agents**: Chatbots, RAG, summarization, workflow automation, single/few-shot tasks
        - **Agentic AI**: Multi-agent systems, orchestration, autonomous decision-making, reasoning, goal-directed behavior

        **AI Approach Classification Logic:**
        - **Next.js with ADK**: Frontend AI apps, basic ADK integration, simple use cases
        - **MCP-Oriented Orchestration**: Multi-agent workflows, MCP protocol, agent collaboration
        - **Custom AI Stack**: Python FastAPI, LangChain, Spring Boot, or other custom frameworks

        **Required JSON Structure:**
        {{
          "id": "(analyze existing usecase ids and generate next incremental ID)",
          "ai_approach": "(Next.js with ADK | MCP-Oriented Orchestration | Custom AI Stack)",
          "ai_category": "(Machine Learning | AI Workflow Agents | Agentic AI)",
          "ai_cloud_provider": "(GCP | AWS | Azure based on requirements)",
          "AIMethodologyType": "(extracted from document)",
          "baseModelName": "(if mentioned in document)",
          "businessUsage": "(business purpose from document)",
          "category": "(same as ai_category)",
          "cloudProvider": "(same as ai_cloud_provider)",
          "createdAt": "(ISO 8601 timestamp)",
          "department": "(if mentioned in document)",
          "designDocument": "(generated comprehensive design document)",
          "documentHash": "(SHA-256 hash of document content)",
          "documentSummary": "(3-5 sentence summary of the document)",
          "impact": "(business impact from document)",
          "isProposalGenerated": false,
          "keyActivity": "(main activity from document)",
          "level": 0,
          "metrics": [],
          "modelDescription": "(AI model description)",
          "modelInput": "(expected input format)",
          "modelName": "(AI model name if specified)",
          "modelOutput": "(expected output format)",
          "modelPurpose": "(purpose of the AI model)",
          "modelSummary": "(summary of model functionality)",
          "modelUsage": "(how the model will be used)",
          "overallRisk": "(LOW-RISK AI | MEDIUM-RISK AI | HIGH-RISK AI | PROHIBITED AI)",
          "platform": "(deployment platform)",
          "priorityType": "(priority level)",
          "processingStatus": "PENDING",
          "questions": [],
          "riskframeworkid": "(framework ID if available)",
          "searchAttributesAsJson": "(JSON string of searchable attributes)",
          "sector": "(industry sector)",
          "sourceDocURL": "(document source URL if available)",
          "status": "ACTIVE",
          "updatedAt": "(ISO 8601 timestamp)",
          "usecaseCategory": "(use case category)",
          "useFrequency": "(frequent | continuous(24/7) | weekly | batch)"
        }}

        **Risk Assessment Criteria:**
        {DOCUMENT_RISK_GUIDANCE}

        **Risk Classification Rules:**
        - Analyze document content for data sensitivity, regulatory requirements, business impact
        - Consider technical complexity, user-facing aspects, and compliance implications
        - Provide clear reasoning for the risk classification
        - Default to MEDIUM-RISK AI if unclear

        **Design Document Generation:**
        - Generate a comprehensive technical design document based on the use case
        - Include architecture overview, data flow, security considerations
        - Format as structured HTML content with proper sections
        - Focus on NIST AI RMF compliance and security best practices

        **Final Steps:**
        - Generate unique documentHash using SHA-256 of document content
        - Add current timestamps for createdAt and updatedAt in ISO 8601 format
        - Store the complete JSON object in DynamoDB table: {stage_name}-{app_name}-usecaseAssessments-{cloud_id}
        - Use proper parameter binding for all DynamoDB operations
        - Confirm successful storage and return the generated JSON

        **Error Prevention:**
        - NEVER use direct values in FilterExpression (causes ValidationException)
        - ALWAYS use parameter binding with ExpressionAttributeValues
        - Use SCAN operation for filtering by non-key attributes
        - Ensure all required fields are populated with meaningful values
        """,
        tools=[mcp_toolset]
    )
    
    return agent

# Usage example with proper cleanup:
# def run_agent_with_cleanup(stage_name: str, app_name: str, cloud_id: str, query: str):
#     agent = None
#     mcp_toolset = None
    
    
                
                
# run_agent_with_cleanup(
#     stage_name="staging",
#     app_name="fusefy",
#     cloud_id="d66cb7c7-04ac-4634-927f-06d91afa39bf",
#     query="Analyze this AI usecase document..."
# )

# try:
stage_name="staging",
app_name="fusefy",
cloud_id="d66cb7c7-04ac-4634-927f-06d91afa39bf",
root_agent = create_master_agent(stage_name, app_name, cloud_id)
# except Exception as e:
#         print(f"Error running agent: {e}")
#         raise
# finally:
#         # Cleanup MCP session
#         if mcp_toolset:
#             try:
#                 # Close the MCP session properly
#                 if hasattr(mcp_toolset, 'cleanup') or hasattr(mcp_toolset, 'close'):
#                     mcp_toolset.cleanup() if hasattr(mcp_toolset, 'cleanup') else mcp_toolset.close()
#             except Exception as cleanup_error:
#                 print(f"Warning: Error during MCP cleanup: {cleanup_error}")