# -*- coding: utf-8 -*-
import traceback
from typing import Optional

from langchain_openai import OpenAIEmbeddings

from src.configs import get_setting, logger

setting = get_setting()


class EmbeddingService:
    def get_embeddings(self, model: Optional[str] = None) -> OpenAIEmbeddings:
        dimensions = setting.EMBEDDING_DIMENSION if setting.EMBEDDING_DIMENSION else None
        return OpenAIEmbeddings(
            model=model or setting.EMBEDDING_MODEL,
            api_key=setting.EMBEDDING_API_KEY,
            base_url=setting.EMBEDDING_BASE_URL,
            dimensions=dimensions,
        )

    def embed_documents(self, texts: list[str], model: Optional[str] = None) -> list[list[float]]:
        try:
            return self.get_embeddings(model=model).embed_documents(texts)
        except BaseException as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            raise

    def embed_query(self, text: str, model: Optional[str] = None) -> list[float]:
        try:
            return self.get_embeddings(model=model).embed_query(text)
        except BaseException as e:
            logger.error(e)
            logger.error(traceback.format_exc())
            raise


embedding_service = EmbeddingService()
