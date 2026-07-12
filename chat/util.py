import os
import re
from qdrant_client import QdrantClient
from qdrant_client.http.models import Filter, FieldCondition, MatchValue, FilterSelector
from django.core.files.storage import default_storage
import valkey
from django.conf import settings

# Cấu hình client Qdrant, client valkey 
qdrant_client = QdrantClient(url=settings.QDRANT_URL, api_key=settings.QDRANT_API_KEY)
valkey_client = valkey.from_url(settings.VALKEY_URL)
collection_name = settings.COLLECTION_NAME

def remove_old_software_pdf(docs_dir, full_name, name_software, version_software):
    try:
        from .models import Document
        
        # 1) Xóa bản ghi trong database trước
        Document.objects.filter(document_name=full_name).delete()
        
        # 2) Xóa điểm vector ở Qdrant và dữ liệu ở Valkey
        list_uuids = update_points(name_software, version_software)
        update_docstore(list_uuids)
        
        # 3) Xóa cache TF-IDF
        from . import embedding
        embedding.clear_tfidf_cache(name_software)
        
        # 4) Nếu file vật lý vẫn tồn tại (ví dụ còn sót lại), tiến hành xóa
        old_file_path = os.path.join(docs_dir, full_name)
        if default_storage.exists(old_file_path):
            default_storage.delete(old_file_path)
    except Exception as e:
        print(f"Error when deleting old file: {e}")   
        raise         
  
def update_docstore (list_uuids):
    if list_uuids:
        deleted_count = valkey_client.delete(*list_uuids) 
        print(f"Deleted {deleted_count} key in docstore")
        
def save_pdf_to_storage(pdf, docs_dir):
    try:
        # Ensure docs_dir is relative to the storage location
        rel_dir = os.path.relpath(docs_dir, settings.BASE_DIR)
        rel_path = os.path.join(rel_dir, pdf.name)
        print(f"Saving PDF to relative path: {rel_path}")
        saved_relative_path = default_storage.save(rel_path, pdf)
        abs_path = default_storage.path(saved_relative_path)
        print(f"Saved to: {abs_path}")
        return abs_path  # absolute path
    except Exception as ex:
        print(f"Error when saving file: {ex}")
        import traceback
        traceback.print_exc()
        raise

def get_valid_pdf_files(docs_dir):
    try:
        os.makedirs(docs_dir, exist_ok=True)
        return [f for f in os.listdir(docs_dir) if is_valid_pdf_name(f)]
    except Exception as ex:
        print(f"Error reading PDF file from {docs_dir}: {ex}")
        return []

def is_valid_pdf_name(file_name: str) -> bool:
    return file_name.lower().endswith('.pdf')

def extract_software_name (file_name: str) -> tuple:
    """
    Tách phần mềm từ tên file PDF (lấy tên file bỏ đuôi mở rộng, không cần version)
    """
    name_without_ext = os.path.splitext(file_name)[0]
    return name_without_ext, None

def update_points (name_software: str, version_software: str = None):
    # Kiểm tra xem collection đã tồn tại trong Qdrant chưa
    try:
        collections = qdrant_client.get_collections().collections
        if not any(c.name == collection_name for c in collections):
            print(f"Collection {collection_name} chưa tồn tại. Bỏ qua bước xóa chỉ mục cũ.")
            return []
    except Exception as ec:
        print(f"Lỗi khi kiểm tra collections trong update_points: {ec}")
        return []

    must_conditions = [
        FieldCondition (
            key = "metadata.source",
            match = MatchValue(value=name_software)
        )
    ]
    if version_software is not None:
        must_conditions.append(
            FieldCondition (
                key = "metadata.version",
                match = MatchValue(value=version_software)
            )
        )
        
    filter_condition = Filter (
        must = must_conditions
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
    
    print(f"Updated successfully ({len(all_points)} point deleted)")
    return deleted_doc_ids

keys = valkey_client.keys()
print(f"Total keys: {len(keys)}")