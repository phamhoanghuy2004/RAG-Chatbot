from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import (
    PdfPipelineOptions,
)
from docling.document_converter import DocumentConverter, PdfFormatOption
import re
from . import summary
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
import os
import base64
import torch


def get_list_header (docling_documents):
    list_header = []
    for item in docling_documents.texts:
        if item.label == "section_header":
            list_header.append(item.text)
    return list_header

def filter_header (list_header):
    pattern =  pattern = r"^[0-9A-Z][a-zA-Z0-9À-Ỹà-ỹĐđ\s._/,-]*$"
    filtered_header = []
    for header in list_header:
        header = header.strip()
        if header and len(header) > 2 and re.match(pattern,header):
            filtered_header.append(header)
        
    return filtered_header

def in_list_header (line, list_header): 
    if not line:
        return False
    if not line[0] == '#':
        return False
    return any (header in line for header in list_header)

def extract_context_by_headings(markdown_text, list_header):
    contexts = []
    current = ""
    lines = markdown_text.split('\n')
    
    for line in lines:
        if in_list_header (line,list_header):  # Phát hiện tiêu đề
            if current:  # Lưu chunk trước đó nếu có
                contexts.append(current)
            current = line.strip() + "\n"  # Bắt đầu chunk mới với tiêu đề
        else:
            current +=  line.strip() + "\n" # Thêm nội dung vào chunk hiện tại
    
    # Lưu chunk cuối cùng
    if current:
        contexts.append(current)
    
    return contexts

def chunk_by_title (pdf_text_as_markdown : str, list_header):
    filtered_headers = filter_header (list_header)
    contexts = extract_context_by_headings (pdf_text_as_markdown, filtered_headers) # mang cac context theo title
    summarize_chain = summary.create_summarize_chain ()
    summaries = summarize_chain.batch(contexts, {"max_concurrency" : 1}) 
    return contexts, summaries   
    
def extract_text_by_docling (pdf_path: str):
    
    # Mẫu converter 1: PyPdfium without EasyOCR
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True
    device = AcceleratorDevice.CUDA if torch.cuda.is_available() else AcceleratorDevice.CPU
    pipeline_options.accelerator_options = AcceleratorOptions (
        device=device
    )
    pipeline_options.generate_picture_images = True  # Bật trích xuất hình ảnh
    pipeline_options.images_scale = 2  # Phóng to hình ảnh gấp đôi

    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options, backend=PyPdfiumDocumentBackend
            )
        }
    )
    
    result = doc_converter.convert(pdf_path)
    
    return result


def extract_images (docling_documents, images_dir,  name_software, version_software, url_prefix="/extracted_images/"):
    # Tạo đường dẫn thư mục lưu lại hình ảnh
    if not os.path.exists(images_dir):
        os.makedirs(images_dir)

    image_paths = []

    for i, pic in enumerate(docling_documents.pictures):
        uri_str = str(pic.image.uri)
        base64_str = uri_str.split(",")[1]
        # giải mã base64 thành dữ liệu nhị phân
        image_data = base64.b64decode(base64_str)
        
        fileName = f"image_{name_software}_{version_software}_{i}.png"
        filePath = os.path.join(images_dir,fileName)
        
        #Lưu file hình ảnh
        with open(filePath, "wb") as f:
            f.write(image_data)
            
        # Thêm vào mãng image_paths
        image_paths.append(f"{url_prefix}{fileName}")
        
    return image_paths

def replace_img_html (image_paths, pdf_as_markdown):
    index = 0
    lines = pdf_as_markdown.splitlines()
    result_lines = []
    for line in lines:
        if line.strip() == "<!-- image -->" and index < len(image_paths):
            result_lines.append(f"<img src='{image_paths[index]}' alt='picture' class='pictureResponse' />")
            index = index + 1
        else:
            result_lines.append(line)
    return "\n".join(result_lines)
