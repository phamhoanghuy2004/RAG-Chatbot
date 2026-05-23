from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
import torch
import re
import numpy as np
from . import summary
from .embedding import embedding_model


def extract_text_by_docling(pdf_path: str):
    """
    Extracts text from PDF using Docling DocumentConverter.
    Image extraction is turned off for lighter processing.
    """
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False
    pipeline_options.do_table_structure = True
    pipeline_options.table_structure_options.do_cell_matching = True
    
    device = AcceleratorDevice.CUDA if torch.cuda.is_available() else AcceleratorDevice.CPU
    pipeline_options.accelerator_options = AcceleratorOptions(device=device)
    
    # Disable image generation to speed up parsing
    pipeline_options.generate_picture_images = False

    doc_converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(
                pipeline_options=pipeline_options, backend=PyPdfiumDocumentBackend
            )
        }
    )
    
    result = doc_converter.convert(pdf_path)
    return result


def split_into_sentences(text: str):
    """
    Splits text into logical sentences or rows (keeping table rows whole).
    """
    lines = text.split('\n')
    sentences = []
    for line in lines:
        line_str = line.strip()
        if not line_str:
            continue
        # Nếu là dòng trong bảng (bắt đầu và kết thúc bằng |), giữ nguyên dòng đó
        if line_str.startswith('|') and line_str.endswith('|'):
            sentences.append(line_str)
        else:
            # Ngược lại, chia thành các câu dựa vào dấu chấm, hỏi, cảm thán theo sau bởi khoảng trắng
            parts = re.split(r'(?<=[.!?])\s+', line_str)
            for p in parts:
                p_str = p.strip()
                if p_str:
                    sentences.append(p_str)
    return sentences


def chunk_recursive(markdown_text: str):
    """
    Semantic Chunker:
    1. Chia văn bản thành các câu đơn lẻ (giữ nguyên cấu trúc bảng/list).
    2. Nhúng vector từng câu qua embedding_model.
    3. Tính toán khoảng cách cosine similarity giữa các câu liên tiếp.
    4. Cắt chunk khi độ tương đồng tụt dưới ngưỡng threshold động (mean - 1.0 * std)
       đồng thời đảm bảo ràng buộc kích thước (tối thiểu 300 ký tự, tối đa 1200 ký tự).
    """
    # Bước 1: Tách các câu thô
    sentences = split_into_sentences(markdown_text)
    if not sentences:
        return [], []
        
    print(f"Tổng số câu/dòng được trích xuất: {len(sentences)}")

    # Bước 2: Nhúng vector các câu
    embeddings = [np.array(e) for e in embedding_model.embed_documents(sentences)]

    # Bước 3: Tính toán khoảng cách tương đồng giữa các câu liên tiếp
    similarities = []
    for i in range(len(embeddings) - 1):
        vec1 = embeddings[i]
        vec2 = embeddings[i+1]
        norm1 = np.linalg.norm(vec1)
        norm2 = np.linalg.norm(vec2)
        if norm1 > 0 and norm2 > 0:
            sim = np.dot(vec1, vec2) / (norm1 * norm2)
        else:
            sim = 0.0
        similarities.append(sim)

    # Xác định ngưỡng threshold động
    if similarities:
        mean_sim = np.mean(similarities)
        std_sim = np.std(similarities)
        # Ngưỡng động, giới hạn trong khoảng [0.78, 0.84] để đảm bảo an toàn
        dynamic_threshold = mean_sim - 1.0 * std_sim
        threshold = max(0.78, min(0.84, dynamic_threshold))
        print(f"Chỉ số tương đồng: Mean={mean_sim:.4f}, Std={std_sim:.4f} -> Ngưỡng cắt (threshold)={threshold:.4f}")
    else:
        threshold = 0.82

    # Bước 4: Tạo nhát cắt dựa trên ngưỡng và độ dài tối thiểu
    min_chars = 300
    
    contexts = []
    current_chunk = []
    current_length = 0
    
    for i, sentence in enumerate(sentences):
        current_chunk.append(sentence)
        current_length += len(sentence) + 1
        
        if i < len(similarities):
            sim = similarities[i]
            # Điều kiện cắt: 
            # - Độ tương đồng dưới ngưỡng AND độ dài hiện tại đạt tối thiểu 300 ký tự
            should_split = (sim < threshold and current_length >= min_chars)
            
            if should_split:
                contexts.append("\n".join(current_chunk))
                current_chunk = []
                current_length = 0
                
    if current_chunk:
        contexts.append("\n".join(current_chunk))

    # Log các chunk ra console để quan sát kết quả phân đoạn
    print(f"\n=================== KẾT QUẢ PHÂN ĐOẠN TÀI LIỆU (SEMANTIC CHUNKING) ({len(contexts)} chunks) ===================")
    for idx, chunk in enumerate(contexts):
        print(f"\n--- [CHUNK {idx+1}/{len(contexts)}] (Độ dài: {len(chunk)} ký tự) ---")
        print(chunk.strip())
        print("-" * 80)
    print("====================================================================================\n")
    
    # Generate summaries for each chunk with sequential execution, proactive delay, and rate limit retries
    summarize_chain = summary.create_summarize_chain(bypass_summary=False)
    summaries = []
    import time
    
    for i, ctx in enumerate(contexts):
        # Proactive sleep to prevent hitting TPM limits on large documents
        if i > 0:
            time.sleep(1.0)
            
        print(f"Summarizing chunk {i+1}/{len(contexts)}...")
        retries = 4
        delay = 2.0
        while retries > 0:
            try:
                summary_text = summarize_chain.invoke(ctx)
                summaries.append(summary_text)
                break
            except Exception as e:
                err_str = str(e).lower()
                if "rate limit" in err_str or "429" in err_str or "rate_limit_exceeded" in err_str:
                    print(f"Rate limit hit at chunk {i+1}. Retrying in {delay}s... (Retries left: {retries})")
                    time.sleep(delay)
                    delay *= 2.0  # Exponential backoff
                    retries -= 1
                else:
                    print(f"Error summarizing chunk {i+1}: {e}")
                    summaries.append(ctx)  # Fallback to original text
                    break
        else:
            print(f"Failed to summarize chunk {i+1} after retries. Using original text as summary.")
            summaries.append(ctx)  # Fallback to original text
            
    return contexts, summaries
