import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Add the backend directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

from app.agents.agent_factory import RFPAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)
logger.level = logging.ERROR

async def test_agent() -> None:
    """
    Test the RFP agent directly
    """
    # Find the first available project
    project_id: str = "proj_6046829a_a22d_4465_9461_2c209ca07234"
    
    # Create the agent
    logger.info("Creating RFP agent...")
    agent = RFPAgent()
    
    # Sample query about the RFP
    query = "Se permite subcontratar parte del trabajo según la licitación?"
    messages = agent.prepare_messages(query)
    
    # Process the query
    logger.info(f"Processing query: '{query}'")
    try:
        with agent.rfp_search.use_project(project_id):
            stream = agent.agent.stream(
                {"messages": messages},
                stream_mode=["updates", "messages"], 
            )
            last_tool_name = None
            for mode, chunk in stream:
                if mode == "updates":
                    # chunk is a dict like {'node_name': {...}}
                    if 'agent' in chunk:
                        chunk = chunk['agent']['messages'][0]
                        if chunk.tool_calls:
                            tool = chunk.tool_calls[0]
                            tool_name = tool['name']
                            last_tool_name = tool_name
                            tool_args = ', '.join(tool['args'].values())
                            print(f"Calling Tool '{tool_name}' with arguments '{tool_args}'")
                    elif 'tools' in chunk:
                        print(f'Analyzing extracted information from {last_tool_name}')

                elif mode == "messages":
                    # chunk is (message_token, metadata)
                    if chunk[0].content and chunk[0].type != 'tool':
                        print(chunk[0].content, end="", flush=True)
            
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_agent())
