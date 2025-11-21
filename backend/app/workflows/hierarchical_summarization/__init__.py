"""
Hierarchical summarization workflow - exports the main workflow graph and entry point.

This module provides a LangGraph-based workflow for summarizing large documents
that exceed LLM context windows using hierarchical map-reduce with adaptive collapsing.
"""

from .graph import summarization_workflow, create_summarization_workflow
from .state import OverallState, Chunk, SubChunk

__all__ = [
    "summarization_workflow",
    "create_summarization_workflow",
    "OverallState",
    "Chunk",
    "SubChunk",
]

# Made with Bob
