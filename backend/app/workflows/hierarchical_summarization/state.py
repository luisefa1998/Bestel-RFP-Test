from typing import TypedDict, List, Optional, Literal


class SubChunk(TypedDict):
    """Represents a sub-chunk of text with its summary"""
    text: str
    summary: Optional[str]


class Chunk(TypedDict):
    """Represents a document chunk with sub-chunks and aggregated summary"""
    text: str
    summary: Optional[str]
    sub_chunks: List[SubChunk]


CollapseLevel = Literal["none", "subsection", "section", "ignore"]
SummarizationType = Literal["detailed", "executive"]


class OverallState(TypedDict):
    """Main workflow state for hierarchical summarization"""
    project_id: str
    document_id: str
    summarization_type: SummarizationType  # Type of summarization to perform
    user_query: Optional[str]  # Optional user instructions for detailed summarization
    chunks: List[Chunk]
    markdown_content: Optional[str]  # Full markdown content for executive summarization
    final_summary: Optional[str]
    error: Optional[str]
    collapse_level: CollapseLevel  # Track how much we've collapsed

# Made with Bob
