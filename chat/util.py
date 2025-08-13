import os
import re
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, FilterSelector
from django.core.files.storage import default_storage
import valkey

# Thông tin Qdarnt
QDRANT_URL = "https://f3f9386a-ebda-4e35-ad7e-65dcd0a0a946.us-east4-0.gcp.cloud.qdrant.io"
QDRANT_API_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.8aC68kp-Djwk4V5Jj1WgyctXBQvxWn1YTPr9OstxCm0"
valkey_url = 'rediss://default:AVNS_rmKGsDZar026KHs_sI5@valkey-dostore-phamhoanghuy-96f0.f.aivencloud.com:15294'

# Cấu hình client Qdrant, client valkey 
qdrant_client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
valkey_client = valkey.from_url(valkey_url)
collection_name = "knowledge_base"

def remove_old_software_pdf(docs_dir, full_name, name_software, version_software):
    for f in get_valid_pdf_files(docs_dir):
        if f and f.lower() == full_name.lower():
            list_uuids = update_points(name_software, version_software)
            update_docstore (list_uuids)
            old_file_path = os.path.join(docs_dir, f)
            if default_storage.exists(old_file_path):
                default_storage.delete(old_file_path)
            break
  
  
def update_docstore (list_uuids):
    if list_uuids:
        deleted_count = valkey_client.delete(*list_uuids) 
        print(f"Đã xóa {deleted_count} key trong docstore")
        
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
        return parts[1], parts[2].rsplit('.',1)[0]
    return None, None

def update_points (name_software: str, version_software: str):
    
    filter_condition = Filter (
        must = [
            FieldCondition (
                key = "metadata.source",
                match = MatchValue(value=name_software)
            ),
            FieldCondition (
                key = "metadata.version",
                match = MatchValue(value=version_software)
            )
        ]
    )
    
    # Lay danh sach docs_id
    all_points = []
    scroll_offset = None
    while True:
        points,scroll_offset = qdrant_client.scroll(
            collection_name=collection_name,
            scroll_filter=filter_condition,
            limit=100, # So point tren moi batch
            offset=scroll_offset,
            with_payload=["metadata.doc_id"]
        )
    
        if not points:
            break
        
        all_points.extend(points)
        
        if scroll_offset is None:
            break
    
    deleted_doc_ids = [point.payload["metadata"]["doc_id"] for point in all_points if "metadata" in point.payload and "doc_id" in point.payload["metadata"]]

    # Xoa cac point cu
    qdrant_client.delete(
        collection_name=collection_name,
        points_selector=FilterSelector (
            filter=filter_condition
        ),
        wait=True
    )
    
    print(f"✅ Đã update thành công ({len(all_points)} point bị xóa)")
    return deleted_doc_ids