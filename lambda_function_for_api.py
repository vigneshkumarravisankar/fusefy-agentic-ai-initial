import os
import io
import json
import hashlib
from typing import Optional, List
from datetime import datetime
from decimal import Decimal
import boto3
import pdfplumber
import docx
import mimetypes
import time
import logging
import re
import urllib.parse
from functools import lru_cache
from boto3.dynamodb.conditions import Attr
from botocore.exceptions import ClientError
import base64

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
s3_client = boto3.client('s3')

# OpenAI API Key
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
if not OPENAI_API_KEY:
    logger.error("OPENAI_API_KEY environment variable is required but not set")

# Load documentation files with caching
@lru_cache(maxsize=1)
def load_documentation():
    """Load documentation files with caching"""
    docs = {}
    try:
        # Try to load from files if they exist, otherwise use defaults
        try:
            with open('model_process.md', 'r') as file:
                docs['model_process'] = file.read()
            logger.info("Successfully loaded model_process.md file")
        except FileNotFoundError:
            docs['model_process'] = "Model process documentation not available"

        try:
            with open('level_finding.md', 'r') as file:
                docs['level_finding'] = file.read()
            logger.info("Successfully loaded level_finding.md file")
        except FileNotFoundError:
            docs['level_finding'] = """
AI Maturity Levels (0-6):
0: No AI - Traditional software without AI components
1: Basic AI - Simple rule-based systems, basic automation
2: Assisted AI - AI provides recommendations, human makes decisions
3: Augmented AI - AI and humans work together, shared decision-making
4: Autonomous AI - AI makes decisions independently with human oversight
5: Fully Autonomous - AI operates independently with minimal human intervention
6: Superintelligent AI - AI exceeds human capabilities across all domains
"""

        logger.info("Skipping category.md - using document-based risk assessment")
    except Exception as e:
        logger.error(f"Error loading documentation files: {e}")
        docs['model_process'] = "Model process documentation not available"
        docs['level_finding'] = "Level finding documentation not available"

    return docs

# Get documentation content
docs = load_documentation()
level_finding_content = docs['level_finding']
model_process_content = docs['model_process']

# Document-based risk assessment guidance
document_risk_guidance = """
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

def convert_floats_to_decimal_for_dynamodb(obj):
    """Convert float values to Decimal for DynamoDB compatibility"""
    if isinstance(obj, float):
        return Decimal(str(obj))
    elif isinstance(obj, dict):
        return {k: convert_floats_to_decimal_for_dynamodb(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [convert_floats_to_decimal_for_dynamodb(item) for item in obj]
    else:
        return obj

def call_llm(prompt: str, system_prompt: Optional[str] = None, model_id: str = "gpt-4o", use_json_format: bool = True, max_tokens: int = 4000) -> str:
    """Call OpenAI GPT-4o via OpenAI API with configurable max_tokens"""
    import requests

    url = "https://api.openai.com/v1/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {OPENAI_API_KEY}"
    }

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})
    messages.append({"role": "user", "content": prompt})

    data = {
        "model": model_id,
        "messages": messages,
        "temperature": 0.3 if not use_json_format else 0.5,
        "max_tokens": max_tokens
    }

    if use_json_format:
        data["response_format"] = {"type": "json_object"}

    try:
        start_time = time.time()
        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()
        result = response.json()

        # Log latency metrics
        latency = (time.time() - start_time) * 1000  # milliseconds
        logger.info(f"OpenAI API call completed in {latency:.2f}ms")

        return result["choices"][0]["message"]["content"]
    except Exception as error:
        logger.error(f"Error calling OpenAI API: {error}")
        raise Exception(f"LLM service error: {error}")

def determine_ai_category_and_approach_with_llm(document_text):
    """Determine AI category and technical approach based on document content"""
    logger.info("Determining AI category and approach using LLM analysis")

    prompt = f"""
Analyze the following COMPLETE document content and identify BOTH:
1. AI Category → One of:
   - Machine Learning
   - AI Workflow Agents
   - Agentic AI
2. Approach → Based on tech stack and complexity:
   - "Next.js + ADK" (simple use case)
   - "Next.js + ADK + MCP" (MCP multi-agent use case)
   - "Custom AI Stack" (if neither matches)

COMPLETE DOCUMENT CONTENT:
{document_text}

CRITERIA:
- Category logic:
  - Machine Learning: Prediction, classification, regression, forecasting, optimization
  - AI Workflow Agents: Step-based or workflow-driven tasks, chatbots, RAG, summarization, single/few-shot flows
  - Agentic AI: Multi-agent, orchestration, decision-making, reasoning, goal-directed autonomy
- Approach logic:
  - Next.js + ADK → If mentions frontend AI app, ADK, basic integration, no orchestration
  - Next.js + ADK + MCP → If mentions MCP, multi-agent, orchestration, workflows, agents collaborating
  - Custom AI Stack → Any other tech stack (e.g., Python FastAPI, LangChain, Spring Boot etc.)

INSTRUCTIONS:
1. Analyze ENTIRE content for both category and approach.
2. Respond strictly in the format:

Category: [Category]
Approach: [Approach]
Reason: [1-2 sentence explanation]
"""

    try:
        system_prompt = "You are an AI categorization and approach expert. Classify both AI category and technical approach from the document."
        response = call_llm(prompt, system_prompt, use_json_format=False, max_tokens=300)

        # Default fallback values
        category, approach = "AI Workflow Agents", "Custom AI Stack"

        # Category handling
        if "Machine Learning" in response:
            category = "Machine Learning"
        elif "Agentic AI" in response:
            category = "Agentic AI"
        elif "AI Workflow Agents" in response:
            category = "AI Workflow Agents"

        # Approach handling
        if "Next.js + ADK + MCP" in response:
            approach = "MCP-Oriented Orchestration"
        elif "Next.js + ADK" in response:
            approach = "Next.js with ADK"
        elif "Custom AI Stack" in response:
            approach = "Custom AI Stack"

        return {"category": category, "approach": approach, "raw_response": response}

    except Exception as e:
        logger.error(f"Error in LLM determination: {e}")
        # Fallback keyword-based categorization
        category = determine_ai_category_based_on_data_fallback(document_text)

        text_lower = document_text.lower()
        if "mcp" in text_lower or "multi-agent" in text_lower or "orchestration" in text_lower:
            approach = "MCP-Oriented Orchestration"
        elif "next.js" in text_lower and "adk" in text_lower:
            approach = "Next.js with ADK"
        else:
            approach = "Custom AI Stack"

        return {"category": category, "approach": approach, "raw_response": "Fallback logic applied"}

def determine_ai_category_based_on_data_fallback(document_text):
    """Fallback keyword-based categorization"""
    logger.info("Using fallback keyword-based categorization")

    try:
        text_lower = document_text.lower()

        # ML keywords  
        ml_keywords = [
            'predict', 'prediction', 'classify', 'classification', 'cluster',
            'regression', 'forecast', 'anomaly detection', 'pattern recognition',
            'supervised learning', 'unsupervised learning', 'recommendation',
            'feature engineering', 'model training', 'algorithm',
            'neural network', 'deep learning', 'random forest', 'svm',
            'decision tree', 'ensemble', 'xgboost', 'logistic regression',
            'clustering', 'optimization', 'data mining'
        ]

        # AI Workflow Agent keywords
        workflow_keywords = [
            'chatbot', 'rag', 'retrieval augmented generation',
            'summarization', 'summarize', 'dialogue', 'conversation',
            'workflow', 'approval process', 'single shot', 'few shot',
            'content creation', 'form processing', 'automation step'
        ]

        # Agentic AI keywords
        agentic_keywords = [
            'agent', 'autonomous', 'multi-agent', 'collaboration',
            'orchestration', 'decision-making', 'reasoning', 'goal-oriented',
            'workflow automation', 'adaptive planning',
            'self-improving', 'tool use', 'api orchestration', 'planner',
            'mcp', 'model context protocol'
        ]

        ml_score = sum(1 for keyword in ml_keywords if keyword in text_lower)
        workflow_score = sum(1 for keyword in workflow_keywords if keyword in text_lower)
        agentic_score = sum(1 for keyword in agentic_keywords if keyword in text_lower)

        logger.info(f"Keyword analysis - ML: {ml_score}, Workflow: {workflow_score}, Agentic: {agentic_score}")

        if ml_score > workflow_score and ml_score > agentic_score:
            return "Machine Learning"
        elif workflow_score > ml_score and workflow_score > agentic_score:
            return "AI Workflow Agents"
        elif agentic_score > ml_score and agentic_score > workflow_score:
            return "Agentic AI"
        else:
            return "AI Workflow Agents"  # Default fallback

    except Exception as e:
        logger.error(f"Error in fallback categorization: {e}")
        return "AI Workflow Agents"

def detect_file_type(filename: str) -> str:
    """Detect file type from filename"""
    content_type, _ = mimetypes.guess_type(filename)

    if content_type == 'application/pdf':
        return 'PDF'
    elif content_type == 'application/vnd.openxmlformats-officedocument.wordprocessingml.document':
        return 'DOCX'

    # Fallback to extension
    _, ext = os.path.splitext(filename)
    ext = ext.lower()

    if ext == '.pdf':
        return 'PDF'
    elif ext == '.docx':
        return 'DOCX'
    elif ext == '.txt':
        return 'TXT'

    return 'UNKNOWN'

def extract_text_from_uploaded_file(file_content: bytes, filename: str) -> dict:
    """Extract text from uploaded file content"""
    try:
        file_type = detect_file_type(filename)
        text = ""

        if file_type == 'PDF':
            logger.info("Processing as PDF")
            pdf_file = io.BytesIO(file_content)
            with pdfplumber.open(pdf_file) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

        elif file_type == 'DOCX':
            logger.info("Processing as DOCX")
            docx_file = io.BytesIO(file_content)
            doc = docx.Document(docx_file)
            for para in doc.paragraphs:
                if para.text:
                    text += para.text + "\n"

        elif file_type == 'TXT':
            logger.info("Processing as TXT")
            text = file_content.decode('utf-8')

        else:
            logger.error(f"Unsupported file type: {file_type}")
            return {"success": False, "error": f"Unsupported file type: {file_type}"}

        # Normalize text
        normalized_text = ' '.join(text.split()) if text else ""

        # Generate document hash
        document_hash = hashlib.sha256(normalized_text.encode('utf-8')).hexdigest()

        return {
            "success": True,
            "text": normalized_text,
            "document_hash": document_hash,
            "file_type": file_type
        }

    except Exception as e:
        logger.error(f"Error extracting text from uploaded file: {e}")
        return {"success": False, "error": str(e)}

def summarize_document_with_llm(document_text):
    """Summarize the provided document text using OpenAI LLM"""
    prompt = f"""
You are an expert business analyst. Read the following business use case document and provide a concise summary (3-5 sentences) that captures the main purpose, business context, and technical approach. Then, list 3-5 key points or highlights from the document as bullet points.

DOCUMENT:
{document_text}

RESPONSE FORMAT:
Summary: <Concise summary here>
Key Points:
- <Key point 1>
- <Key point 2>
- <Key point 3>
(Add more if relevant)
"""
    system_prompt = "You are a business analyst summarizing business use case documents for executive review."
    response = call_llm(prompt, system_prompt, use_json_format=False, max_tokens=600)
    return {"documentSummary": response.strip()}

def generate_design_document_prompt(document_text):
    """Create a comprehensive prompt for generating a design document"""
    prompt = f"""
MASTER AGENT PROMPT: Solution Architect and Project Planner
AGENT ROLE: You are a Senior Solutions Architect and Agentic AI Specialist. You are an expert in Domain-Driven Design (DDD), Google Cloud Platform (GCP) architecture, and the NIST AI Risk Management Framework (AI RMF).

GOAL: Analyze the provided Functional Requirement Document (FRD) and generate a comprehensive, structured technical design package. This package must adhere to all specified constraints, including strict NIST AI RMF compliance, focusing heavily on layered security for the Agentic components.

OUTPUT MANDATE:
Generate the output sequentially, adhering strictly to the five sections below.
Format all output as valid, well-structured HTML fragments using appropriate tags (h2, h3, p, table, pre, code, etc.).
DO NOT include <!DOCTYPE>, <html>, <body> or other full document tags - just provide the HTML content fragments.
Start with a <h2> heading for Section 1 (not h1), and include a brief introductory paragraph explaining the core problem before Section 1.

FUNCTIONAL REQUIREMENT DOCUMENT (FRD) INPUT:
{document_text}

1. Domain and Entity Identification (NIST AI RMF: MAP)
2. Data Model Design: Database Tables and Linkages
3. Domain-Driven Design APIs (RESTful Service Contracts)
4. Agentic AI Integration: ADK, MCP, and IPI Defense (NIST AI RMF: MANAGE)
5. Frontend Pages and Agentic UX

FINAL MANDATE: Review your entire output. Format everything with proper HTML tags. Ensure every instruction has been fully addressed, and that the five sections flow logically from requirements to implementation.
"""
    return prompt

def generate_usecase_with_llm_focused(document_text, ai_category, cloud_provider, all_mapping_records=None):
    """Generate a use case using OpenAI LLM based on document content and AI category"""
    try:
        logger.info(f"Preparing enhanced prompt for OpenAI model with category: {ai_category}")

        # Cloud provider extraction logic
        cloud_providers = ["AWS", "Azure", "GCP", "Google Cloud", "Google Cloud Platform", "Amazon Web Services", "Microsoft Azure"]
        found_provider = None
        for provider in cloud_providers:
            if provider.lower() in document_text.lower():
                found_provider = provider
                break

        # Normalize found provider
        if found_provider:
            if found_provider in ["Google Cloud", "Google Cloud Platform"]:
                found_provider = "GCP"
            elif found_provider == "Amazon Web Services":
                found_provider = "AWS"
            elif found_provider == "Microsoft Azure":
                found_provider = "Azure"
            final_cloud_provider = found_provider
        else:
            final_cloud_provider = cloud_provider

        # Create category-specific system prompt
        if ai_category == "Machine Learning":
            system_prompt = "You are an expert AI solution architect with deep expertise in Machine Learning methodologies. Generate comprehensive use cases that combine business strategy with technical implementation."
            methodology_guidance = "Focus on Machine Learning methodologies: predictive modeling, classification, regression, pattern recognition, feature engineering, statistical learning, anomaly detection."
        elif ai_category == "AI Workflow Agents":
            system_prompt = "You are an expert AI solution architect with deep expertise in workflow automation and AI agents. Generate comprehensive use cases that combine business strategy with technical implementation."
            methodology_guidance = "Focus on AI Workflow Agent methodologies: task automation, approval workflows, form/document processing, single-shot/few-shot execution, structured pipelines."
        elif ai_category == "Agentic AI":
            system_prompt = "You are an expert AI solution architect with deep expertise in Agentic AI methodologies. Generate comprehensive use cases that combine business strategy with technical implementation."
            methodology_guidance = "Focus on Agentic AI methodologies: multi-agent systems, autonomous task execution, decision orchestration, planning, agent collaboration, adaptive workflows."
        else:
            system_prompt = "You are an expert AI solution architect. Generate comprehensive use cases that combine business strategy with technical implementation."
            methodology_guidance = "Fallback guidance: ensure clear business-technical mapping, highlight security, compliance, and practical deployment considerations."

        prompt = f"""
Based on the following document content analysis, generate a comprehensive AI use case specifically for a {ai_category} solution.

DOCUMENT CONTENT:
{document_text}

AI CATEGORY DETERMINED: {ai_category}
CLOUD PROVIDER TO USE: {final_cloud_provider}
METHODOLOGY GUIDANCE: {methodology_guidance}

CRITICAL INSTRUCTIONS:
- All field values must be grammatically correct, human-readable, and use proper casing
- For modelInput and modelOutput, return as user-friendly, title-cased, comma-separated strings
- For modelName and AIMethodologyType, return human-readable, title-cased strings
- All output must be valid JSON parsable by json.loads()

REQUIRED FIELDS:
1. businessUsage: Extract specific business application from document (2-3 sentences)
2. currentBusinessUsage: Describe current manual process before AI implementation
3. department: Identify or infer department from context
4. usecaseCategory: Set to "{ai_category}"
5. impact: Assess business impact (HIGH/MEDIUM/LOW)
6. level: Determine AI maturity level (0-6)
7. AIMethodologyType: Human-readable methodology type
8. baseModelName: Appropriate base model (GPT-4, Claude, Gemini, Bedrock)
9. keyActivity: Primary activity/function (1-2 sentences)
10. modelInput: Relevant input data types (comma-separated)
11. modelOutput: Relevant output data types (comma-separated)
12. modelName: Human-readable model name
13. modelDescription: Comprehensive 3-4 sentence description
14. modelSummary: Concise 1-2 sentence summary
15. modelPurpose: Specific goal/purpose
16. modelUsage: Technical usage description
17. overallRisk: Risk level (LOW-RISK AI/MEDIUM-RISK AI/HIGH-RISK AI/PROHIBITED AI)
18. platform: Technologies + cloud provider
19. cloudProvider: {final_cloud_provider}
20. priorityType: Same as overallRisk
21. sector: Industry sector
22. useFrequency: Daily/Weekly/Monthly/Yearly
23. metrics: 5-7 relevant metrics with thresholds
24. status: "Not yet started"
25. searchAttributesAsJson: Comma-separated key attributes
26. questions: Extract actual questions from document
27. isProposalGenerated: false

Generate the complete JSON response now:
"""

        response = call_llm(prompt, system_prompt, max_tokens=7000)

        # Parse JSON response
        try:
            usecase_data = json.loads(response)
        except json.JSONDecodeError:
            # Try to extract JSON from response
            json_start = response.find('{')
            json_end = response.rfind('}') + 1
            if json_start != -1 and json_end > json_start:
                json_text = response[json_start:json_end]
                json_text = re.sub(r',(\s*[}\]])', r'\1', json_text)  # Remove trailing commas
                usecase_data = json.loads(json_text)
            else:
                raise Exception("No valid JSON found in response")

        # Ensure category matches
        usecase_data['usecaseCategory'] = ai_category
        usecase_data['cloudProvider'] = final_cloud_provider

        # Enhance the data
        usecase_data = enhance_usecase_data(usecase_data, ai_category)

        return usecase_data

    except Exception as e:
        logger.error(f"Error in enhanced usecase generation: {e}")
        return {"error": str(e)}

def enhance_usecase_data(usecase_data, ai_category):
    """Enhance and validate usecase data"""
    try:
        # Convert floats to Decimal for DynamoDB
        usecase_data = convert_floats_to_decimal_for_dynamodb(usecase_data)

        if not isinstance(usecase_data, dict):
            usecase_data = {}

        # Ensure usecaseCategory matches
        usecase_data["usecaseCategory"] = ai_category

        # Add searchAttributesAsJson field
        usecase_data["searchAttributesAsJson"] = ",".join([
            str(usecase_data.get("AIMethodologyType", "")),
            str(usecase_data.get("modelName", "")),
            str(usecase_data.get("sector", "")),
            str(usecase_data.get("platform", ""))
        ])

        # Handle metrics
        raw_metrics = usecase_data.get("metrics", [])
        if not isinstance(raw_metrics, list) or not raw_metrics:
            # Set default metrics based on AI category
            if ai_category == "AI Workflow Agents":
                metrics = [
                    {"metricName": "Response Relevance", "metricDescription": "Measure of how well the agent follows the defined workflow steps", "threshold": 85},
                    {"metricName": "Workflow Accuracy", "metricDescription": "Percentage of tasks executed correctly within the defined workflow", "threshold": 90},
                    {"metricName": "User Satisfaction", "metricDescription": "Rating of agent interaction quality and usefulness", "threshold": 90},
                    {"metricName": "Response Time", "metricDescription": "Time taken for the agent to complete a workflow step", "threshold": 5}
                ]
            elif ai_category == "Machine Learning":
                metrics = [
                    {"metricName": "Accuracy", "metricDescription": "The proportion of correctly classified instances out of the total instances", "threshold": 90},
                    {"metricName": "Precision", "metricDescription": "The ratio of correctly predicted positive instances to all predicted positives", "threshold": 85},
                    {"metricName": "Recall", "metricDescription": "The ratio of correctly predicted positive instances to actual positives", "threshold": 85},
                    {"metricName": "F1-Score", "metricDescription": "The harmonic mean of precision and recall", "threshold": 85}
                ]
            elif ai_category == "Agentic AI":
                metrics = [
                    {"metricName": "Task Completion Rate", "metricDescription": "Percentage of tasks successfully executed by agents", "threshold": 90},
                    {"metricName": "Decision Accuracy", "metricDescription": "Accuracy of autonomous decisions or recommendations", "threshold": 85},
                    {"metricName": "System Reliability", "metricDescription": "Measure of uptime and fault tolerance of the AI system", "threshold": 95},
                    {"metricName": "Collaboration Efficiency", "metricDescription": "Effectiveness of multi-agent coordination and workflow execution", "threshold": 85}
                ]
            else:
                metrics = [{"metricName": "Generic Success Rate", "metricDescription": "Fallback metric when category is unclear", "threshold": 80}]

            usecase_data["metrics"] = metrics

        # Ensure required fields are strings
        string_fields = ["platform", "businessUsage", "modelDescription"]
        for field in string_fields:
            val = usecase_data.get(field, "")
            if isinstance(val, list):
                usecase_data[field] = ", ".join(str(item) for item in val)
            elif not isinstance(val, str):
                usecase_data[field] = str(val)

        # Set required status
        usecase_data["status"] = "Not yet started"

        logger.info("Successfully enhanced usecase data")
        return usecase_data

    except Exception as e:
        logger.error(f"Error enhancing usecase data: {e}")
        return {"error": f"Error enhancing data: {e}"}

def fetch_all_dynamodb_records(table_name, dynamodb_resource):
    """Fetch all records from a DynamoDB table, handling pagination."""
    try:
        table = dynamodb_resource.Table(table_name)
        all_records = []
        scan_kwargs = {}
        while True:
            response = table.scan(**scan_kwargs)
            items = response.get('Items', [])
            all_records.extend(items)
            if 'LastEvaluatedKey' in response:
                scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']
            else:
                break
        logger.info(f"Fetched {len(all_records)} records from {table_name}")
        return all_records
    except Exception as e:
        logger.error(f"Error fetching records from {table_name}: {e}")
        return []

def get_usecase_assessment_table_and_framework_id(app_name: str, stage_name: str, tenant_id: str, dynamodb_resource) -> tuple[str, str]:
    """Returns tenant-specific usecase assessment table name and framework ID"""
    # Framework Table
    framework_table_name = f"{stage_name}-{app_name}-frameworks"
    try:
        framework_table = dynamodb_resource.Table(framework_table_name)
        response = framework_table.scan(
            FilterExpression=Attr('name').contains('NIST') & Attr('assessmentCategory').contains('AI Evaluation Engine'),
            ProjectionExpression="id"
        )
        items = response.get('Items', [])
        framework_id = items[0]['id'] if items else None
        logger.info(f"Framework ID found: {framework_id}")
    except Exception as e:
        logger.error(f"Error scanning framework table {framework_table_name}: {e}")
        framework_id = None

    # Construct final usecase assessment table name
    usecase_table_name = f"{stage_name}-{app_name}-usecaseAssessments-{tenant_id}"
    logger.info(f"Resolved usecase assessment table: {usecase_table_name}")

    return usecase_table_name, framework_id

def generate_sequential_id(dynamodb_resource, table_name, prefix):
    """Generate a sequential ID by finding and incrementing the highest existing ID"""
    logger.info(f"Generating sequential ID with prefix '{prefix}' for table: {table_name}")

    table = dynamodb_resource.Table(table_name)

    try:
        response = table.scan(
            ProjectionExpression="id",
            FilterExpression="begins_with(id, :prefix)",
            ExpressionAttributeValues={':prefix': prefix}
        )

        items = response['Items']
        logger.info(f"Found {len(items)} items with prefix {prefix}")

        # Handle pagination
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ProjectionExpression="id",
                FilterExpression="begins_with(id, :prefix)",
                ExpressionAttributeValues={':prefix': prefix},
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            items.extend(response['Items'])

        # Find the highest number
        max_num = 0
        prefix_len = len(prefix)

        for item in items:
            try:
                id_str = item.get('id', '')
                if id_str.startswith(prefix):
                    num_part = id_str[prefix_len:]
                    if num_part.isdigit():
                        current_num = int(num_part)
                        if current_num > max_num:
                            max_num = current_num
            except (ValueError, IndexError) as e:
                logger.error(f"Error parsing ID {item.get('id', '')}: {str(e)}")
                continue

        # Generate new ID
        new_num = max_num + 1
        new_id = f"{prefix}{new_num:03d}"
        logger.info(f"Generated new sequential ID: {new_id}")

        return new_id

    except Exception as e:
        logger.error(f"Error generating sequential ID: {str(e)}")
        # Fallback
        timestamp = int(datetime.now().timestamp())
        fallback_id = f"{prefix}{timestamp}"
        logger.info(f"Using fallback ID with timestamp: {fallback_id}")
        return fallback_id

def process_document_upload(file_content, filename, cloud_id, stage_name="staging", app_name="fusefy", risk_framework_id=None):
    """Process uploaded document and generate AI usecase assessment"""
    try:
        # Validate file type
        file_type = detect_file_type(filename)
        if file_type == 'UNKNOWN':
            return {
                "success": False,
                "message": "Unsupported file type. Please upload PDF, DOCX, or TXT files.",
                "error": "Unsupported file type"
            }

        # Extract text from file
        extraction_result = extract_text_from_uploaded_file(file_content, filename)

        if not extraction_result["success"]:
            return {
                "success": False,
                "message": "Failed to extract text from document",
                "error": extraction_result["error"]
            }

        document_text = extraction_result["text"]
        document_hash = extraction_result["document_hash"]

        if not document_text.strip():
            return {
                "success": False,
                "message": "No text content found in the document",
                "error": "Empty document"
            }

        logger.info(f"Extracted text length: {len(document_text)} characters")
        logger.info(f"Document hash: {document_hash}")

        # Get table names and framework ID
        usecase_table_name, framework_id = get_usecase_assessment_table_and_framework_id(
            app_name, stage_name, cloud_id, dynamodb
        )

        # Check for duplicate document
        usecase_table = dynamodb.Table(usecase_table_name)
        try:
            response = usecase_table.scan(
                FilterExpression=Attr('documentHash').eq(document_hash),
                ProjectionExpression="id, documentHash"
            )
            if response.get('Items'):
                existing_id = response['Items'][0]['id']
                return {
                    "success": False,
                    "message": f"Document already exists with ID: {existing_id}",
                    "error": "Duplicate document detected"
                }
        except Exception as e:
            logger.warning(f"Could not check for duplicates: {e}")

        # Fetch methodology metrics mapping records
        methodology_metrics_mapping_table = f"{stage_name}-{app_name}-methodologyMetricsMapping"
        all_mapping_records = fetch_all_dynamodb_records(methodology_metrics_mapping_table, dynamodb)

        # Generate document summary
        logger.info("Generating document summary...")
        document_summary_result = summarize_document_with_llm(document_text)
        document_summary = document_summary_result["documentSummary"]

        # Determine AI category and approach
        logger.info("Determining AI category and approach...")
        try:
            result = determine_ai_category_and_approach_with_llm(document_text)
            ai_category = result["category"]
            ai_approach = result["approach"]
            logger.info(f"AI category: {ai_category}, AI approach: {ai_approach}")
        except Exception as e:
            logger.error(f"Error in AI category determination: {e}")
            ai_category = "AI Workflow Agents"
            ai_approach = "Custom AI Stack"

        # Generate design document
        logger.info("Generating design document...")
        design_doc_prompt = generate_design_document_prompt(document_text)
        system_prompt = "You are a Solution Architect and Agentic AI Specialist generating a comprehensive technical design document."
        design_doc_content = call_llm(design_doc_prompt, system_prompt, use_json_format=False, max_tokens=7000)

        # Generate enhanced use case using LLM
        logger.info(f"Generating enhanced use case for {ai_category}...")
        cloud_provider = "GCP"
        usecase_data = generate_usecase_with_llm_focused(document_text, ai_category, cloud_provider, all_mapping_records)

        if "error" in usecase_data:
            return {
                "success": False,
                "message": f"Error generating usecase: {usecase_data['error']}",
                "error": usecase_data['error']
            }

        # Generate usecase ID
        usecase_id = generate_sequential_id(dynamodb, usecase_table_name, "AI-UC-AST-")

        # Create comprehensive usecase item
        timestamp = datetime.utcnow().isoformat()

        # Create S3 URL placeholder (you can upload the file to S3 if needed)
        s3url = f"s3://your-bucket/{cloud_id}/{document_hash}/{filename}"

        usecase_item = {
            "id": usecase_id,
            "createdAt": timestamp,
            "updatedAt": timestamp,
            "sourceDocURL": s3url,
            "category": "AI Inventory",
            "processingStatus": "completed",
            "riskframeworkid": risk_framework_id if risk_framework_id else framework_id,
            "aiApproach": ai_approach,
            "aiCategory": ai_category,
            "documentHash": document_hash,
            "documentSummary": document_summary,
            "designDocument": design_doc_content,
            "aiCloudProvider": usecase_data.get("cloudProvider", cloud_provider),
            **{k: v for k, v in usecase_data.items() if k not in ["documserId"]}
        }

        # Save to DynamoDB
        logger.info(f"Saving usecase with ID {usecase_id}...")
        usecase_table.put_item(Item=usecase_item)
        logger.info("Successfully saved usecase")

        return {
            "success": True,
            "message": "Document processed successfully",
            "usecase_id": usecase_id,
            "ai_category": ai_category,
            "document_hash": document_hash
        }

    except Exception as e:
        logger.error(f"Error processing document: {e}")
        return {
            "success": False,
            "message": f"Internal server error: {str(e)}",
            "error": str(e)
        }

def lambda_handler(event, context):
    """
    AWS Lambda handler function
    Supports both API Gateway REST API and direct Lambda invocation
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Determine the request path and method
        http_method = event.get('httpMethod', 'POST')
        path = event.get('path', '/')

        # Handle different endpoints
        if path == '/health' and http_method == 'GET':
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'status': 'healthy',
                    'timestamp': datetime.utcnow().isoformat()
                })
            }

        elif path == '/upload-document' and http_method == 'POST':
            # Handle file upload
            try:
                # Parse the body - it could be base64 encoded from API Gateway
                if event.get('isBase64Encoded', False):
                    body = base64.b64decode(event['body'])
                else:
                    body = event.get('body', '')

                # Parse multipart form data (simplified - you may need a proper parser)
                # For now, assuming the body contains JSON with base64 encoded file
                if isinstance(body, str):
                    body_data = json.loads(body)
                else:
                    body_data = body

                # Extract parameters
                file_content_base64 = body_data.get('file_content')
                filename = body_data.get('filename', 'document.pdf')
                cloud_id = body_data.get('cloud_id')
                stage_name = body_data.get('stage_name', 'staging')
                app_name = body_data.get('app_name', 'fusefy')
                risk_framework_id = body_data.get('risk_framework_id')

                if not file_content_base64:
                    return {
                        'statusCode': 400,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'success': False,
                            'message': 'No file content provided',
                            'error': 'Missing file_content'
                        })
                    }

                if not cloud_id:
                    return {
                        'statusCode': 400,
                        'headers': {
                            'Content-Type': 'application/json',
                            'Access-Control-Allow-Origin': '*'
                        },
                        'body': json.dumps({
                            'success': False,
                            'message': 'cloud_id is required',
                            'error': 'Missing cloud_id'
                        })
                    }

                # Decode file content
                file_content = base64.b64decode(file_content_base64)

                # Process the document
                result = process_document_upload(
                    file_content,
                    filename,
                    cloud_id,
                    stage_name,
                    app_name,
                    risk_framework_id
                )

                status_code = 200 if result['success'] else 400

                return {
                    'statusCode': status_code,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps(result)
                }

            except Exception as e:
                logger.error(f"Error processing upload request: {e}")
                return {
                    'statusCode': 500,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({
                        'success': False,
                        'message': f'Internal server error: {str(e)}',
                        'error': str(e)
                    })
                }

        elif path == '/process-usecase' and http_method == 'POST':
            # Handle S3 URL processing (existing functionality)
            body = json.loads(event.get('body', '{}'))

            # This would implement the S3 processing logic
            # For now, return a placeholder response
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'success': True,
                    'message': 'S3 usecase processing endpoint - implementation pending'
                })
            }

        else:
            # Default root endpoint
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'Fusefy AI Usecase Generator Lambda API',
                    'version': '1.0.0',
                    'endpoints': [
                        'GET /health',
                        'POST /upload-document',
                        'POST /process-usecase'
                    ]
                })
            }

    except Exception as e:
        logger.error(f"Unexpected error in lambda_handler: {e}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'success': False,
                'message': f'Unexpected error: {str(e)}',
                'error': str(e)
            })
        }