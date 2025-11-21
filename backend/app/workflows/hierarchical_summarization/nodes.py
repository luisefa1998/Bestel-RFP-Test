import asyncio
import tiktoken
import logging
from typing import List, Optional
from langchain_text_splitters import CharacterTextSplitter
from app.services.vector_store_service import VectorStoreService
from app.services.document_service import DocumentService
from .state import OverallState, Chunk, SubChunk
from .config import (
    SUMMARIZER_MAX_CONTEXT_LENGTH,
    FINAL_SUMMARIZER_MAX_CONTEXT_LENGTH,
    llm_id
)
from .chains import (
    get_map_chain,
    get_reduce_chain,
    get_final_chain,
    get_executive_chain
)

# Use the workflow logger that's configured in logging_config.py
logger = logging.getLogger('app.workflows.hierarchical_summarization')
ENC = tiktoken.encoding_for_model(llm_id.split('/')[-1])

# Log that this module is being loaded
logger.info("=" * 80)
logger.info("Hierarchical summarization nodes module loaded")
logger.info("=" * 80)


def route_summarization_type(state: OverallState) -> str:
    """
    Router node that determines which summarization path to take.
    
    Returns:
        "detailed" for hierarchical map-reduce summarization
        "executive" for single-pass executive summarization
    """
    summarization_type = state.get("summarization_type", "executive")
    logger.info(f"[route_summarization_type] Routing to '{summarization_type}' summarization path")
    return summarization_type


async def load_markdown_document(state: OverallState):
    """
    Load the full markdown document from the file system for executive summarization.
    This bypasses the vector DB and loads the complete document directly.
    """
    logger.info(f"[load_markdown_document] Loading markdown for project={state['project_id']}, document={state['document_id']}")
    
    try:
        doc_service = DocumentService()
        markdown_content = await doc_service.get_markdown_content(state["project_id"], state["document_id"])
        
        logger.info(f"[load_markdown_document] Loaded markdown content, length: {len(markdown_content)} chars")
        
        return {"markdown_content": markdown_content}
    except Exception as e:
        logger.error(f"[load_markdown_document] Error: {str(e)}", exc_info=True)
        return {"error": f"Failed to load markdown document: {str(e)}"}


async def generate_executive_summary(state: OverallState):
    """
    Generate an executive summary in a single pass using the full markdown document.
    Rate limiting is handled automatically by ChatWatsonx via the global rate limiter.
    """
    logger.info(f"[generate_executive_summary] Starting executive summarization")
    
    try:
        markdown_content = state.get("markdown_content")
        if not markdown_content:
            raise ValueError("No markdown content available for executive summarization")
        
        # Count tokens
        token_count = len(ENC.encode(markdown_content))
        logger.info(f"[generate_executive_summary] Document token count: {token_count}")
        
        # Generate executive summary
        logger.info(f"[generate_executive_summary] Invoking executive summarization chain")
        chain = get_executive_chain()
        response = await chain.ainvoke({"input_text": markdown_content})
        
        logger.info(f"[generate_executive_summary] Executive summary generated, length: {len(response)} chars")
        
        return {"final_summary": response}
    except Exception as e:
        logger.error(f"[generate_executive_summary] Error: {str(e)}", exc_info=True)
        return {"error": f"Failed to generate executive summary: {str(e)}"}


def get_document_chunks(state: OverallState):
    """Get's all document's chunks from vector DB"""
    logger.info(f"[get_document_chunks] Starting for project={state['project_id']}, document={state['document_id']}")
    try:
        vec_service = VectorStoreService(state["project_id"])
        chunks = []
        raw_chunks = vec_service.get_all_chunks(state["document_id"])
        logger.info(f"[get_document_chunks] Retrieved {len(raw_chunks)} chunks from vector DB")
        
        for i, chunk in enumerate(raw_chunks):
            chunks.append(
                {
                    'text': chunk,
                    'sub_chunks': [],
                    'summary': None
                }
            )
            if i < 3:  # Log first 3 chunks
                logger.debug(f"[get_document_chunks] Chunk {i} length: {len(chunk)} chars")
        
        logger.info(f"[get_document_chunks] Completed successfully with {len(chunks)} chunks")
        return {'chunks': chunks, 'collapse_level': 'none'}
    except Exception as e:
        logger.error(f"[get_document_chunks] Error: {str(e)}", exc_info=True)
        raise

def split_document_chunks(state: OverallState):
    """Split document's chunks within current limits"""
    logger.info(f"[split_document_chunks] Starting with {len(state['chunks'])} chunks")
    
    try:
        text_splitter = CharacterTextSplitter.from_tiktoken_encoder(
            chunk_size=SUMMARIZER_MAX_CONTEXT_LENGTH, chunk_overlap=0
        )
        chunks = state["chunks"]
        total_sub_chunks = 0
        
        for chunk in chunks:
            for sub_chunk in text_splitter.split_text(chunk["text"]):
                chunk["sub_chunks"].append(
                    {
                        "text": sub_chunk,
                        "summary": None
                    }
                )
                total_sub_chunks += 1
        
        logger.info(f"[split_document_chunks] Completed successfully. Total sub-chunks: {total_sub_chunks}")
        return {'chunks': chunks}
    except Exception as e:
        logger.error(f"[split_document_chunks] Error: {str(e)}", exc_info=True)
        raise

async def generate_summary(sub_chunk: SubChunk, user_query: Optional[str] = None):
    """Function that generates a summary for a single sub-chunk of text"""
    text = sub_chunk["text"]
    token_count = len(ENC.encode(text))
    logger.debug(f"[generate_summary] Processing sub-chunk with {token_count} tokens")
    
    if token_count < 128:
        logger.debug(f"[generate_summary] Text too short ({token_count} tokens), returning as-is")
        return {"summary": text}
    
    try:
        logger.debug(f"[generate_summary] Invoking LLM for summarization")
        chain = get_map_chain(user_query)
        
        if user_query:
            response = await chain.ainvoke({"input_text": text, "user_query": user_query})
        else:
            response = await chain.ainvoke({"input_text": text})
        
        logger.debug(f"[generate_summary] LLM response received, length: {len(response)}")
        return {"summary": response}
    except Exception as e:
        logger.error(f"[generate_summary] Error: {str(e)}", exc_info=True)
        raise

async def generate_summaries(state: OverallState):
    """
    Node that generates summaries for all sub-chunks concurrently.
    Rate limiting is handled automatically by ChatWatsonx via the global rate limiter.
    """
    chunks = state["chunks"]
    user_query = state.get("user_query")
    logger.info(f"[generate_summaries] Starting with {len(chunks)} chunks")
    
    if user_query:
        logger.info(f"[generate_summaries] Using user query: {user_query[:100]}...")
    
    try:
        total_sub_chunks = sum(len(chunk["sub_chunks"]) for chunk in chunks)
        logger.info(f"[generate_summaries] Total sub-chunks to summarize: {total_sub_chunks}")
        logger.info(f"[generate_summaries] Using centralized rate limiter (8 requests/second)")
        
        # Create tasks for ALL sub-chunks at once
        all_tasks = []
        chunk_indices = []
        subchunk_indices = []
        
        for i, chunk in enumerate(chunks):
            for j, sub_chunk in enumerate(chunk["sub_chunks"]):
                all_tasks.append(generate_summary(sub_chunk, user_query))
                chunk_indices.append(i)
                subchunk_indices.append(j)
        
        logger.info(f"[generate_summaries] Running {len(all_tasks)} summarization tasks (rate-limited)")
        
        # Run ALL summaries concurrently - rate limiter will control the flow
        results = await asyncio.gather(*all_tasks)
        
        logger.info(f"[generate_summaries] Completed all {len(results)} summaries")
        
        # Update sub-chunks with their summaries
        for task_idx, result in enumerate(results):
            chunk_idx = chunk_indices[task_idx]
            subchunk_idx = subchunk_indices[task_idx]
            chunks[chunk_idx]["sub_chunks"][subchunk_idx]["summary"] = result["summary"]
        
        logger.info(f"[generate_summaries] Completed successfully")
        return {"chunks": chunks}
    except Exception as e:
        logger.error(f"[generate_summaries] Error: {str(e)}", exc_info=True)
        raise

async def reduce_summaries(chunk: Chunk, user_query: Optional[str] = None):
    """
    Function that reduces a list of summaries for a single chunk.
    Rate limiting is handled automatically by ChatWatsonx via the global rate limiter.
    """
    sub_chunks = chunk["sub_chunks"]
    if len(sub_chunks) == 1:
        return {"summary": sub_chunks[0]["summary"]}
    summaries = ""
    for i, sub_chunk in enumerate(sub_chunks):
        summaries += f"Summary {i}:\n{sub_chunk['summary']}\n\n"
    summaries = summaries.strip()
    
    chain = get_reduce_chain(user_query)
    
    if user_query:
        response = await chain.ainvoke({"input_summaries": summaries, "user_query": user_query})
    else:
        response = await chain.ainvoke({"input_summaries": summaries})
    
    return {"summary": response}

async def merge_summaries(state: OverallState):
    """Node that merge summaries from all chunks concurrently using asyncio.gather"""
    chunks = state["chunks"]
    user_query = state.get("user_query")

    tasks = [
        reduce_summaries(chunk, user_query)
        for chunk in chunks
    ]

    # Run all summaries concurrently
    results = await asyncio.gather(*tasks)
        
    # Update chunks with their summaries
    for i, result in enumerate(results):
        chunks[i]["summary"] = result["summary"]
    
    return {"chunks": chunks}


def validate_summaries_length(state: OverallState) -> str:
    """
    Node that validates that the sum of tokens for all chunk-summaries is less than FINAL_SUMMARIZER_MAX_CONTEXT_LENGTH.
    Returns routing decision: 'collapse' or 'finalize'
    
    If already at 'section' level or 'ignore', proceed to finalize regardless of length.
    """
    collapse_level = state.get("collapse_level", "none")
    
    summaries_length = sum(
        [
            len(ENC.encode(chunk["summary"] or ""))
            for chunk in state["chunks"]
            if chunk["summary"]
        ]
    )
    
    logger.info(f"Total summaries length: {summaries_length} tokens (limit: {FINAL_SUMMARIZER_MAX_CONTEXT_LENGTH}), collapse_level: {collapse_level}")
    
    # If we've already collapsed at section level or decided to ignore, proceed
    if collapse_level in ["section", "ignore"]:
        logger.info(f"At collapse level '{collapse_level}', proceeding to finalize regardless of length")
        return "finalize"
    
    # Check if summaries fit
    if summaries_length <= FINAL_SUMMARIZER_MAX_CONTEXT_LENGTH:
        return "finalize"
    
    return "collapse"


def _get_subsection_key(chunk: Chunk) -> str:
    """Extract exact section from first line (e.g., '1.1 DEFINICIONES')"""
    return chunk["text"].split('\n')[0].strip()


def _get_section_key(chunk: Chunk) -> str:
    """Extract main section number from first line (e.g., '1.1' -> '1')"""
    import re
    first_line = chunk["text"].split('\n')[0].strip()
    # Extract section number (handles formats like "1.1 TITLE" or "## 1.1 TITLE")
    match = re.search(r'(\d+)(?:\.\d+)*', first_line)
    if match:
        return match.group(1)  # Return just the main section number
    return first_line  # Fallback to full line if no number found


async def collapse_chunks(state: OverallState):
    """
    Node that collapses chunks hierarchically when summaries exceed context limit.
    
    Collapse levels:
    - none -> subsection: Group by exact section (e.g., "1.1 DEFINICIONES")
    - subsection -> section: Group by main section number (e.g., "1")
    - section -> ignore: Accept any length and proceed
    
    The chunk.summary already represents all sub_chunks, so we convert each chunk
    into a sub-chunk for the merged chunk, then regenerate the summary.
    """
    chunks = state["chunks"]
    current_level = state.get("collapse_level", "none")
    
    logger.info(f"Collapsing {len(chunks)} chunks at level '{current_level}'")
    
    # Determine next collapse level and grouping strategy
    if current_level == "none":
        next_level = "subsection"
        get_key = _get_subsection_key
    elif current_level == "subsection":
        next_level = "section"
        get_key = _get_section_key
    else:
        # Already at section level, set to ignore and don't collapse further
        logger.info(f"Already at section level, setting to 'ignore' and proceeding")
        return {"collapse_level": "ignore"}
    
    # Group chunks by the determined key
    sections = {}
    for chunk in chunks:
        group_key = get_key(chunk)
        if group_key not in sections:
            sections[group_key] = []
        sections[group_key].append(chunk)
    
    logger.info(f"Found {len(sections)} unique groups at level '{next_level}'")
    
    # Merge chunks within each group
    collapsed_chunks: List[Chunk] = []
    for section_name, section_chunks in sections.items():
        if len(section_chunks) == 1:
            # No need to merge single chunk
            collapsed_chunks.append(section_chunks[0])
        else:
            # Merge multiple chunks in this section
            merged_text = "\n\n".join([c["text"] for c in section_chunks])
            merged_sub_chunks: List[SubChunk] = []
            
            # Convert each chunk into a sub-chunk using its text and summary
            # The chunk.summary already represents all its sub_chunks
            for chunk in section_chunks:
                if chunk["summary"]:
                    merged_sub_chunks.append({
                        "text": chunk["text"],
                        "summary": chunk["summary"]
                    })
            
            # Create merged chunk with summary set to None
            # The graph will route back to merge_summaries node to regenerate
            merged_chunk: Chunk = {
                "text": merged_text,
                "sub_chunks": merged_sub_chunks,
                "summary": None
            }
            
            collapsed_chunks.append(merged_chunk)
    
    logger.info(f"Collapsed to {len(collapsed_chunks)} chunks at level '{next_level}'")
    
    # Return state with collapsed chunks and updated level
    # The graph will route back to merge_summaries to regenerate chunk summaries
    return {"chunks": collapsed_chunks, "collapse_level": next_level}

async def generate_final_summary(state: OverallState):
    """Node that generates the final summary of the document"""
    user_query = state.get("user_query")
    
    summaries = ""
    for i, chunk in enumerate(state["chunks"]):
        summaries += f"Summary {i}:\n{chunk['summary']}\n\n"
    summaries = summaries.strip()
    logger.debug(f"Final summarization context length: {len(ENC.encode(summaries))}")
    
    chain = get_final_chain(user_query)
    
    if user_query:
        response = await chain.ainvoke({"input_summaries": summaries, "user_query": user_query})
    else:
        response = await chain.ainvoke({"input_summaries": summaries})
    
    return {"final_summary": response}


if __name__ == "__main__":
    state = {
        "project_id": "proj_788b65e0_3249_46e4_a0bf_bc64de94a5eb",
        "document_id": "bases_de_licitacion_siop-e-redjal-ob-lp-1250-2023"
    }
    state = state | get_document_chunks(state)
    state = state | split_document_chunks(state)