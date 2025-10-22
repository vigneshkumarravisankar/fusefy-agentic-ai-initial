import json
import os 
from typing import Optional

from google.adk.agents import Agent
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_session_manager import StdioConnectionParams
from mcp import StdioServerParameters

from .prompt import CONTROLS_PROMPT, FRAMEWORKS_PROMPT, FRAMEWORK_CONTROLS_PROMPT, FUSEFY_GREETING, DYNAMODB_PROMPT

# Verify GOOGLE_API_KEY is available in environment
google_api_key = os.getenv("GOOGLE_API_KEY")
if google_api_key is None:
    raise ValueError("GOOGLE_API_KEY environment variable is not set")


class FusefyAgentManager:
    """
    Fusefy AI Adoption as a Service Platform Agent Manager
    
    Fusefy is a next-generation Enterprise AI Consulting and Delivery Platform 
    designed to accelerate safe, scalable, and trustworthy AI adoption across organizations.
    """
    
    def __init__(self, stage_name: str = "staging", app_name: str = "fusefy"):
        self.stage_name = stage_name
        self.app_name = app_name
        
        # Generate table names based on stage and app
        self.controls_table = f"{stage_name}-{app_name}-controls"
        self.frameworks_table = f"{stage_name}-{app_name}-frameworks"
        self.framework_controls_table = f"{stage_name}-{app_name}-frameworkControls"
        
        # Display greeting message
        print(self._get_greeting_message())
        
        # Initialize agents
        self.controls_agent = self._create_controls_agent()
        self.frameworks_agent = self._create_frameworks_agent()
        self.framework_controls_agent = self._create_framework_controls_agent()
    
    def _get_greeting_message(self) -> str:
        """Get Fusefy welcome greeting message"""
        return f"""
🚀 Welcome to Fusefy - AI Adoption as a Service Platform! 🚀

Environment: {self.stage_name.upper()}
Application: {self.app_name.title()}

🔧 Agent Configuration:
├── Controls Agent: {self.controls_table}
├── Frameworks Agent: {self.frameworks_table}
└── Framework Controls Agent: {self.framework_controls_table}

🎯 Ready to assist with AI governance, compliance, and trustworthy AI implementation!
Type 'help' for available commands or start asking questions about AI controls, frameworks, or mappings.
        """
    
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
        """Create AI Controls agent for Fusefy"""
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
- **F**easibility: Assessing technical and business viability
- **U**sability: Ensuring user-centric design and adoption  
- **S**ecurity: Implementing robust security and compliance
- **E**xplainability: Maintaining transparency and interpretability

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
        
        return Agent(
            name="Fusefy_Controls_Agent",
            model="gemini-2.0-flash-exp",
            instruction=controls_instruction,
            tools=[self._create_mcp_toolset(self.controls_table)]
        )
    
    def _create_frameworks_agent(self) -> Agent:
        """Create AI Frameworks agent for Fusefy"""
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

🌐 **Supported Global Frameworks**:

**Regulatory Frameworks:**
- EU AI Act (European Union) - Risk-based classification, compliance obligations
- China Gen AI Law - Censorship, accountability, transparency  
- Algorithm Law (China) - Fairness in recommendations, user control

**Voluntary Guidelines:**
- NIST AI RMF (USA) - Risk management, trust, documentation
- UK AI Framework - Pro-innovation, sector-specific principles
- CHAI (USA) - Human-compatible AI, safety research

**Security & Standards:**
- OWASP LLM Top 10 (Global) - LLM-specific risks and countermeasures
- ISO 5338 (Global) - AI lifecycle governance standard

🎯 **Key Framework Functions**:
- Cross-framework alignment and harmonization
- Regulatory compliance mapping and gap analysis
- Implementation guidance and best practices
- Risk assessment and mitigation strategies
"""
        
        return Agent(
            name="Fusefy_Frameworks_Agent",
            model="gemini-2.0-flash-exp",
            instruction=frameworks_instruction,
            tools=[self._create_mcp_toolset(self.frameworks_table)]
        )
    
    def _create_framework_controls_agent(self) -> Agent:
        """Create Framework Controls mapping agent for Fusefy"""
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
        
        return Agent(
            name="Fusefy_FrameworkControls_Agent",
            model="gemini-2.0-flash-exp",
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
        """Display available commands and capabilities"""
        return f"""
🔧 **Fusefy Agent Manager - Available Commands**

**Agent Operations:**
├── chat_with_controls(message) - Interact with AI Controls agent
├── chat_with_frameworks(message) - Interact with AI Frameworks agent  
├── chat_with_framework_controls(message) - Interact with Framework Controls agent
└── get_agent(type) - Get specific agent instance

**Example Queries:**

🛡️ **AI Controls:**
- "Show me all bias mitigation controls"
- "List controls for data privacy compliance"
- "Find high-risk controls requiring immediate attention"

🌐 **AI Frameworks:** 
- "Compare EU AI Act vs NIST framework requirements"
- "Show all regulatory frameworks for healthcare AI"
- "List voluntary vs mandatory compliance frameworks"

🔗 **Framework Controls Mapping:**
- "Map GDPR controls to EU AI Act requirements" 
- "Show compliance gaps for NIST framework"
- "Find overlapping controls across multiple frameworks"

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


# Factory function for easy agent creation
def create_fusefy_agents(stage_name: str = "staging", app_name: str = "fusefy") -> FusefyAgentManager:
    """
    Create Fusefy agent manager with specified stage and app name
    
    Args:
        stage_name: Environment stage (dev, staging, prod)
        app_name: Application name (default: fusefy)
        
    Returns:
        FusefyAgentManager: Configured agent manager instance
    """
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
    """
    Fusefy Root Agent - Intelligent Query Router
    
    This agent analyzes user queries and routes them to the appropriate specialized agent:
    - Controls queries → Controls Agent
    - Frameworks queries → Frameworks Agent  
    - Framework Controls mapping queries → Framework Controls Agent
    """
    
    def __init__(self, stage_name: str = "staging", app_name: str = "fusefy"):
        self.stage_name = stage_name
        self.app_name = app_name
        self.agent_manager = FusefyAgentManager(stage_name, app_name)
        
        # Keywords for routing logic
        self.controls_keywords = [
            "control", "controls", "bias", "mitigation", "security", "audit", "governance",
            "compliance", "risk", "technical control", "procedural control", "administrative control",
            "access control", "monitoring", "oversight", "human-in-the-loop", "explainability",
            "transparency", "accountability", "privacy", "data protection", "incident response"
        ]
        
        self.frameworks_keywords = [
            "framework", "frameworks", "nist", "eu ai act", "chai", "owasp", "iso", "regulation",
            "regulatory", "voluntary", "guideline", "standard", "china gen ai", "algorithm law",
            "uk ai framework", "security standard", "research framework", "compliance framework",
            "regulatory framework", "voluntary guideline"
        ]
        
        self.mapping_keywords = [
            "mapping", "map", "relationship", "coverage", "gap", "alignment", "cross-framework",
            "framework control", "framework controls", "control mapping", "compliance gap",
            "coverage analysis", "overlap", "framework alignment", "control-to-framework"
        ]
    
    def _analyze_query(self, query: str) -> str:
        """
        Analyze query to determine which agent should handle it
        
        Returns: 'controls', 'frameworks', 'framework_controls', or 'general'
        """
        query_lower = query.lower()
        
        # Count keyword matches
        controls_score = sum(1 for keyword in self.controls_keywords if keyword in query_lower)
        frameworks_score = sum(1 for keyword in self.frameworks_keywords if keyword in query_lower)
        mapping_score = sum(1 for keyword in self.mapping_keywords if keyword in query_lower)
        
        # Prioritize mapping queries first (most specific)
        if mapping_score > 0 or any(word in query_lower for word in ["map", "mapping", "relationship", "coverage", "gap"]):
            return "framework_controls"
        
        # Then frameworks
        if frameworks_score > controls_score:
            return "frameworks"
        
        # Then controls
        if controls_score > 0:
            return "controls"
        
        # Default to controls for general queries
        return "controls"
    
    def chat(self, message: str) -> str:
        """
        Main chat interface that routes queries to appropriate agents
        """
        # Handle help requests
        if message.lower().strip() in ["help", "?", "commands", "what can you do"]:
            return self._get_help_message()
        
        # Analyze query and route to appropriate agent
        agent_type = self._analyze_query(message)
        
        # Add routing context to the message
        routing_context = f"""
Query Analysis: This appears to be a {agent_type.replace('_', ' ')} related question.
Routing to: {agent_type.title().replace('_', ' ')} Agent

Original Query: {message}
"""
        
        try:
            if agent_type == "controls":
                response = self.agent_manager.chat_with_controls(message)
                return f"🛡️ **AI Controls Response:**\n\n{response}"
            
            elif agent_type == "frameworks":
                response = self.agent_manager.chat_with_frameworks(message)
                return f"🌐 **AI Frameworks Response:**\n\n{response}"
            
            elif agent_type == "framework_controls":
                response = self.agent_manager.chat_with_framework_controls(message)
                return f"🔗 **Framework Controls Response:**\n\n{response}"
            
            else:
                # Default to controls agent for general queries
                response = self.agent_manager.chat_with_controls(message)
                return f"🛡️ **AI Controls Response (Default):**\n\n{response}"
                
        except Exception as e:
            return f"❌ **Error routing query:** {str(e)}\n\nPlease try rephrasing your question or contact support."
    
    def _get_help_message(self) -> str:
        """Return comprehensive help message"""
        return f"""
        {FUSEFY_GREETING}

        🤖 **Fusefy AI Assistant - Intelligent Query Router**

        I automatically analyze your questions and route them to the most appropriate specialist:

        🛡️ **AI Controls Queries** - Routed to Controls Agent:
        Examples: "Show bias mitigation controls", "List security controls", "Find high-risk controls"

        🌐 **AI Frameworks Queries** - Routed to Frameworks Agent:  
        Examples: "Compare NIST vs EU AI Act", "Show regulatory frameworks", "List voluntary guidelines"

        🔗 **Framework Controls Mapping** - Routed to Framework Controls Agent:
        Examples: "Map GDPR to controls", "Show compliance gaps", "Framework coverage analysis"

        📊 **Current Configuration:**
        ├── Environment: {self.stage_name.upper()}
        ├── Application: {self.app_name.title()}
        ├── Controls Table: {self.agent_manager.controls_table}
        ├── Frameworks Table: {self.agent_manager.frameworks_table}
        └── Framework Controls Table: {self.agent_manager.framework_controls_table}

        💡 **Pro Tips:**
        - Ask specific questions for better routing
        - Use keywords like "control", "framework", "mapping" for precise routing
        - I'll automatically determine the best agent to handle your query

        🚀 **Ready to help with AI governance, compliance, and trustworthy AI implementation!**
        """

# Create ADK-compatible root agent that uses Fusefy routing logic
def create_adk_root_agent(stage_name: str = "staging", app_name: str = "fusefy") -> Agent:
    """
    Create ADK-compatible root agent with Fusefy routing capabilities
    """
    
    # Create the routing system
    # fusefy_router = FusefyRootAgent(stage_name, app_name)
    
    # Create instruction that explains the routing system
    root_instruction = f"""{FUSEFY_GREETING}

    🤖 **Fusefy AI Assistant - Intelligent Query Router**

    You are the main entry point for the Fusefy AI Adoption as a Service Platform. Your role is to:

    1. **Understand User Queries**: Analyze what the user is asking about
    2. **Route Intelligently**: Determine if the query is about:
    - 🛡️ **AI Controls** (security, governance, compliance, risk management)
    - 🌐 **AI Frameworks** (NIST, EU AI Act, regulations, standards)  
    - 🔗 **Framework Controls Mapping** (relationships, coverage, gaps, alignment)

    3. **Provide Contextual Help**: Guide users on available capabilities

    **Current Configuration:**
    ├── Environment: {stage_name.upper()}
    ├── Application: {app_name.title()}
    ├── Controls Table: {stage_name}-{app_name}-controls
    ├── Frameworks Table: {stage_name}-{app_name}-frameworks
    └── Framework Controls Table: {stage_name}-{app_name}-frameworkControls

    **Available Tables and Operations:**
    - Query and scan DynamoDB tables for comprehensive data retrieval
    - Present results in structured, readable formats
    - Provide actionable insights and recommendations
    - Support compliance analysis and gap assessments

    **Instructions:**
    When users ask questions, use your DynamoDB tools to:
    1. Scan the appropriate tables based on query content
    2. Retrieve comprehensive data matching the user's request  
    3. Present results in organized, easy-to-read formats with Fusefy branding
    4. Provide actionable insights and recommendations based on the data
    5. NEVER show raw IDs or technical failure messages to users
    6. Always provide business-friendly, Fusefy-branded responses

    **Response Guidelines:**
    - Use Fusefy terminology and context in all responses
    - Present data in business-friendly language, not technical database terms
    - Hide technical details like IDs, error codes, and raw database responses
    - Frame everything in terms of AI governance, compliance, and trustworthy AI
    - Provide actionable recommendations aligned with the FUSE methodology
    - Use emojis and formatting to make responses engaging and professional

    **Framework-Controls Relationship Handling:**
    When users ask about relationships between frameworks and controls:
    1. Query the frameworkControls table to get frameworkId and controlId pairs
    2. For each frameworkId, lookup the framework name/details in the frameworks table
    3. For each controlId, lookup the control name/details in the controls table
    4. Present results showing framework names and control names, NEVER raw IDs
    5. Provide insights about coverage, gaps, and compliance implications

    **Query Routing Guidelines:**
    - Controls queries: bias, security, governance, compliance, risk, monitoring
    - Frameworks queries: NIST, EU AI Act, regulations, standards, guidelines
    - Mapping queries: relationships, coverage, gaps, alignment, cross-framework

    **Error Handling:**
    - If tables are empty, say "No data available yet in your Fusefy environment"
    - If queries fail or timeout, say "We're working to retrieve your AI governance data. Please try again in a moment."
    - For connection timeouts, say "Your Fusefy AI governance system is initializing. Please wait a moment and try again."
    - Never show raw error messages, timeout errors, or technical failures
    - Always maintain a professional, helpful Fusefy tone
    - Provide actionable guidance when possible (e.g., "Try a more specific query")

    Always be proactive in retrieving ALL relevant data and presenting it in a Fusefy-branded, business-friendly manner.
    """
    
    # Create agent with all three MCP toolsets for complete access
    return Agent(
        name="Fusefy_Root_Agent",
        model="gemini-2.0-flash-exp",
        instruction=root_instruction,
        tools=[
            # Controls table access
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
            # Frameworks table access
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
            # Framework Controls table access
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

# Health check function
def check_fusefy_connection(stage_name: str = "staging", app_name: str = "fusefy") -> dict:
    """
    Check the health of Fusefy agent connections
    
    Returns:
        dict: Status of each table connection
    """
    status = {
        "controls": "unknown",
        "frameworks": "unknown", 
        "frameworkControls": "unknown",
        "overall": "unknown"
    }
    
    try:
        # Test basic environment variables
        if not os.getenv("AWS_ACCESS_ID") or not os.getenv("AWS_SECRET_ACCESS_KEY"):
            status["overall"] = "AWS credentials not configured"
            return status
            
        if not os.getenv("GOOGLE_API_KEY"):
            status["overall"] = "Google API key not configured"
            return status
            
        status["overall"] = "Environment configured - ready for queries"
        status["controls"] = f"Ready: {stage_name}-{app_name}-controls"
        status["frameworks"] = f"Ready: {stage_name}-{app_name}-frameworks"
        status["frameworkControls"] = f"Ready: {stage_name}-{app_name}-frameworkControls"
        
    except Exception as e:
        status["overall"] = f"Configuration check failed: {str(e)}"
    
    return status

# Create the ADK-compatible root agent
root_agent = create_adk_root_agent("staging", "fusefy")

# Convenience function for direct root agent access
def create_fusefy_root_agent(stage_name: str = "staging", app_name: str = "fusefy") -> FusefyRootAgent:
    """
    Create Fusefy root agent with intelligent query routing
    
    Args:
        stage_name: Environment stage (dev, staging, prod)
        app_name: Application name (default: fusefy)
        
    Returns:
        FusefyRootAgent: Root agent with automatic query routing
    """
    return FusefyRootAgent(stage_name, app_name)

