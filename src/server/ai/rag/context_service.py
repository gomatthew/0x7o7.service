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
            filename = doc.metadata.get("filename") or doc.metadata.get("source") or "未知文件"
            page = doc.metadata.get("page")
            section_title = doc.metadata.get("section_title")
            source_line = f"来源：{filename}"
            if page:
                source_line += f" 第 {page} 页"
            if section_title:
                source_line += f" / {section_title}"
            part = f"[资料{index}]\n{source_line}\n内容：\n{doc.content}\n"
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
        return [{"content": doc.content, "score": doc.score, "metadata": doc.metadata} for doc in docs]


context_builder = ContextBuilder()
