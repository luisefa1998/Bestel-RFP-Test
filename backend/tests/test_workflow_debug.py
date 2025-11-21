"""
Debug script to test the hierarchical summarization workflow directly.
Run this to see detailed logs without going through the API/Celery.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add backend to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    # handlers=[
    #     logging.StreamHandler(),
    #     logging.FileHandler('logs/workflow_debug.log')
    # ]
)

# Set our app loggers to DEBUG
logging.getLogger('app.workflows').setLevel(logging.DEBUG)
logging.getLogger('__main__').setLevel(logging.INFO)

# Reduce verbosity of HTTP libraries
logging.getLogger('httpx').setLevel(logging.WARNING)
logging.getLogger('httpcore').setLevel(logging.WARNING)
logging.getLogger('ibm_watsonx_ai').setLevel(logging.WARNING)
logging.getLogger('urllib3').setLevel(logging.WARNING)
logging.getLogger('asyncio').setLevel(logging.WARNING)

logger = logging.getLogger(__name__)

async def test_workflow(summarization_type="executive"):
    """Test the workflow with a sample document"""
    try:
        logger.info("="*80)
        logger.info(f"Starting workflow debug test - {summarization_type.upper()} summarization")
        logger.info("="*80)
        
        # Import workflow
        logger.info("Importing workflow...")
        from app.workflows.hierarchical_summarization import summarization_workflow
        logger.info("Workflow imported successfully")
        
        # Test state with summarization type
        test_state = {
            "project_id": "proj_4ac29911_c141_41d7_98d2_68d01470a877",
            "document_id": "bases_de_licitacion_siop-e-redjal-ob-lp-1250-2023",
            "summarization_type": summarization_type,
            "chunks": [],
            "markdown_content": None,
            "final_summary": None,
            "error": None,
            "collapse_level": "none"
        }
        
        logger.info(f"Test state: {test_state}")
        logger.info("Starting workflow execution...")
        
        # Run workflow and accumulate state
        event_count = 0
        accumulated_state = {**test_state}
        
        async for event in summarization_workflow.astream(test_state):
            event_count += 1
            logger.info(f"\n{'='*60}")
            logger.info(f"Event #{event_count}")
            logger.info(f"Event keys: {list(event.keys())}")
            
            for node_name, node_state in event.items():
                logger.info(f"Node: {node_name}")
                if isinstance(node_state, dict):
                    # Accumulate state updates
                    accumulated_state.update(node_state)
                    
                    logger.info(f"State keys: {list(node_state.keys())}")
                    if 'chunks' in node_state:
                        logger.info(f"Number of chunks: {len(node_state['chunks'])}")
                    if 'markdown_content' in node_state and node_state.get('markdown_content'):
                        logger.info(f"Markdown content length: {len(node_state['markdown_content'])} chars")
                    if 'error' in node_state and node_state['error']:
                        logger.error(f"Error in state: {node_state['error']}")
                    if 'final_summary' in node_state:
                        logger.info(f"Final summary present: {bool(node_state['final_summary'])}")
                        if node_state['final_summary']:
                            logger.info(f"Summary length: {len(node_state['final_summary'])} chars")
                else:
                    logger.info(f"State type: {type(node_state)}")
            logger.info(f"{'='*60}\n")
        
        logger.info(f"\nWorkflow completed. Total events: {event_count}")
        logger.info(f"Final accumulated state keys: {list(accumulated_state.keys())}")
        
        # Print final summary
        if accumulated_state.get('final_summary'):
            logger.info("\n" + "="*80)
            logger.info(f"FINAL SUMMARY ({summarization_type.upper()}):")
            logger.info("="*80)
            logger.info(accumulated_state['final_summary'])
            logger.info("="*80)
            return True
        else:
            logger.warning("No final summary generated!")
            if accumulated_state.get('error'):
                logger.error(f"Error: {accumulated_state['error']}")
            return False
        
    except Exception as e:
        logger.error(f"Error in test: {str(e)}", exc_info=True)
        return False

async def run_tests():
    """Run tests for both summarization types"""
    logger.info("Starting debug script...")
    
    # Test Executive summarization
    logger.info("\n" + "="*80)
    logger.info("TEST 1: Executive Summarization")
    logger.info("="*80)
    exec_success = await test_workflow("executive")
    
    # Test Detailed summarization
    logger.info("\n" + "="*80)
    logger.info("TEST 2: Detailed Summarization")
    logger.info("="*80)
    detailed_success = await test_workflow("detailed")
    
    # Summary
    logger.info("\n" + "="*80)
    logger.info("TEST SUMMARY")
    logger.info("="*80)
    logger.info(f"Executive Summarization: {'✅ PASSED' if exec_success else '❌ FAILED'}")
    logger.info(f"Detailed Summarization: {'✅ PASSED' if detailed_success else '❌ FAILED'}")
    logger.info("="*80)
    
    return exec_success and detailed_success

if __name__ == "__main__":
    success = asyncio.run(run_tests())
    logger.info("Debug script completed")
    sys.exit(0 if success else 1)

# Made with Bob
