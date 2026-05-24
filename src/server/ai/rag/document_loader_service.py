# -*- coding: utf-8 -*-
import os
import traceback
from typing import Optional

from src.configs import logger
from src.server.ai.rag.rag_dto import LoadedDocumentDto


class DocumentLoaderService:
    def load(self, file_path: str, metadata: Optional[dict] = None) -> list[LoadedDocumentDto]:
        try:
            ext = os.path.splitext(file_path)[-1].lower()
            metadata = metadata or {}
            match ext:
                case ".txt":
                    return self.load_text(file_path, metadata)
                case ".md":
                    return self.load_text(file_path, metadata)
                case ".pdf":
                    return self.load_pdf(file_path, metadata)
                case ".docx":
                    return self.load_docx(file_path, metadata)
                case _:
                    raise ValueError(f"暂不支持的文件类型: {ext}")
        except BaseException as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            raise

    @staticmethod
    def read_text(file_path: str) -> str:
        for encoding in ["utf-8", "utf-8-sig", "gb18030"]:
            try:
                with open(file_path, "r", encoding=encoding) as f:
                    return f.read()
            except UnicodeDecodeError:
                continue
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    def load_text(self, file_path: str, metadata: dict) -> list[LoadedDocumentDto]:
        return [LoadedDocumentDto(content=self.read_text(file_path), metadata={**metadata, "page": None})]

    def load_pdf(self, file_path: str, metadata: dict) -> list[LoadedDocumentDto]:
        try:
            from pypdf import PdfReader
        except BaseException as e:
            raise RuntimeError("缺少 pypdf 依赖，无法解析 PDF") from e
        reader = PdfReader(file_path)
        docs = []
        for index, page in enumerate(reader.pages):
            text = page.extract_text() or ""
            if text.strip():
                docs.append(LoadedDocumentDto(content=text, metadata={**metadata, "page": index + 1}))
        return docs

    def load_docx(self, file_path: str, metadata: dict) -> list[LoadedDocumentDto]:
        try:
            from docx import Document
        except BaseException as e:
            raise RuntimeError("缺少 python-docx 依赖，无法解析 DOCX") from e
        doc = Document(file_path)
        text = "\n".join([p.text for p in doc.paragraphs if p.text])
        return [LoadedDocumentDto(content=text, metadata={**metadata, "page": None})]


document_loader_service = DocumentLoaderService()
