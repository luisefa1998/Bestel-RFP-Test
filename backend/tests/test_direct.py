import asyncio
import os
import sys
import logging
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Add the backend directory to the path so we can import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.agents.agent_factory import RFPAgent

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)


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
    
    # Process the query
    logger.info(f"Processing query: '{query}'")
    try:
            # Get the response from the chat model
            response = await agent.ainvoke(query, project_id)
            
            # Print the result
            logger.info("Agent response:")
            print("\n" + "-" * 80)
            print(response)
            print("-" * 80 + "\n")
            
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")

if __name__ == "__main__":
    # Run the test
    asyncio.run(test_agent())

# Made with Bob
