import warnings
warnings.filterwarnings("ignore")

from typing import List, Dict, Any
from pymilvus import MilvusClient, connections
from app.core.settings import settings
import logging

logger = logging.getLogger(__name__)


class VectorStoreService:
    """
    Handles all vector database operations:
    - Collection creation and management
    - Insertion of document embeddings
    - Similarity search for retrieval or chat context
    """

    def __init__(self, project_id: str):
        """
        Initialize the vector store service for a specific project
        
        Args:
            project_id: The ID of the project
        """
        self.project_id = project_id
        self.collection_name = project_id  # Use project_id directly as collection name
        self.dim = settings.EMBEDDING_DIMENSION
        
        # Connect to cloud Milvus instance using URI and token format
        uri = f"https://{settings.MILVUS_HOST}:{settings.MILVUS_PORT}"
        token = f"{settings.MILVUS_USER}:{settings.MILVUS_KEY}"
        
        self.client = MilvusClient(uri=uri, token=token)
        logger.info(f"Connected to cloud Milvus at {settings.MILVUS_HOST}:{settings.MILVUS_PORT}")
        self._ensure_collection()

    def _ensure_collection(self):
        """Create collection schema"""
        if self.client.has_collection(self.collection_name):
            logger.info(f"Using existing collection: {self.collection_name}")
            return
        logger.info(f"Creating new collection: {self.collection_name}")
        
        # Create collection using MilvusClient API
        self.client.create_collection(
            collection_name=self.collection_name,
            dimension=self.dim,
            primary_field_name="id",
            auto_id=True,
            metric_type="IP"
        )

    def insert_chunks(self, document_id: str, chunks: List[Dict[str, Any]]):
        """
        Insert pre-vectorized document chunks into Milvus.
        Each chunk must have 'text', 'embedding', and 'page_numbers' fields.
        """
        data = []
        
        for chunk in chunks:
            data.append({
                "document_id": document_id,
                "page_numbers": chunk.get("page_numbers", []),
                "text": chunk["text"],
                "vector": chunk["embedding"]
            })
        
        logger.info(f"Inserting {len(chunks)} chunks for project {self.project_id} (collection: {self.collection_name})")
        self.client.insert(
            collection_name=self.collection_name,
            data=data
        )

    def search(self, query_vector: List[float], top_k: int = 5) -> List[Dict[str, Any]]:
        """
        Perform similarity search given an embedding vector.
        Returns the most relevant chunks.
        """
        results = self.client.search(
            collection_name=self.collection_name,
            data=[query_vector],
            limit=top_k,
            output_fields=["document_id", "page_numbers", "text"]
        )

        hits = []
        # MilvusClient.search returns a list of results for each query vector
        for result in results:
            for hit in result:
                hits.append(
                    {
                        "document_id": hit["entity"].get("document_id", ""),
                        "page_numbers": hit["entity"].get("page_numbers", []),
                        "text": hit["entity"].get("text", ""),
                        "score": hit.get("distance", 0.0),
                    }
                )

        return hits

    def clear_document(self, document_id: str):
        """Delete all vectors related to a document."""
        expr = f'document_id == "{document_id}"'
        deleted_count = self.client.delete(
            collection_name=self.collection_name,
            filter=expr
        )
        logger.info(f"Deleted vectors for document {document_id} in project {self.project_id}: {deleted_count}")

    def drop_collection(self):
        """Remove entire collection by dropping it"""
        if self.client.has_collection(self.collection_name):
            logger.info(f"Dropping collection for project {self.project_id}: {self.collection_name}")
            self.client.drop_collection(self.collection_name)

    def get_all_chunks(self, document_id: str) -> list:
        """Retrieve all stored chunks for a specific document ID."""
        if not self.client.has_collection(self.collection_name):
            logger.warning(f"Collection '{self.collection_name}' does not exist")
            return []

        results = self.client.query(
            collection_name=self.collection_name,
            filter=f"document_id == '{document_id}'",
            output_fields=["text"],
        )

        if not results:
            logger.info(f"No chunks found for document_id={document_id}")
            return []

        chunks = [chunk for r in results if (chunk := r.get("text", None))]

        logger.info(f"Retrieved {len(chunks)} chunks for document_id={document_id} from {self.collection_name}")
        return chunks
        