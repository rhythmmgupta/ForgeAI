"""Tests for Document Processor and Chunking"""

import pytest
from pathlib import Path
from forgeai.core.document_processor import (
    load_documents, chunk_documents, create_vector_store, get_document_summary
)
from forgeai.config import EmbeddingConfig


def test_load_and_chunk_txt_documents(tmp_path):
    doc_file = tmp_path / "test_policy.txt"
    doc_file.write_text("Section 1: Annual Leave\nEmployees are entitled to 21 days annual leave.\n\nSection 2: Sick Leave\nEmployees get 12 days sick leave.")
    
    docs = load_documents(str(tmp_path))
    assert len(docs) >= 1
    assert "Annual Leave" in docs[0].page_content

    chunks = chunk_documents(docs, chunk_size=50, chunk_overlap=10)
    assert len(chunks) >= 2
    assert "chunk_id" in chunks[0].metadata


def test_load_csv_documents(tmp_path):
    csv_file = tmp_path / "catalogue.csv"
    csv_file.write_text("item,cost,vendor\nTurbine,5000,MarineCorp\nValve,120,ValveCo\n")
    
    docs = load_documents(str(tmp_path))
    assert len(docs) == 2
    assert any("Turbine" in d.page_content for d in docs)


def test_document_summary(tmp_path):
    doc_file = tmp_path / "guide.txt"
    doc_file.write_text("Maritime safety operational guide.\nAll vessels must carry lifejackets.")
    docs = load_documents(str(tmp_path))
    summary = get_document_summary(docs)
    assert "guide.txt" in summary


def test_local_deterministic_embeddings_faiss_search(tmp_path):
    from langchain_community.vectorstores import FAISS
    from forgeai.config import LocalDeterministicEmbeddings

    doc_file = tmp_path / "leave.txt"
    doc_file.write_text("Shore staff receive 21 days of paid annual leave per year.")
    docs = load_documents(str(tmp_path))
    chunks = chunk_documents(docs, chunk_size=200, chunk_overlap=20)
    emb = LocalDeterministicEmbeddings(dim=384)
    vs = FAISS.from_documents(chunks, emb)
    results = vs.similarity_search_with_score("annual leave days", k=2)
    assert len(results) >= 1
    assert "21 days" in results[0][0].page_content
