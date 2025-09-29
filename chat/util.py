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
        for f in get_valid_pdf_files(docs_dir):
            if f and f.lower() == full_name.lower():
                list_uuids = update_points(name_software, version_software)
                update_docstore (list_uuids)
                # Clear TF-IDF cache for this source
                from . import embedding
                embedding.clear_tfidf_cache(name_software)
                old_file_path = os.path.join(docs_dir, f)
                if default_storage.exists(old_file_path):
                    default_storage.delete(old_file_path)
                break
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
    
    print(f"Updated successfully ({len(all_points)} point deleted)")
    return deleted_doc_ids

keys = valkey_client.keys()
print(f"Total keys: {len(keys)}")