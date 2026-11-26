"""
Document Processor
==================
Handles PDF/CSV/text document loading, text extraction, chunking, and
vector store creation using LangChain.
"""

import os
from pathlib import Path
from typing import List, Tuple

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    from langchain.text_splitter import RecursiveCharacterTextSplitter

from langchain_community.vectorstores import FAISS

try:
    from langchain_core.documents import Document
except ImportError:
    from langchain.schema import Document

from forgeai.config import EmbeddingConfig, get_embeddings


def load_documents(doc_folder: str) -> List[Document]:
    """
    Load all supported documents from a folder.
    Supports: PDF (.pdf), CSV (.csv), Text (.txt), Markdown (.md)
    """
    documents = []
    folder = Path(doc_folder)

    if not folder.exists():
        raise FileNotFoundError(f"Document folder not found: {doc_folder}")

    for file_path in sorted(folder.iterdir()):
        if file_path.suffix.lower() == ".pdf":
            documents.extend(_load_pdf(file_path))
        elif file_path.suffix.lower() == ".csv":
            documents.extend(_load_csv(file_path))
        elif file_path.suffix.lower() in (".txt", ".md"):
            documents.extend(_load_text(file_path))

    if not documents:
        raise ValueError(f"No supported documents found in {doc_folder}")

    return documents


def _load_pdf(file_path: Path) -> List[Document]:
    """Extract text from PDF using PyPDF2, fallback to pdfplumber."""
    docs = []
    try:
        from PyPDF2 import PdfReader
        reader = PdfReader(str(file_path))
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text and text.strip():
                docs.append(Document(
                    page_content=text,
                    metadata={
                        "source": file_path.name,
                        "page": i + 1,
                        "type": "pdf"
                    }
                ))
    except Exception:
        # Fallback to pdfplumber
        import pdfplumber
        with pdfplumber.open(str(file_path)) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if text and text.strip():
                    docs.append(Document(
                        page_content=text,
                        metadata={
                            "source": file_path.name,
                            "page": i + 1,
                            "type": "pdf"
                        }
                    ))
    return docs


def _load_csv(file_path: Path) -> List[Document]:
    """Load CSV file, each row becomes a document."""
    import csv
    docs = []
    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            # Format row as readable text
            text = " | ".join(f"{k}: {v}" for k, v in row.items() if v)
            if text.strip():
                docs.append(Document(
                    page_content=text,
                    metadata={
                        "source": file_path.name,
                        "row": i + 1,
                        "type": "csv"
                    }
                ))
    return docs


def _load_text(file_path: Path) -> List[Document]:
    """Load a text or markdown file."""
    text = file_path.read_text(encoding="utf-8", errors="replace")
    if text.strip():
        return [Document(
            page_content=text,
            metadata={
                "source": file_path.name,
                "type": "text"
            }
        )]
    return []


def chunk_documents(
    documents: List[Document],
    chunk_size: int = 500,
    chunk_overlap: int = 100
) -> List[Document]:
    """Split documents into smaller chunks for embedding."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        length_function=len,
        separators=["\n\n", "\n", ". ", " ", ""]
    )
    chunks = splitter.split_documents(documents)
    # Add chunk index to metadata
    for i, chunk in enumerate(chunks):
        chunk.metadata["chunk_id"] = i
    return chunks


def create_vector_store(
    chunks: List[Document],
    embedding_config: EmbeddingConfig
) -> FAISS:
    """Create a FAISS vector store from document chunks."""
    embeddings = get_embeddings(embedding_config)
    vector_store = FAISS.from_documents(chunks, embeddings)
    return vector_store


def get_document_summary(documents: List[Document]) -> str:
    """Create a summary of loaded documents for the requirements stage."""
    summary_parts = []
    sources = {}
    for doc in documents:
        source = doc.metadata.get("source", "unknown")
        if source not in sources:
            sources[source] = {
                "type": doc.metadata.get("type", "unknown"),
                "preview": doc.page_content[:300],
                "pages": set()
            }
        if "page" in doc.metadata:
            sources[source]["pages"].add(doc.metadata["page"])

    for source, info in sources.items():
        pages_str = ""
        if info["pages"]:
            pages_str = f" ({len(info['pages'])} pages)"
        summary_parts.append(
            f"- **{source}** [{info['type']}]{pages_str}:\n  "
            f"Preview: {info['preview'][:200]}..."
        )

    return "\n".join(summary_parts)
