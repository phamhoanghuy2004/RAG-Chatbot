from docling.datamodel.accelerator_options import AcceleratorDevice, AcceleratorOptions
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import DocumentConverter, PdfFormatOption
from docling.backend.pypdfium2_backend import PyPdfiumDocumentBackend
from docling.chunking import HybridChunker
import torch
from . import summary


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


def chunk_by_title(docling_result):
    """
    Parent-Child Retrieval / Map-Reduce RAG Chunking:
    Sử dụng HybridChunker của Docling với max_tokens cực lớn (1.000.000)
    để gom toàn bộ nội dung dưới mỗi Heading/Title thành đúng 1 chunk duy nhất.

    Thuật toán HybridChunker: gom tất cả đoạn văn có chung Tiêu đề,
    chỉ dừng khi gặp Tiêu đề mới HOẶC chạm max_tokens.
    → max_tokens khổng lồ = chỉ cắt tại ranh giới heading.

    Bước summarize phía sau sẽ lo việc nén các chunk dài.
    """
    doc = docling_result.document

    chunker = HybridChunker(
        max_tokens=1_000_000,   # Cực lớn → chỉ split khi gặp Heading mới
        merge_peers=True,       # Gom các đoạn cùng cấp heading lại với nhau
    )

    chunks = list(chunker.chunk(doc))

    if not chunks:
        print("⚠️ HybridChunker không tạo được chunk nào!")
        return [], []

    # Xây dựng danh sách contexts: mỗi chunk = heading path + nội dung
    contexts = []
    for i, chunk in enumerate(chunks):
        headings = []
        if chunk.meta and hasattr(chunk.meta, 'headings') and chunk.meta.headings:
            headings = chunk.meta.headings

        title = " > ".join(headings) if headings else f"Phần {i + 1}"

        # Gắn heading path vào đầu chunk để giữ ngữ cảnh khi retrieve
        context_text = f"## {title}\n\n{chunk.text}"
        contexts.append(context_text)

    # =================== LOG KẾT QUẢ PHÂN ĐOẠN ===================
    print(f"\n{'=' * 90}")
    print(f"  KẾT QUẢ PHÂN ĐOẠN THEO TITLE (HybridChunker) — {len(contexts)} chunks")
    print(f"{'=' * 90}")
    for idx, ctx in enumerate(contexts):
        print(f"\n--- [CHUNK {idx + 1}/{len(contexts)}] (Độ dài: {len(ctx)} ký tự) ---")
        # Chỉ in 500 ký tự đầu để log không quá dài
        preview = ctx[:500].strip()
        if len(ctx) > 500:
            preview += "\n... (đã cắt bớt để hiển thị)"
        print(preview)
        print("-" * 80)
    print(f"{'=' * 90}\n")

    # =================== SUMMARIZE TỪNG CHUNK ===================
    summarize_chain = summary.create_summarize_chain(bypass_summary=False)
    summaries = []
    import time

    for i, ctx in enumerate(contexts):
        # Proactive sleep to prevent hitting TPM limits on large documents
        if i > 0:
            time.sleep(1.0)

        print(f"📝 Summarizing chunk {i + 1}/{len(contexts)} ({len(ctx)} ký tự)...")
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
                    print(f"⏳ Rate limit hit at chunk {i + 1}. Retrying in {delay}s... (Retries left: {retries})")
                    time.sleep(delay)
                    delay *= 2.0  # Exponential backoff
                    retries -= 1
                else:
                    print(f"❌ Error summarizing chunk {i + 1}: {e}")
                    summaries.append(ctx)  # Fallback to original text
                    break
        else:
            print(f"❌ Failed to summarize chunk {i + 1} after retries. Using original text as summary.")
            summaries.append(ctx)  # Fallback to original text

    return contexts, summaries
