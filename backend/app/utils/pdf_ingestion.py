from __future__ import annotations

import io
import re
from datetime import datetime
from typing import Callable, Dict, List, Optional, Tuple

import fitz
from PIL import Image

from app.memory.vector_store import VectorStore
from app.memory.episodic_store import EpisodicStore


TokenChunk = Tuple[str, int, int]
ProgressCallback = Callable[[int, int, str], None]


def ingest_pdf_file(
    file_path: str,
    filename: str,
    source_label: Optional[str] = None,
    progress_callback: Optional[ProgressCallback] = None,
) -> Dict[str, int]:
    vector_store = VectorStore()
    episodic_store = EpisodicStore()
    source_name = filename
    label = source_label or filename
    timestamp = datetime.utcnow().isoformat()

    with fitz.open(file_path) as doc:
        total_pages = doc.page_count
        documents: List[str] = []
        metadatas: List[Dict[str, object]] = []
        chunk_index = 0

        for page_index in range(total_pages):
            page_number = page_index + 1
            if progress_callback:
                progress_callback(page_number, total_pages, "processing")

            page = doc.load_page(page_index)
            page_text = _extract_page_text(page)

            if not page_text.strip():
                page_text = _extract_text_with_ocr(page)

            if not page_text.strip():
                continue

            chunks = _chunk_text_by_tokens(page_text, chunk_size=500, overlap=50)
            for chunk_text, start_token, end_token in chunks:
                documents.append(chunk_text)
                metadatas.append(
                    {
                        "source": source_name,
                        "page": page_number,
                        "type": "pdf",
                        "chunk_index": chunk_index,
                        "start_token": start_token,
                        "end_token": end_token,
                        "ingested_at": timestamp,
                    }
                )
                chunk_index += 1

        if not documents:
            raise ValueError("No extractable text found in PDF")

        vector_store.add_documents(documents=documents, metadatas=metadatas)

        for content in documents:
            episodic_store.append_memory(
                source=label,
                content=content,
                version=1,
                confidence=1.0,
            )

    return {
        "chunks_ingested": len(documents),
        "total_pages": total_pages,
    }


def _extract_page_text(page: fitz.Page) -> str:
    blocks = page.get_text("blocks")
    if blocks:
        ordered = sorted(blocks, key=lambda b: (b[1], b[0]))
        parts = [block[4].strip() for block in ordered if block[4].strip()]
        return "\n".join(parts)

    return page.get_text("text")


def _extract_text_with_ocr(page: fitz.Page) -> str:
    try:
        import pytesseract
    except Exception:
        return ""

    pix = page.get_pixmap(dpi=300)
    mode = "RGBA" if pix.alpha else "RGB"
    image = Image.frombytes(mode, [pix.width, pix.height], pix.samples)
    text = pytesseract.image_to_string(image)
    return text or ""


def _chunk_text_by_tokens(text: str, chunk_size: int, overlap: int) -> List[TokenChunk]:
    tokens = re.findall(r"\S+", text)
    if not tokens:
        return []

    chunks: List[TokenChunk] = []
    start = 0
    index = 0

    while start < len(tokens):
        end = min(start + chunk_size, len(tokens))
        chunk_tokens = tokens[start:end]
        chunk_text = " ".join(chunk_tokens).strip()
        if chunk_text:
            chunks.append((chunk_text, start, end))
            index += 1

        if end >= len(tokens):
            break

        start = max(0, end - overlap)

    return chunks
