import re
from typing import List
from transformers import AutoTokenizer
from app.core.settings import settings
from docling.chunking import HybridChunker
from docling.document_converter import DocumentConverter
from docling_core.types.doc.document import DoclingDocument
from docling_core.transforms.chunker.tokenizer.huggingface import HuggingFaceTokenizer


class DocumentProcessor:

    def __init__(self, file_path: str) -> None:
        converter = DocumentConverter()
        self.doc: DoclingDocument = converter.convert(file_path).document

    def export_doc_to_markdown(self, output_path: str = None) -> None:
        """
        Export the document to markdown format
        
        Args:
            output_path: Optional path to save the markdown to a file
            
        Returns:
            The markdown content as a string
        """
        md = self.doc.export_to_markdown()
        md = md.replace('<!-- image -->', '')
        md = re.sub(r'\n+', '\n', md)
        
        # Save to file if output_path is provided
        if output_path:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(md)

        
    def chunk_doc(self) -> List[dict]:
        # Use the HuggingFace-compatible tokenizer model for chunking
        tokenizer = HuggingFaceTokenizer(
            tokenizer=AutoTokenizer.from_pretrained(settings.TOKENIZER_MODEL)
        )
        chunker = HybridChunker(
            tokenizer=tokenizer
        )
        chunks: list = []
        
        for chunk in chunker.chunk(dl_doc=self.doc):
            page_nos: list = list({
                prov.page_no 
                for item in chunk.meta.doc_items
                for prov in item.prov
            })
            chunks.append(
                {
                    "text": chunker.contextualize(chunk=chunk),
                    "page_numbers": page_nos
                }
            )
        
        return chunks
