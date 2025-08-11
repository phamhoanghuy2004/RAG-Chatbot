import os
import re
from qdrant_client import QdrantClient,models
from django.core.files.storage import default_storage

# Thông tin Qdarnt
QDRANT_URL = "https://f3f9386a-ebda-4e35-ad7e-65dcd0a0a946.us-east4-0.gcp.cloud.qdrant.io"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.8aC68kp-Djwk4V5Jj1WgyctXBQvxWn1YTPr9OstxCm0"

#Cấu hình client Qdrant
qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
collection_name = "knowledge_base"

def remove_old_software_pdf(docs_dir, name_software):
    for f in get_valid_pdf_files(docs_dir):
        existing_software = extract_software_name(f)
        if existing_software and existing_software.lower() == name_software.lower():
            update_points(f)
            old_file_path = os.path.join(docs_dir, f)
            if default_storage.exists(old_file_path):
                default_storage.delete(old_file_path)
            break
        
        
def save_pdf_to_storage(pdf, docs_dir):
    save_path = os.path.join(docs_dir, pdf.name)
    saved_relative_path = default_storage.save(save_path, pdf)
    return default_storage.path(saved_relative_path)  # absolute path

def get_valid_pdf_files(docs_dir):
    os.makedirs(docs_dir, exist_ok=True)
    return [f for f in os.listdir(docs_dir) if is_valid_pdf_name(f)]

def is_valid_pdf_name(file_name: str) -> bool:
    pattern = r'^HDSD_[a-zA-Z0-9_]+_[a-zA-Z0-9_]+\.pdf$'
    return re.match(pattern, file_name, re.IGNORECASE) is not None

def extract_software_name (file_name: str) -> str:
    """
    Tách phần mềm từ định dạng: HDSD_<TênPhanMem>_<Release>.pdf
    """
    parts = file_name.split('_')
    if (len(parts) >=3):
        return parts[1]
    return None

def update_points (source : str):
    # Xoá tất cả point có "source" trùng 
    qdrant_client.delete(
        collection_name="knowledge_base",
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.source",
                        match=models.MatchValue(value=source),
                    ),
                ],
            )
        ),
        wait=True
    )
    print("Đã update thành công khi có phiên bản update")