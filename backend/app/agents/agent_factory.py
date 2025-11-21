import os
from typing import Optional, List, Dict, Any, AsyncGenerator, Tuple
from abc import ABC
from ibm_watsonx_ai import Credentials
from ibm_watsonx_ai.client import APIClient
from langchain_ibm import ChatWatsonx
from langgraph.prebuilt import create_react_agent
from langchain_core.tools import Tool
from app.services.rate_limiter_service import get_rate_limiter
from .tools import RFPSearchTool
from .prompts import RFP_AGENTIC_RAG


class BaseAgent(ABC):
    """Base class for all watsonx.ai agents with common functionality"""
    
    def __init__(self, model_id: str, temperature: float, max_new_tokens: int, tools: List, system_prompt: str):
        """
        Initialize the base agent
        
        Args:
            model_id: Watson AI model identifier
            temperature: Model temperature parameter
            max_new_tokens: Maximum number of generated tokens
            tools: List of tools for the agent
            system_prompt: System prompt template for the agent
        """
        # Initialize Watson AI client
        url = "https://us-south.ml.cloud.ibm.com"
        project_id = os.environ.get('WX_PROJECT_ID')
        apikey = os.environ.get('WX_API_KEY')
        
        if not project_id or not apikey:
            raise ValueError("WX_PROJECT_ID and WX_API_KEY environment variables are required")
        
        api_client = APIClient(
            credentials=Credentials(url=url, api_key=apikey),
            project_id=project_id
        )
        
        self.chat = ChatWatsonx(
            watsonx_client=api_client,
            model_id=model_id,
            params={
                "temperature": temperature,
                "max_tokens": max_new_tokens,
                "penalty_repetition": 1.1
            },
            rate_limiter=get_rate_limiter()
        )
        
        # Create the LangGraph ReAct agent
        self.agent = create_react_agent(
            self.chat,
            tools=tools,
            prompt=system_prompt
        )
    
    def prepare_messages(self, prompt: Optional[str] = None, messages: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Prepare input messages for the agent
        
        Args:
            prompt: User's question or request
            messages: List of message dictionaries from frontend
            
        Returns:
            Formatted messages list
        """
        if messages:
            return messages
        else:
            return [{"role": "user", "content": prompt or ""}]


class RFPAgent(BaseAgent):
    """Agentic RAG Agent specialized in RFPs"""
    
    def __init__(self):
        # Create RFP search tool instance
        self.rfp_search = RFPSearchTool()
        
        # Create the Tool that will use the RFP search tool
        rag_rfps_tool = Tool(
            name="rag_rfps",
            description="Search for information in RFP documents based on a query",
            func=self.rfp_search.search_rfp
        )
        
        super().__init__(
            model_id="openai/gpt-oss-120b",
            max_new_tokens=4096,
            temperature=0.1,
            tools=[rag_rfps_tool],
            system_prompt=RFP_AGENTIC_RAG
        )
    
    async def ainvoke(self, query: str, project_id: str) -> str:
        """
        Run the agent with the specified project context
        
        Args:
            query: The user's question
            project_id: The project ID to use for retrieval
            
        Returns:
            The agent's response as a string (only the final answer)
        """
        with self.rfp_search.use_project(project_id):
            messages = self.prepare_messages(prompt=query)
            result = await self.agent.ainvoke({"messages": messages})
            
            # Extract only the final answer from the last AI message
            if result and "messages" in result:
                # Find the last AI message
                for message in reversed(result["messages"]):
                    if message.type == "ai":
                        return message.content
            
            # Fallback if we can't extract the answer
            return "No se pudo generar una respuesta."

    async def achat(self, messages: list, project_id: str) -> str:
        """
        Run the conversational agent with the specified project context
        
        Args:
            messages: List of conversation messages
            project_id: The project ID to use for retrieval
            
        Returns:
            The agent's response as a string (only the final answer)
        """
        with self.rfp_search.use_project(project_id):
            result = await self.agent.ainvoke({"messages": messages})
            
            # Extract only the final answer from the last AI message
            if result and "messages" in result:
                # Find the last AI message
                for message in reversed(result["messages"]):
                    if message.type == "ai":
                        return message.content
            
            # Fallback if we can't extract the answer
            return "No se pudo generar una respuesta."
    
    async def astream(self,  messages: list, project_id: str) -> AsyncGenerator[Tuple[str, Dict[str, Any]], None]:
        """
        Stream the agent's response with the specified project context.
        
        Args:
            messages: List of conversation messages
            project_id: The project ID to use for retrieval
            
        Yields:
            Tuples of (chunk_text, metadata) where metadata contains information about the chunk
        """
        with self.rfp_search.use_project(project_id):
            # Stream the agent's response
            stream = self.agent.astream(
                {"messages": messages},
                stream_mode=["updates", "messages"]
            )

            last_tool_name = None
            current_content = ""
            
            async for mode, chunk in stream:
                if mode == "updates":
                    # Handle tool calls and other updates
                    if 'agent' in chunk:
                        message = chunk['agent']['messages'][0]
                        if hasattr(message, 'tool_calls') and message.tool_calls:
                            tool = message.tool_calls[0]
                            tool_name = tool['name']
                            last_tool_name = tool_name
                            tool_args = ', '.join(tool['args'].values())
                            
                            # Yield tool usage information
                            # Format tool arguments for display
                            tool_args_str = ', '.join(tool['args'].values())
                            
                            metadata = {
                                "type": "tool_call",
                                "tool_name": tool_name,
                                "tool_args": tool_args_str
                            }
                            yield f"🔍 Buscando información con {tool_name}: '{tool_args_str}'", metadata
                    
                    elif 'tools' in chunk:
                        # Tool execution completed
                        metadata = {
                            "type": "tool_result",
                            "tool_name": last_tool_name,
                            "tool_output": chunk['tools']['messages'][0].content
                        }
                        yield f"🧠 Analizando información de {last_tool_name}...", metadata
                
                elif mode == "messages":
                    # Handle content chunks
                    if chunk[0].content and chunk[0].type != "tool":
                        content_chunk = chunk[0].content
                        current_content += content_chunk
                        
                        metadata = {
                            "type": "content",
                            "done": False
                        }
                        yield content_chunk, metadata
            
            # Final chunk with done=True
            metadata = {
                "type": "content",
                "done": True
            }
            yield "", metadata