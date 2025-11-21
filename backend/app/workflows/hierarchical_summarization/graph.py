"""
LangGraph workflow definition for hierarchical document summarization.

This workflow supports two summarization types:

1. DETAILED (hierarchical map-reduce with adaptive collapsing):
   - Get document chunks from vector DB
   - Split chunks into sub-chunks if needed
   - Parallel summarize all sub-chunks (map phase)
   - Merge sub-chunk summaries into chunk summaries (reduce phase)
   - Validate if summaries fit in final context window
   - If not, collapse chunks by section and repeat merge
   - Generate final summary from all chunk summaries

2. EXECUTIVE (single-pass fast summarization):
   - Load full markdown document from file system
   - Generate executive summary in one pass using GPT-OSS-120b
   - Optimized for speed and high-level overview
"""

from langgraph.graph import StateGraph, END
from .state import OverallState
from .nodes import (
    route_summarization_type,
    load_markdown_document,
    generate_executive_summary,
    get_document_chunks,
    split_document_chunks,
    generate_summaries,
    merge_summaries,
    validate_summaries_length,
    collapse_chunks,
    generate_final_summary
)


def create_summarization_workflow():
    """
    Create and compile the hierarchical summarization workflow with routing.
    
    Returns:
        Compiled StateGraph ready for execution
    """
    # Initialize the graph with our state schema
    workflow = StateGraph(OverallState)
    
    # Add all nodes
    # Executive path nodes
    workflow.add_node("load_markdown", load_markdown_document)
    workflow.add_node("generate_executive", generate_executive_summary)
    
    # Detailed path nodes
    workflow.add_node("get_chunks", get_document_chunks)
    workflow.add_node("split_chunks", split_document_chunks)
    workflow.add_node("generate_summaries", generate_summaries)
    workflow.add_node("merge_summaries", merge_summaries)
    workflow.add_node("collapse_chunks", collapse_chunks)
    workflow.add_node("generate_final", generate_final_summary)
    
    # Set entry point with conditional routing based on summarization_type
    workflow.set_conditional_entry_point(
        route_summarization_type,
        {
            "executive": "load_markdown",
            "detailed": "get_chunks"
        }
    )
    
    # Executive path: load_markdown -> generate_executive -> END
    workflow.add_edge("load_markdown", "generate_executive")
    workflow.add_edge("generate_executive", END)
    
    # Detailed path: existing hierarchical flow
    workflow.add_edge("get_chunks", "split_chunks")
    workflow.add_edge("split_chunks", "generate_summaries")
    workflow.add_edge("generate_summaries", "merge_summaries")
    
    # Conditional routing after merge_summaries
    # If summaries are too long, collapse and re-merge
    # Otherwise, proceed to final summary
    workflow.add_conditional_edges(
        "merge_summaries",
        validate_summaries_length,
        {
            "collapse": "collapse_chunks",
            "finalize": "generate_final"
        }
    )
    
    # After collapsing, go back to merge_summaries to regenerate chunk summaries
    workflow.add_edge("collapse_chunks", "merge_summaries")
    
    # Final summary is the end
    workflow.add_edge("generate_final", END)
    
    # Compile the graph
    return workflow.compile()


# Create the compiled workflow instance
summarization_workflow = create_summarization_workflow()

# Made with Bob
