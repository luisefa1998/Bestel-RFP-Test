"""
Celery tasks for document processing and summarization.
"""
import os
import json
import logging
import datetime
import asyncio
from typing import Optional
from app.core.celery_app import celery_app
from app.utils.doc_processor import DocumentProcessor
from app.services.document_service import DocumentService
from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService

# Set up logging
logger = logging.getLogger(__name__)
document_service = DocumentService()

@celery_app.task(name="process_document")
def process_document(project_id: str, document_id: str, file_path: str):
    """
    Process a document: converts PDF into a vectorized collection.
    
    This task runs in a separate worker process, so it won't block the web server.
    It updates the processing status in the status file.
    
    Args:
        project_id: ID of the project
        document_id: ID of the document
        file_path: Path to the PDF file
    """
    logger.info(f"Starting document processing task for project {project_id}, document {document_id}")
    
    try:
        # Update status to processing
        update_status(project_id, document_id, status="converting document", progress=20)
        
        # Verify file exists
        if not os.path.exists(file_path):
            logger.error(f"PDF file not found: {file_path}")
            update_status(project_id, document_id, status="failed", progress=0, error=f"PDF file not found: {file_path}")
            return {"status": "error", "project_id": project_id, "document_id": document_id, "error": f"PDF file not found: {file_path}"}
        
        # Convert PDF to Docling's Document
        logger.info(f"Converting PDF: {file_path}")
        doc_processor = DocumentProcessor(file_path)
        
        # Create markdown directory and save markdown to file
        markdown_dir = document_service.get_markdown_dir(project_id)
        markdown_path = markdown_dir / f"{document_id}.md"
        logger.info(f"Saving markdown to: {markdown_path}")
        doc_processor.export_doc_to_markdown(str(markdown_path))
        update_status(project_id, document_id, status="chunking document", progress=50)

        # Chunk document
        chunks = doc_processor.chunk_doc()
        logger.info(f"Generated {len(chunks)} chunks from document")
        
        if not chunks:
            error_msg = "No chunks generated from document"
            logger.error(error_msg)
            update_status(project_id, document_id, status="failed", progress=0, error=error_msg)
            return {"status": "error", "project_id": project_id, "document_id": document_id, "error": error_msg}
        
        update_status(project_id, document_id, status="vectorizing chunks", progress=60)

        # Vectorize chunks
        logger.info(f"Starting to vectorize {len(chunks)} chunks")
        emb_service = EmbeddingService()
        texts = [chunk["text"] for chunk in chunks]
        
        # Log some info about the texts
        logger.info(f"Extracted {len(texts)} texts from chunks")
        if texts:
            logger.info(f"First text length: {len(texts[0])} chars")
            logger.info(f"Last text length: {len(texts[-1])} chars")
        
        embeddings = emb_service.embed_documents(texts)
        logger.info(f"Received {len(embeddings)} embeddings")
        
        # Validate counts match
        if len(embeddings) != len(chunks):
            error_msg = f"Embedding count mismatch: {len(chunks)} chunks but {len(embeddings)} embeddings"
            logger.error(error_msg)
            update_status(project_id, document_id, status="failed", progress=0, error=error_msg)
            return {"status": "error", "project_id": project_id, "document_id": document_id, "error": error_msg}
        
        # Assign embeddings back to chunks
        for i, chunk in enumerate(chunks):
            chunk["embedding"] = embeddings[i]
        
        logger.info(f"Successfully assigned embeddings to all {len(chunks)} chunks")
        update_status(project_id, document_id, status="storing vectors", progress=80)

        # Store Vectors - use project-specific collection
        vec_service = VectorStoreService(project_id)
        vec_service.insert_chunks(document_id, chunks)
        update_status(project_id, document_id, status="completed", progress=100)
        
    except Exception as e:
        logger.error(f"Error processing document {document_id}: {str(e)}")
        update_status(project_id, document_id, status="failed", progress=0, error=str(e))
        return {"status": "error", "project_id": project_id, "document_id": document_id, "error": str(e)}


def update_status(project_id: str, document_id: str, **fields):
    """Generic status updater. Merges arbitrary key/value fields into a document's status file."""
    path = document_service.get_status_dir(project_id) / f"{document_id}.json"

    # Load current data (safe fallback)
    try:
        data = json.load(open(path)) if path.exists() else {}
    except Exception as e:
        logger.warning(f"Failed to read existing status file {path}: {e}")
        data = {}

    # Merge
    data.update({
        "project_id": project_id,
        "document_id": document_id,
        "timestamp": datetime.datetime.now().isoformat(),
    })
    data.update(fields)

    # Persist
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

    logger.info(f"Updated status for project={project_id}, document={document_id} with {list(fields.keys())}")


@celery_app.task(name="summarize_document")
def summarize_document(project_id: str, document_id: str, summarization_type: str = "executive", user_query: Optional[str] = None):
    """
    Summarize a document using hierarchical summarization workflow.
    
    This task runs the LangGraph workflow asynchronously and saves the result.
    It updates the summarization status using separate fields (summary_status, summary_progress, summary_error)
    to avoid overwriting document processing status.
    
    Args:
        project_id: ID of the project
        document_id: ID of the document to summarize
        summarization_type: Type of summarization ('detailed' or 'executive', default: 'executive')
        user_query: Optional user instructions for detailed summarization (only applies to 'detailed' type)
    """
    logger.info(f"Starting {summarization_type} summarization task for project {project_id}, document {document_id}")
    if user_query:
        logger.info(f"User query provided: {user_query[:100]}...")
    
    try:
        # Import here to avoid circular dependencies
        from app.workflows.hierarchical_summarization import summarization_workflow
        
        # Clear any previous summary error and set initial status
        update_status(project_id, document_id, summary_status="initializing", summary_progress=10, summary_error="")
        
        # Prepare initial state
        initial_state = {
            "project_id": project_id,
            "document_id": document_id,
            "summarization_type": summarization_type,
            "user_query": user_query,
            "chunks": [],
            "markdown_content": None,
            "final_summary": None,
            "error": None,
            "collapse_level": "none"
        }
        
        # Run the workflow
        logger.info(f"Invoking summarization workflow for document {document_id}")
        update_status(project_id, document_id, summary_status="processing", summary_progress=20)
        
        # Get or create event loop for async operations
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Execute workflow using the same event loop
        final_state = loop.run_until_complete(_run_workflow(summarization_workflow, initial_state, project_id, document_id))
        
        # Check for errors
        if final_state.get("error"):
            logger.error(f"Workflow error for document {document_id}: {final_state['error']}")
            update_status(project_id, document_id, summary_status="failed", summary_progress=0,
                         summary_error=final_state["error"])
            return {"status": "error", "project_id": project_id, "document_id": document_id,
                   "error": final_state["error"]}
        
        # Extract final summary
        final_summary = final_state.get("final_summary")
        if not final_summary:
            error_msg = "Workflow completed but no summary was generated"
            logger.error(f"{error_msg} for document {document_id}: {final_state}")
            update_status(project_id, document_id, summary_status="failed", summary_progress=0,
                         summary_error=error_msg)
            return {"status": "error", "project_id": project_id, "document_id": document_id,
                   "error": error_msg}
        
        # Save summary to file (save_summary handles multiple types in one file)
        logger.info(f"Saving {summarization_type} summary for document {document_id}")
        update_status(project_id, document_id, summary_status="saving", summary_progress=90)
        
        summary_data = {
            "document_id": document_id,
            "project_id": project_id,
            "summarization_type": summarization_type,
            "user_query": user_query,
            "summary": final_summary,
            "collapse_level": final_state.get("collapse_level", "none"),
            "num_chunks": len(final_state.get("chunks", [])),
            "timestamp": str(datetime.datetime.now())
        }
        
        # Get or create event loop for async operations
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
        
        # Run the async save operation (save_summary will handle merging with existing summaries)
        loop.run_until_complete(document_service.save_summary(project_id, document_id, summary_data))
        
        # Update status to completed
        update_status(project_id, document_id, summary_status="completed", summary_progress=100)
        logger.info(f"Document summarization completed for {document_id}")
        
        return {
            "status": "success",
            "project_id": project_id,
            "document_id": document_id,
            "summary": final_summary
        }
        
    except Exception as e:
        logger.error(f"Error summarizing document {document_id}: {str(e)}", exc_info=True)
        update_status(project_id, document_id,
                     summary_status="failed", summary_progress=0,
                     summary_error=str(e))
        return {"status": "error", "project_id": project_id, "document_id": document_id, "error": str(e)}


async def _run_workflow(workflow, initial_state, project_id, document_id):
    """
    Helper function to run the workflow and update progress.
    
    Args:
        workflow: The compiled LangGraph workflow
        initial_state: Initial state dictionary
        project_id: Project ID for status updates
        document_id: Document ID for status updates
    
    Returns:
        Final state from workflow execution
    """
    try:
        logger.info(f"[_run_workflow] Starting workflow execution for document {document_id}")
        logger.info(f"[_run_workflow] Initial state keys: {list(initial_state.keys())}")
        
        # Stream workflow execution to track progress
        # Map node completion to next step status message and progress
        progress_map = {
            "get_chunks": (30, "split_chunks"),
            "split_chunks": (40, "generate_summaries"),
            "generate_summaries": (60, "merge_summaries"),
            "merge_summaries": (70, "validate_summaries"),
            "collapse_chunks": (75, "merge_summaries"),
            "validate_summaries": (80, "generate_final"),
            "generate_final": (90, "finalizing")
        }
        
        # Accumulate state updates - start with initial state
        accumulated_state = {**initial_state}
        event_count = 0
        
        logger.info("[_run_workflow] Starting to stream workflow events...")
        async for event in workflow.astream(initial_state):
            event_count += 1
            logger.info(f"[_run_workflow] Received event #{event_count}: {list(event.keys())}")
            
            # event is a dict with node names as keys
            for node_name, node_state in event.items():
                logger.info(f"[_run_workflow] Node '{node_name}' completed")
                logger.debug(f"[_run_workflow] Node state keys: {list(node_state.keys()) if isinstance(node_state, dict) else 'not a dict'}")
                
                # Accumulate state updates (merge with existing state)
                if isinstance(node_state, dict):
                    accumulated_state.update(node_state)
                    logger.debug(f"[_run_workflow] Accumulated state keys: {list(accumulated_state.keys())}")
                
                # Get progress and next step message
                progress_info = progress_map.get(node_name, (50, "processing"))
                progress = progress_info[0]
                next_step = progress_info[1]
                
                # Use summary-specific fields
                update_status(project_id, document_id,
                            summary_status=f"processing: {next_step}",
                            summary_progress=progress)
        
        logger.info(f"[_run_workflow] Workflow completed. Total events: {event_count}")
        logger.info(f"[_run_workflow] Final accumulated state keys: {list(accumulated_state.keys())}")
        
        return accumulated_state
        
    except Exception as e:
        logger.error(f"[_run_workflow] Error in workflow execution: {str(e)}", exc_info=True)
        return {"error": str(e), **initial_state}
