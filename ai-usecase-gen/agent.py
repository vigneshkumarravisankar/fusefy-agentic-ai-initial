import json
import os
from typing import Optional
from datetime import datetime
from google.adk.agents import Agent, LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.models.lite_llm import LiteLlm
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from functools import lru_cache



# Environment validation
google_api_key = os.getenv("GOOGLE_API_KEY")
aws_access_key = os.getenv("AWS_ACCESS_ID")
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
openai_key = os.getenv("OPENAI_API_KEY")

@lru_cache(maxsize=1)
def load_documentation():
    """Load documentation files with caching"""
    docs = {}
    try:
        with open('model_process.md', 'r') as file:
            docs['model_process'] = file.read()
        print("Successfully loaded model_process.md file")

        with open('level_finding.md', 'r') as file:
            docs['level_finding'] = file.read()
        print("Successfully loaded level_finding.md file")
        
        # Remove category.md as it's not needed for document analysis
        print("Skipping category.md - using document-based risk assessment")
    except Exception as e:
        print(f"Error loading documentation files: {e}")
        docs['model_process'] = "Model process documentation not available"
        docs['level_finding'] = "Level finding documentation not available"

    return docs


docs = load_documentation()
level_finding_content = docs['level_finding']
model_process_content = docs['model_process']

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


DESIGN_DOCUMENT_STEPS = """
            MASTER AGENT PROMPT: Solution Architect and Project Planner
            AGENT ROLE: You are a Senior Solutions Architect and Agentic AI Specialist. You are an expert in Domain-Driven Design (DDD), Google Cloud Platform (GCP) architecture, and the NIST AI Risk Management Framework (AI RMF).

            GOAL: Analyze the provided Functional Requirement Document (FRD) and generate a comprehensive, structured technical design package. This package must adhere to all specified constraints, including strict NIST AI RMF compliance, focusing heavily on layered security for the Agentic components.

            OUTPUT MANDATE:
            Generate the output sequentially, adhering strictly to the five sections below.
            Format all output as valid, well-structured HTML fragments using appropriate tags (h2, h3, p, table, pre, code, etc.).
            DO NOT include <!DOCTYPE>, <html>, <body> or other full document tags - just provide the HTML content fragments.
            Start with a <h2> heading for Section 1 (not h1), and include a brief introductory paragraph explaining the core problem before Section 1.


            1. Domain and Entity Identification (NIST AI RMF: MAP)

            Core Domain Definition:
            Specify the primary domain name and core focus area of the system.
            Format: "Core Domain: [Domain Name]"

            Bounded Context Definitions:
            For each bounded context (minimum 3), provide:
            - Context Name and Number (e.g., "Bounded Context 1: [Name]")
            - Focus: One-line description of the context\'s responsibility
            - Core Entity: List of primary entities in this context

            Entity Identification Table:
            Present in a clear tabular format:
            ```
            Entity Identification
            Context (Bounded Context Name)
            Entity (Aggregate Root)
            Key Attributes
            [Context Name]
            [Entity Name]
            [List of key attributes with types]
            ```
            
            Notes:
            - Use dimension (Dim_) and fact (Fact_) prefixes appropriately
            - Include Primary Keys (PK) and Foreign Keys (FK) in attributes
            - Follow exact format and naming conventions as shown
            - Keep descriptions concise and technical
            - Focus on structural relationships between entities

            2. Data Model Design: Database Tables and Linkages

            Table Schema: Full DDL Snippets
            For each table, provide complete CREATE TABLE statements with:
            - Table name with appropriate prefix (Dim_/Fact_)
            - All columns with precise PostgreSQL data types
            - Primary and Foreign key constraints
            - Required constraints (NOT NULL, UNIQUE)
            - Audit columns (created_by, created_at, etc.)
            - Comments explaining key constraints
            
            Present each CREATE TABLE statement in its own section, separated by a descriptive header:

            <h4>[Table Name] Definition</h4>
            <pre><code class="language-sql">
            CREATE TABLE [TableName] (
                [column_name] [data_type] [constraints],
                ...
                CONSTRAINT [constraint_name] [constraint_definition]
            );
            </code></pre>

            <p>[Brief description of table purpose and key relationships]</p>

            Relationship Diagram:
            List all relationships in format:
            [Table1] (1) ⟷ (M) [Table2] ([relationship description])

            3. Domain-Driven Design APIs (RESTful Service Contracts)

            Service List:
            List all core services with brief descriptions:
            - [ServiceName]: Brief description of service responsibility

            API Endpoints: Comprehensive Application View
            Present in a table format:
            ```
            Service | Method | Endpoint | Description | Key Roles/Authorization Scope
            ```

            Required columns:
            - Service: Name of the service
            - Method: HTTP method (GET, POST, PATCH, etc.)
            - Endpoint: Full URL path with version (/api/v1/...)
            - Description: Brief description of endpoint purpose
            - Key Roles/Authorization Scope: Required permissions

            Group endpoints by service with separators (---)

            4. Agentic AI Integration: ADK, MCP, and IPI Defense (NIST AI RMF: MANAGE)

            Agent Definition:
            Present in table format:
            ```
            Field | Detail
            Agent Name | [name]
            Agent Persona | [description]
            Primary Goal | [goal]
            ```

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
        name="Fusefy_Usecase_Generator_and_storing_Agent",
        model=LiteLlm(model="openai/gpt-4o"),
        instruction=f"""
        You are an expert AI Usecase extractor and risk assessor for Fusefy.
        
        Use DynamoDB MCP(strict) in order to select appropriate tools and store the data in the tables.
        
        
        
        REQUIRED FIELDS (ALL MUST BE DERIVED FROM THE DOCUMENT CONTENT):

        1. businessUsage: Extract the specific business application from the document content - provide 2-3 detailed, grammatically correct sentences describing exactly what is mentioned in the document.
        2. currentBusinessUsage: Describe how the process or activity is currently being performed in the real business before AI implementation. Focus on manual steps, inefficiencies, challenges, or existing workflows that the AI solution aims to improve. Provide 2-3 clear, grammatically correct sentences that reflect the current or existing state of the business process.
        3. department: Identify the department mentioned in the document or infer from the business context described.
        4. usecaseCategory: Set to ai_category accordingly to the usecase".
        5. impact: Assess business impact based on what's described in the document:
         - HIGH: Strategic transformation, significant efficiency gains, competitive advantage
         - MEDIUM: Operational improvements, moderate efficiency gains
         - LOW: Minor enhancements, limited scope
        6. level: Determine AI maturity level (0-6) based on the complexity and scope described in the document:
        {level_finding_content}
        7. AIMethodologyType: Select the most appropriate value from the MASTER AIMethodologyType OPTIONS above and return it as a human-readable, title-cased, space-separated string (e.g., "Real Estate Consultancy AI").
        8. baseModelName: Identify the most appropriate base model (e.g., Gemini, Bedrock, GPT-4, Claude, etc.) mentioned in the document or suitable for the described use case. If not explicitly mentioned, you MUST infer and select the most appropriate model and always provide a value. baseModelName must never be empty.
        9. keyActivity: Extract the primary activity/function described in the document in 1-2 concise, grammatically correct sentences.
        10. modelInput: Extract all relevant input data types mentioned or implied in the document. If multiple, return as a single comma-separated string in user-friendly, title-cased, space-separated format (e.g., "Lesson Plan PPT, Student List, Assessment Report"). Use correct spelling and casing.
        11. modelOutput: Extract all relevant output data types mentioned or implied in the document. If multiple, return as a single comma-separated string in user-friendly, title-cased, space-separated format (e.g., "PDF Report, Email Notification"). Use correct spelling and casing.
        12. modelName: Create a human-readable, title-cased, space-separated name based on the use case described in the document (e.g., "Property Requirements AI", "Real Estate Consultancy AI").
        13. modelDescription: Based on the document content, provide a comprehensive 3-4 sentence description of the model's functionality, ensuring all details are derived from the document and the text is grammatically correct.
        14. modelSummary: Provide a concise 1-2 sentence summary based on the document content, ensuring all details are derived from the document and the text is grammatically correct.
        15. modelPurpose: Extract the specific goal/purpose from the document content.
        16. modelUsage: Based on the document, describe how the model would be used technically.
        17. overallRisk: Based on the document content, assess the overall risk level:
            - LOW: Basic automation, minimal sensitive data, simple business processes
            - MEDIUM: Moderate automation, some personal data, industry compliance considerations
            - HIGH: Critical decisions, extensive sensitive data, high regulatory requirements, safety-critical
            - PROHIBITED: Biometric surveillance, social scoring, behavioral manipulation
        18. platform: Extract or infer relevant technologies from the document content as a comma-separated string, and always append the cloud provider (the cloud provider) at the end (e.g., "Python, FastAPI etc and so on").
        19. cloudProvider: Set to the cloud provider found in the document (if present), otherwise use the passed argument.
        20. priorityType: Determine the risk classification based on document content analysis:
            - "LOW-RISK AI": For basic business automation with minimal risk factors
            - "MEDIUM-RISK AI": For moderate complexity systems with some risk considerations
            - "HIGH-RISK AI": For critical systems with significant risk factors or regulatory requirements
            - "PROHIBITED AI": Only if document describes prohibited use cases (rare)
        21. sector: Extract or infer the industry sector from the document content.
        22. useFrequency: Extract or infer usage frequency from the document content. Only select one of the following master values: "Daily", "Weekly", "Monthly", or "Yearly".

        Your goal:
        1. Accept an uploaded AI Usecase requirements document (PDF, DOCX, TXT).
        2. Read and understand the document content.
        4. Generate a structured JSON for the AI usecase in this exact format:
        {{
          "id": ""(See with the latest id in the table, and increment 1 with the one which is greatest. eg - If id is AI-UC-AST-025, then change it to AI-UC-AST-026,
          "ai_approach": "",
          "ai_category": "",
          "ai_cloud_provider": "",
          "AIMethodologyType": "",
          "baseModelName": "",
          "businessUsage": "",
          "category": "AI Inventory(by default)",
          "cloudProvider": "",
          "createdAt": "",
          "department": "",
          "disableModelProcess":false(by default),
          "designDocument": ""(Refer below instructions(strictly minimum 4-5 pages, covering broader aspects of the AI Usecase.) : \n {DESIGN_DOCUMENT_STEPS}, strictly it should be of html format only),
          "documentHash": "",
          "documentSummary": "",
          "impact": "",
          "jiraStoryId":"",
          "isProposalGenerated": false,
          "keyActivity": "",
          "level": 0,
          "metrics": [],
          "modelDescription": ""(Around 5-6 sentences),
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
        
        metrics: Select the most appropriate metrics (5-7 total). Prioritize selection from the MASTER METRICS OPTIONS. However, to ensure **real business measurement** and not just generic AI metrics, you may **infer and append 1-2 additional, highly specific metrics** that are crucial to the documented business use case, if the master list lacks necessary business relevance. For each selected metric, set a realistic threshold value (0-100) based on the document content and the identified AIMethodologyType (do not use any threshold from master data, always infer from the document and context).

        CRITICAL TIP FOR METRICS: Metrics must be highly relevant and tied to tangible business outcomes, not just model accuracy. Use the following examples to guide your specificity:

        - **GENERIC (AVOID):** "F1 Score," "Accuracy" (unless strictly necessary)
        - **REAL ESTATE (EXAMPLE):** "Property Listing Match Rate (85%)," "Lead-to-View Conversion Rate (70%)," "Time-to-Offer Reduction (75%)"
        - **HEALTHCARE CLAIMS (EXAMPLE):** "Claims Processing Straight-Through Rate (90%)," "Error Rate on Approved Claims (98%)," "Time to Adjudication Reduction (75%)"
        - **EDUCATION (EXAMPLE):** "Student Assessment Consistency (95%)," "Lesson Plan Generation Time (90%)," "Teacher Time Saved Per Week (80%)"
        - **INTERVIEW AGENT (EXAMPLE):** "Candidate Quality Rating Consistency (85%)," "Screening Time Per Candidate Reduction (70%)," "Hiring Manager Satisfaction Score (80%)"

        Each metric must follow this JSON structure:
        [
        {{
            "metricName": "",
            "metricDescription": "",
            "threshold": 0
        }}
        ]
        
        24. status: Set to "Not yet started".
        

        Then:
        - Use the following guidance to classify the overallRisk:
        {DOCUMENT_RISK_GUIDANCE}
        

        Agent Development Kit (ADK) and Tool Mapping:
            List all tools in table format:
            ```
            Tool Name (Internal Function) | Mapped DDD API Endpoint | DDD Service | Purpose & Edge Case Coverage
            ```

            Model Context Protocol (MCP) Design:
            Detail the following components:

            1. Input Validation and Sanitization Layer (IPI Defense)
                - Protocol Step
                - GCP Service
                - Mechanism
                - Protocol Action

            2. Context Retrieval and Grounding Layer
                - Protocol Step
                - GCP Service
                - Mechanism

            3. Tool Orchestration and Security Wrapper
                - Protocol Step
                - GCP Service
                - Mechanism (detailed bullet points)

            4. Safety and Alignment Layer
                - Protocol Step
                - GCP Service
                - Function

            5. Frontend Pages and Agentic UX

            Page List:
            List the three most critical views with their primary purposes.

            Agent Integration Flow:
            Document the integration in table format:
            ```
            UI Element | Trigger Action | Agent Flow Step
            ```

        Security and Edge Case UX Design:
            1. AI Action Confirmation Modal (NIST AI RMF: MANAGE - AI-4.5)
            - Content requirements
            - Edge case handling
            - User feedback mechanisms

            2. Intervention and Reporting Chat UX (Principal Focus)
            Present in table format:
            ```
            UX Feature | Purpose | Edge Case Handling
            ```

            3. Policy and Grounding Transparency UX
            Detail the following:
            - Transparency mechanisms
            - Source documentation
            - Error handling
            - User feedback

        FINAL MANDATE: Review your entire output. Format everything with proper HTML tags. Ensure every instruction has been fully addressed, and that the five sections flow logically from requirements to implementation.

            Rules for Risk Evaluation:
            - Determine the most fitting category (LOW, MEDIUM, HIGH, or PROHIBITED)
            based on document context (AI type, sensitivity, scope, compliance impact).
            - Provide clear reasoning for the risk classification.

            Finally:
            - Generate a unique documentHash using the document content
            - Add the documentSummary (3-5 sentence summary)
            - For baseModelName, if not explicitly mentioned in the document, you MUST infer and select the most appropriate model (e.g., "GPT-4", "Claude", "Gemini", "Bedrock", etc.) based on the use case and always provide a value. baseModelName must never be empty.
            
            - Add timestamps for 'createdAt' and 'updatedAt' in ISO 8601 format
            - Store the final structured JSON object into the DynamoDB table:
            {stage_name}-{app_name}-usecaseAssessments-{cloud_id}
            
        Other critical things to note:
            - searchAttributesAsJson: Combine key attributes derived from document as comma-separated string.
            - questions: Extract ALL explicit questions that are specifically written in the document. Look for:
                - Questions ending with "?"
                - Interrogative statements
                - Requests for information or clarification
                - Any queries posed in the document
                Do NOT generate new questions - only extract the actual questions that appear in the document text.
                Return as an array of strings containing the exact questions found in the document.
            - isProposalGenerated: Set to false.

            CRITICAL FORMATTING REQUIREMENTS:
                - Return valid JSON that can be parsed by json.loads().
                - All field values must be grammatically correct, human-readable, and use the correct casing and style for each field (e.g., Real Estate Consultancy AI, property_requirements_form, PDF_report).
                - Do not invent, misspell, or change casing of any value. Use master options and document content exactly as provided.
                - Include specific ai_category tools, technologies, and implementation details in all relevant fields.
                - Show clear business value progression alongside technical development.
                - ALL content must be derived from the actual document content provided above.
                - Focus on ai_category -specific approaches and methodologies.
                - Ensure accuracy to the document content - no generic responses.   
            
            Important point : You can also suggest some tools and technologies in the respective usecase, which is to be built - if not specifically mentioned in the document.

            Always respond with the generated JSON and confirmation of storage. Never use undefined values inside when storing, either replace with empty string or array.
            
            Strictly follow this response format:
            {{
                "status":"success|fail",
                "message":"About the operation whether its done successfully or not."
            }}
        """,
        tools=[mcp_toolset]
    )

# Create the agent
root_agent = create_master_agent(
    stage_name="staging",
    app_name="fusefy",
    cloud_id="d66cb7c7-04ac-4634-927f-06d91afa39bf"
)