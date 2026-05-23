import os
from . import docling_extract
from . import embedding


def ingest_pdf_docling(pdf_path: str, name_software: str, version_software: str, images_dir: str):
    try:
        # 1) Convert PDF using Docling (without image extraction)
        result_docling_conv = docling_extract.extract_text_by_docling(pdf_path)
        pdf_as_markdown = result_docling_conv.document.export_to_markdown()
        
        # 2) Chunk using the new recursive character splitter
        contexts, summaries = docling_extract.chunk_recursive(pdf_as_markdown)
        
        # 3) Embed and store summaries in Qdrant and raw texts in Redis
        embedding.embedding_multivector(contexts, summaries, name_software, version_software)
    except Exception as e:
        print("Error in ingest_pdf_docling:", str(e))
        raise RuntimeError("Unable to parse pdf")