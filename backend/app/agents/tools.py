from app.services.embedding_service import EmbeddingService
from app.services.vector_store_service import VectorStoreService
import logging
import contextlib
import warnings
warnings.filterwarnings("ignore")

# Set up logging
logger = logging.getLogger(__name__)

class RFPSearchTool:
    """
    Specialized search tool for RFP (Request for Proposal) documents.
    
    This tool searches for relevant information in RFP documents based on the query.
    It uses vector embeddings to find the most relevant passages and returns them as context.
    """
    def __init__(self):
        self._current_project_id = None
        self._embedding_service = EmbeddingService()
    
    @contextlib.contextmanager
    def use_project(self, project_id: str):
        """
        Context manager to set project context for the duration of a request.
        
        Args:
            project_id: The project ID to use for retrieval
        """
        prev_project_id = self._current_project_id
        self._current_project_id = project_id
        logger.info(f"Set RFP project context: {project_id}")
        try:
            yield
        finally:
            logger.info(f"Restored RFP project context")
            self._current_project_id = prev_project_id
    
    def search_rfp(self, query: str) -> str:
        """
        Search RFP documents for relevant information.
        
        Args:
            query: The question or query about RFP documents
            
        Returns:
            str: Relevant context from the RFP documents
        """
        try:
            logger.info(f"RFP search query: {query}")
            
            if not self._current_project_id:
                raise RuntimeError("RFP project context not set. Use the 'use_project' context manager.")
            
            # Initialize vector store with current project
            vector_store = VectorStoreService(project_id=self._current_project_id)
            
            # Create embedding for the query
            query_embedding = self._embedding_service.embed_query(query)
            
            # Search for relevant documents
            results = vector_store.search(query_vector=query_embedding, top_k=5)
            
            if not results:
                return "No relevant information found in the RFP documents."
            
            # Format the results
            context = ""
            for _, result in enumerate(results):
                context += f"Document: {result['document_id']}\n"
                context += f"Page(s): {', '.join(map(str, result['page_numbers']))}\n\n"
                context += f"Chunk Text:\n{result['text']}\n\n"
            
            return context
        
        except Exception as e:
            logger.error(f"Error in RFP search tool: {str(e)}")
            return f"Error retrieving information: {str(e)}"

