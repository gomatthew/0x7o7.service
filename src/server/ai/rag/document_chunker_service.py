# -*- coding: utf-8 -*-
import re
import traceback

from langchain_text_splitters import RecursiveCharacterTextSplitter

from src.configs import logger
from src.server.ai.rag.rag_dto import DocumentChunkDto, LoadedDocumentDto


class DocumentChunker:
    def split_documents(self, docs: list[LoadedDocumentDto], chunk_size: int,
                        chunk_overlap: int) -> list[DocumentChunkDto]:
        try:
            chunks = []
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=chunk_size,
                chunk_overlap=chunk_overlap,
                separators=["\n# ", "\n## ", "\n### ", "\n\n", "\n", "。", "？", "！", "；", ";", "，", ",", " ", ""],
            )
            chunk_index = 0
            for doc in docs:
                section_title = self.get_section_title(doc.content)
                for text in splitter.split_text(doc.content):
                    content = text.strip()
                    if not content:
                        continue
                    metadata = {**doc.metadata, "section_title": section_title, "chunk_index": chunk_index}
                    chunks.append(DocumentChunkDto(content=content, metadata=metadata))
                    chunk_index += 1
            return chunks
        except BaseException as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            raise

    @staticmethod
    def get_section_title(text: str) -> str | None:
        for line in text.splitlines():
            value = line.strip()
            if not value:
                continue
            if value.startswith("#"):
                return value.strip("#").strip()
            if re.match(r"^第[一二三四五六七八九十\d]+[章节条]", value):
                return value[:80]
            if len(value) <= 40:
                return value
            return None
        return None


document_chunker = DocumentChunker()
