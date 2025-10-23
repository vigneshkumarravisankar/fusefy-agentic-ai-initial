import json
import os 
from typing import Optional

from google.adk.agents import Agent, LlmAgent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters
from google.adk.models.lite_llm import LiteLlm
from .prompt import CONTROLS_PROMPT, FRAMEWORKS_PROMPT, FRAMEWORK_CONTROLS_PROMPT, FUSEFY_GREETING, DYNAMODB_PROMPT




openai_api_key = os.getenv("OPENAI_API_KEY")
if openai_api_key is None:
    raise ValueError("OPENAI_API_KEY environment variable is not set")


class FusefyAgentManager:
    def __init__(self, stage_name: str = "staging", app_name: str = "fusefy"):
        self.stage_name = stage_name
        self.app_name = app_name
        self.controls_table = f"{stage_name}-{app_name}-controls"
        self.frameworks_table = f"{stage_name}-{app_name}-frameworks"
        self.framework_controls_table = f"{stage_name}-{app_name}-frameworkControls"
        
        # Initialize agents
        self.controls_agent = self._create_controls_agent()
        self.frameworks_agent = self._create_frameworks_agent()
        self.framework_controls_agent = self._create_framework_controls_agent()
    
    
    def _create_mcp_toolset(self, table_name: str) -> MCPToolset:
        """Create MCP toolset with specific table context"""
        return MCPToolset(
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
                        "DDB_MCP_READONLY": "true",
                        "PRIMARY_TABLE": table_name,
                        "MCP_TIMEOUT": "30",
                        "CONNECTION_TIMEOUT": "10"
                    },
                )
            )
        )
    
    def _create_controls_agent(self) -> Agent:
        controls_instruction = f"""{FUSEFY_GREETING}

        {CONTROLS_PROMPT}
                
        Application Context: Fusefy - AI Adoption as a Service Platform
        Primary Table: {self.controls_table}
        Stage: {self.stage_name}
        Module: AI Controls Management

        🎯 **Your Role**: AI Controls Specialist for Fusefy Platform

        You are working with AI Controls in the Fusefy application, specifically within the AI Audit Suite component. 
        AI controls are policies, processes, and technical measures that ensure AI systems operate safely, ethically, 
        and in compliance with organizational and regulatory standards.

        🏗️ **Fusefy Context**: 
        Fusefy operates on the FUSE Methodology:
        - Feasibility: Assessing technical and business viability
        - Usability: Ensuring user-centric design and adoption  
        - Security: Implementing robust security and compliance
        - Explainability: Maintaining transparency and interpretability

        🎯 **Focus Areas for AI Controls**:
        - Risk mitigation (bias, discrimination, explainability)
        - Standardized governance across AI projects
        - Transparency through control IDs and lifecycle stages
        - Regulatory readiness and compliance (GDPR, SOC 2, EU AI Act)
        - Accountability with trustworthy AI focus
        - Risk prioritization through visible ratings

        🔧 **Control Categories**:
        - Technical Controls: Access controls, encryption, monitoring
        - Procedural Controls: Audit processes, approval workflows
        - Administrative Controls: Training, policies, governance
        """
        
        return LlmAgent(
            name="Fusefy_Controls_Agent",
            model=LiteLlm(model="openai/gpt-4o"),
            instruction=controls_instruction,
            tools=[self._create_mcp_toolset(self.controls_table)]
        )
    
    def _create_frameworks_agent(self) -> Agent:
        frameworks_instruction = f"""{FUSEFY_GREETING}

        {FRAMEWORKS_PROMPT}
                
        Application Context: Fusefy - AI Adoption as a Service Platform
        Primary Table: {self.frameworks_table}
        Stage: {self.stage_name}
        Module: AI Frameworks Management

        🎯 **Your Role**: AI Frameworks Specialist for Fusefy Platform

        You are working with AI Frameworks in the Fusefy application, supporting all three core offerings:
        1. 💡 AI Ideation Studio - Framework guidance for use case planning
        2. 🏭 AI Factory - Framework compliance during development
        3. 🧾 AI Audit Suite - Framework validation and monitoring

        🌐 **Supported Global Frameworks**: EU AI Act, China Gen AI Law, Algorithm Law, NIST AI RMF, UK AI Framework, CHAI, OWASP LLM Top 10, ISO 5338

        🎯 **Key Framework Functions**:
        - Cross-framework alignment and harmonization
        - Regulatory compliance mapping and gap analysis
        - Implementation guidance and best practices
        - Risk assessment and mitigation strategies
        """
        
        return LlmAgent(
            name="Fusefy_Frameworks_Agent",
            model=LiteLlm(model="openai/gpt-4o"),
            instruction=frameworks_instruction,
            tools=[self._create_mcp_toolset(self.frameworks_table)]
        )
    
    def _create_framework_controls_agent(self) -> Agent:
        framework_controls_instruction = f"""{FUSEFY_GREETING}

        {FRAMEWORK_CONTROLS_PROMPT}
                
        Application Context: Fusefy - AI Adoption as a Service Platform
        Primary Table: {self.framework_controls_table}
        Stage: {self.stage_name}
        Module: Framework Controls Mapping

        🎯 **Your Role**: Framework Controls Mapping Specialist for Fusefy Platform

        You are working with Framework Controls mappings in the Fusefy application, bridging the gap between 
        AI controls and regulatory frameworks. This is crucial for Fusefy's AI Audit Suite and compliance validation.

        🔗 **Mapping Relationships**:
        - Controls Table: {self.controls_table}
        - Frameworks Table: {self.frameworks_table}  
        - Current Table: {self.framework_controls_table}

        🎯 **Core Mapping Functions**:
        - **Control-to-Framework Mapping**: Link specific controls to applicable frameworks
        - **Compliance Gap Analysis**: Identify missing controls for framework requirements
        - **Coverage Assessment**: Evaluate framework implementation completeness
        - **Cross-Framework Alignment**: Find overlapping requirements across frameworks
        - **Risk-Based Prioritization**: Map controls based on risk levels and framework criticality

        🏗️ **Fusefy Integration Points**:
        - **AI Ideation Studio**: Framework requirements during use case planning
        - **AI Factory**: Automated compliance checks during development
        - **AI Audit Suite**: Continuous monitoring and compliance reporting

        🎯 **Mapping Considerations**:
        - One control may satisfy multiple framework requirements
        - Complex frameworks may need multiple coordinated controls  
        - Regional compliance variations (EU vs US vs China requirements)
        - Industry-specific adaptations (Healthcare, Finance, etc.)
        """
        
        return LlmAgent(
            name="Fusefy_FrameworkControls_Agent",
            model=LiteLlm(model="openai/gpt-4o"),
            instruction=framework_controls_instruction,
            tools=[self._create_mcp_toolset(self.framework_controls_table)]
        )
    
    def get_agent(self, agent_type: str) -> Agent:
        """Get specific agent by type"""
        agents = {
            "controls": self.controls_agent,
            "frameworks": self.frameworks_agent,
            "framework_controls": self.framework_controls_agent,
            "frameworkControls": self.framework_controls_agent  # Alternative naming
        }
        
        if agent_type not in agents:
            raise ValueError(f"Unknown agent type: {agent_type}. Available: {list(agents.keys())}")
        
        return agents[agent_type]
    
    def show_help(self) -> str:
        return f"""
            🔧 **Fusefy Agent Manager - Available Commands**

            **Agent Operations:**
            ├── chat_with_controls(message) - Interact with AI Controls agent
            ├── chat_with_frameworks(message) - Interact with AI Frameworks agent  
            ├── chat_with_framework_controls(message) - Interact with Framework Controls agent
            ├── get_framework_controls(framework_name) - Get controls for specific framework
            ├── get_control_frameworks(control_name) - Get frameworks for specific control
            └── get_agent(type) - Get specific agent instance

            

            **Table Configuration:**
            ├── Controls: {self.controls_table}
            ├── Frameworks: {self.frameworks_table}
            └── Framework Controls: {self.framework_controls_table}
        """
    
    def chat_with_controls(self, message: str) -> str:
        """Chat with AI Controls agent"""
        return self.controls_agent.chat(message)
    
    def chat_with_frameworks(self, message: str) -> str:
        """Chat with AI Frameworks agent"""
        return self.frameworks_agent.chat(message)
    
    def chat_with_framework_controls(self, message: str) -> str:
        """Chat with Framework Controls agent"""
        return self.framework_controls_agent.chat(message)
    
    def get_framework_controls(self, framework_name: str) -> str:
        """
        Specialized method to get controls attached to a specific framework
        This demonstrates the 3-table lookup process you described
        """
        query = f"List all controls attached to the {framework_name} framework. Follow the process: 1) Find the framework in frameworks table, 2) Get its ID, 3) Query frameworkControls table for that frameworkId, 4) Get control details from controls table, 5) Present with framework name and control names (not IDs)."
        return self.chat_with_framework_controls(query)
    
    def get_control_frameworks(self, control_name: str) -> str:
        """
        Specialized method to get frameworks attached to a specific control (reverse lookup)
        """
        query = f"List all frameworks that use the '{control_name}' control. Follow the process: 1) Find the control in controls table, 2) Get its ID, 3) Query frameworkControls table for that controlId, 4) Get framework details from frameworks table, 5) Present with control name and framework names (not IDs)."
        return self.chat_with_framework_controls(query)


# Factory function for easy agent creation
def create_fusefy_agents(stage_name: str = "staging", app_name: str = "fusefy") -> FusefyAgentManager:
    return FusefyAgentManager(stage_name, app_name)


# Individual agent creation functions for backward compatibility  
def create_controls_agent(stage_name: str = "staging", app_name: str = "fusefy") -> Agent:
    """Create standalone AI Controls agent"""
    manager = FusefyAgentManager(stage_name, app_name)
    return manager.controls_agent


def create_frameworks_agent(stage_name: str = "staging", app_name: str = "fusefy") -> Agent:
    """Create standalone AI Frameworks agent"""
    manager = FusefyAgentManager(stage_name, app_name)
    return manager.frameworks_agent


def create_framework_controls_agent(stage_name: str = "staging", app_name: str = "fusefy") -> Agent:
    """Create standalone Framework Controls agent"""
    manager = FusefyAgentManager(stage_name, app_name)
    return manager.framework_controls_agent


class FusefyRootAgent:    
    def __init__(self, stage_name: str = "staging", app_name: str = "fusefy"):
        self.stage_name = stage_name
        self.app_name = app_name
        self.unified_agent = create_adk_root_agent(stage_name, app_name)
    
    def chat(self, message: str) -> str:
        """
        Main chat interface using unified agent with access to all tables
        """
        if message.lower().strip() in ["help", "?", "commands", "what can you do"]:
            return self._get_help_message()
        
        try:
            # Use unified agent that has access to all three tables
            response = self.unified_agent.chat(message)
            return response
                
        except Exception as e:
            return f"❌ **Error processing query:** {str(e)}\n\nPlease try rephrasing your question or contact support."
    
    def _get_help_message(self) -> str:
        """Return comprehensive help message"""
        return f"""
        {FUSEFY_GREETING}

        🤖 **Fusefy AI Assistant - Intelligent AI Governance Assistant**

        I can help you with any questions about AI controls, frameworks, and their relationships.
        I have access to all your AI governance data and can intelligently understand what you need.

        **Example Queries:**

        🛡️ **AI Controls:**
        - "Listing Controls
        - "Find high-risk controls requiring immediate attention"

        🌐 **AI Frameworks:**
        - "Show regulatory frameworks"
        - "List voluntary guidelines"

        🔗 **Framework-Control Relationships:**
        - "List controls attached to a particular framework"
        - "What frameworks use bias detection controls?"

        📊 **Current Configuration:**
        ├── Environment: {self.stage_name.upper()}
        ├── Application: {self.app_name.title()}
        ├── Controls Table: {self.stage_name}-{self.app_name}-controls
        ├── Frameworks Table: {self.stage_name}-{self.app_name}-frameworks
        └── Framework Controls Table: {self.stage_name}-{self.app_name}-frameworkControls

        💡 **How it works:**
        - Ask any question in natural language
        - I'll intelligently determine what data you need
        - I have access to all three tables for comprehensive analysis
        - No need to specify which "agent" to use - just ask!

        🚀 **Ready to help with AI governance, compliance, and trustworthy AI implementation!**
        """

def create_adk_root_agent(stage_name: str = "staging", app_name: str = "fusefy") -> Agent:
    """
    Create ADK-compatible root agent with Fusefy routing capabilities
    """
    
    root_instruction = f"""{FUSEFY_GREETING}

    🤖 **Fusefy AI Assistant - Intelligent Query Router**

    You are the main entry point for the Fusefy AI Adoption as a Service Platform. Your role is to:

    1. **Understand User Queries**: Analyze what the user is asking about
    2. **Route Intelligently**: Determine if the query is about:
    - 🛡️ **AI Controls** (security, governance, compliance, risk management)
    - 🌐 **AI Frameworks** (NIST, EU AI Act, regulations, standards)  
    - 🔗 **Framework Controls Mapping** (relationships, coverage, gaps, alignment)

    **Current Configuration:**
    ├── Environment: {stage_name.upper()}
    ├── Application: {app_name.title()}
    ├── Controls Table: {stage_name}-{app_name}-controls
    ├── Frameworks Table: {stage_name}-{app_name}-frameworks
    └── Framework Controls Table: {stage_name}-{app_name}-frameworkControls

    **Available Tables and Operations:**
    - Query and scan DynamoDB tables for comprehensive data retrieval
    - Present results in structured, readable formats

    **Instructions:**
    When users ask questions, use your DynamoDB tools to:
    1. Scan the appropriate tables based on query content
    2. Retrieve comprehensive data matching the user's request  
    3. Present results in organized, easy-to-read formats with Fusefy branding

    **Framework-Controls Relationship Handling:**
    When users ask about relationships between frameworks and controls (e.g., "list controls attached to NIST AI framework"):
    
    **Process for "List controls attached to [framework]":**
    1. 🔍 **Find Framework**: Query frameworks table to locate framework by name (support partial matching)
    2. 📋 **Get Framework ID**: Extract the framework ID from the result
    3. 🔗 **Find Relationships**: Query frameworkControls table for all entries with that frameworkId
    4. 🛡️ **Get Control Details**: For each controlId found, query controls table to get control information
    5. 📊 **Present Results**: Show framework name + complete list of controls with names (NEVER raw IDs)
    
    **Process for "List frameworks attached to [control]" (reverse):**
    1. 🔍 **Find Control**: Query controls table to locate control by name
    2. 📋 **Get Control ID**: Extract the control ID from the result
    3. 🔗 **Find Relationships**: Query frameworkControls table for all entries with that controlId  
    4. 🌐 **Get Framework Details**: For each frameworkId found, query frameworks table
    5. 📊 **Present Results**: Show control name + all associated frameworks with names
    
    **Always follow this 3-table lookup process:**
    - Table 1: Find the primary entity (framework or control)
    - Table 2: Query frameworkControls for relationships
    - Table 3: Lookup details of related entities
    - Present: Human-readable names and comprehensive analysis

    **Error Handling:**
    - If tables are empty, say "No data available yet in your Fusefy environment"
    - If queries fail or timeout, say "We're working to retrieve your AI governance data. Please try again in a moment."
    - For connection timeouts, say "Your Fusefy AI governance system is initializing. Please wait a moment and try again."
    - Never show raw error messages, timeout errors, or technical failures
    """
    
    return LlmAgent(
        name="Fusefy_Root_Agent",
        model=LiteLlm(model="openai/gpt-4o"),
        instruction=root_instruction,
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
                            "DDB_MCP_READONLY": "true",
                            "PRIMARY_TABLE": f"{stage_name}-{app_name}-controls",
                            "MCP_TIMEOUT": "30",
                            "CONNECTION_TIMEOUT": "10"
                        },
                    )
                )
            ),
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
                            "DDB_MCP_READONLY": "true",
                            "PRIMARY_TABLE": f"{stage_name}-{app_name}-frameworks",
                            "MCP_TIMEOUT": "30",
                            "CONNECTION_TIMEOUT": "10"
                        },
                    )
                )
            ),
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
                            "DDB_MCP_READONLY": "true",
                            "PRIMARY_TABLE": f"{stage_name}-{app_name}-frameworkControls",
                            "MCP_TIMEOUT": "30",
                            "CONNECTION_TIMEOUT": "10"
                        },
                    )
                )
            ),
        ],
    )

# Create the ADK-compatible root agent
root_agent = create_adk_root_agent("staging", "fusefy")


