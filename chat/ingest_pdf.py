import os
from . import docling_extract
from . import embedding


def ingest_pdf_docling (pdf_path: str, images_dir: str):
    source_name = os.path.basename(pdf_path) # lấy tên của cái file 
    result_docling_conv =  docling_extract.extract_text_by_docling(pdf_path)
    image_paths = docling_extract.extract_images (result_docling_conv.document, images_dir, source_name)
    pdf_as_markdown =  docling_extract.replace_img_html (image_paths, result_docling_conv.document.export_to_markdown())
    list_header = docling_extract.get_list_header(result_docling_conv.document)
    contexts, summaries = docling_extract.chunk_by_title (pdf_as_markdown,source_name,list_header)
    embedding.embedding_multivector(contexts, summaries, source_name)