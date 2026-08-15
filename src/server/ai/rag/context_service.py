# -*- coding: utf-8 -*-
from src.configs import get_setting
from src.server.ai.rag.rag_dto import RetrievedDocumentDto

setting = get_setting()


class ContextBuilder:
    def build(self, docs: list[RetrievedDocumentDto], max_chars: int | None = None) -> str:
        if not docs:
            return ""
        max_chars = max_chars or setting.RAG_MAX_CONTEXT_CHARS
        parts = []
        total_len = 0
        for index, doc in enumerate(docs, start=1):
            filename = doc.metadata.get("filename") or doc.metadata.get("source") or "document"
            page = doc.metadata.get("page")
            section_title = doc.metadata.get("section_title")
            source_id = doc.metadata.get("source_id") or f"source-{index}"
            source_line = f"SOURCE_FILE: {filename}"
            if page:
                source_line += f"; PAGE: {page}"
            if section_title:
                source_line += f"; SECTION: {section_title}"
            source_line += f"; SOURCE_ID: {source_id}"
            part = f"[SOURCE {index}]\n{source_line}\nCONTENT:\n{doc.content}\n"
            if total_len + len(part) > max_chars:
                remain = max_chars - total_len
                if remain > 120:
                    parts.append(part[:remain])
                break
            parts.append(part)
            total_len += len(part)
        return "\n".join(parts)

    @staticmethod
    def to_sources(docs: list[RetrievedDocumentDto]) -> list[dict]:
        sources = []
        for index, doc in enumerate(docs, start=1):
            metadata = dict(doc.metadata or {})
            filename = metadata.get("original_filename") or metadata.get("filename") or metadata.get("source") or "document"
            chunk_index = metadata.get("chunk_index")
            source_id = metadata.get("source_id") or f"source-{index}"
            excerpt = " ".join(doc.content.split())[:360]
            sources.append({
                "source_id": source_id,
                "filename": filename,
                "page": metadata.get("page"),
                "chunk_index": chunk_index,
                "excerpt": excerpt,
            })
        return sources


context_builder = ContextBuilder()
