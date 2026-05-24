# -*- coding: utf-8 -*-
import datetime
import json
import os
import traceback
import uuid
from typing import Optional

from fastapi import Body, File, Form, Query, UploadFile

from src.configs import get_setting, logger
from src.enum import FileTypeEnum, RecordStatusEnum, UploadRagFileTypeEnum
from src.server.ai.rag.context_service import context_builder
from src.server.ai.rag.document_chunker_service import document_chunker
from src.server.ai.rag.document_loader_service import document_loader_service
from src.server.ai.rag.query_service import query_processor
from src.server.ai.rag.retrieval_service import retrieval_pipeline
from src.server.ai.rag.vector_store_service import faiss_vector_store_service
from src.server.db.repository import add_file_to_db, create_kb_to_db, get_file_list_from_db, get_kb_from_db, \
    get_kb_list_from_db
from src.server.db.repository.ai_repository import delete_kb_from_db
from src.server.dto import AddFileToDBDTO, ApiCommonResponseDTO
from src.server.utils import TokenChecker

setting = get_setting()


def get_current_user_id(token_checker: TokenChecker = None, user_id: Optional[int | str] = None):
    if isinstance(user_id, (int, str)):
        return str(user_id)
    if isinstance(token_checker, (int, str)) and token_checker:
        return str(token_checker)
    return None


def get_now():
    return datetime.datetime.now().isoformat(timespec="seconds")


def get_kb_relative_path(user_id: str, kb_id: str):
    return os.path.join("kb", str(user_id), kb_id)


def get_kb_absolute_path(kb_path: str):
    if os.path.isabs(kb_path):
        return kb_path
    return os.path.join(setting.BASE_PATH, kb_path)


def get_metadata_path(kb_path: str):
    return os.path.join(get_kb_absolute_path(kb_path), "metadata.json")


def read_metadata(kb_path: str):
    metadata_path = get_metadata_path(kb_path)
    try:
        with open(metadata_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        raise FileNotFoundError("知识库 metadata.json 不存在")
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        raise RuntimeError("知识库 metadata.json 损坏或不可读取")


def write_metadata(kb_path: str, metadata: dict):
    metadata_path = get_metadata_path(kb_path)
    os.makedirs(os.path.dirname(metadata_path), exist_ok=True)
    with open(metadata_path, "w", encoding="utf-8") as f:
        json.dump(metadata, f, ensure_ascii=False, indent=2)


def get_kb_record(kb_id: str):
    record = get_kb_from_db(kb_id)
    if not record:
        raise FileNotFoundError("知识库不存在")
    if not record.get("kb_path"):
        raise RuntimeError("知识库未记录本地文件路径")
    return record


def create_kb(token_checker: TokenChecker,
              kb_name: str = Body(..., description="知识库名称"),
              kb_description: Optional[str] = Body(None, description="知识库描述"),
              business_type: str = Body("default", description="业务类型"),
              knowledge_base_id: Optional[str] = Body(None, description="知识库ID"),
              user_id: Optional[int] = Body(None, description="用户ID")) -> ApiCommonResponseDTO:
    try:
        current_user_id = get_current_user_id(token_checker, user_id)
        if not current_user_id:
            return ApiCommonResponseDTO(message="用户未登录!", status=401).model_dict()
        kb_id = knowledge_base_id or f"kb_{uuid.uuid4().hex[:12]}"
        kb_path = get_kb_relative_path(current_user_id, kb_id)
        abs_kb_path = get_kb_absolute_path(kb_path)
        docs_path = os.path.join(abs_kb_path, "docs")
        os.makedirs(docs_path, exist_ok=True)
        now = get_now()
        metadata = {
            "knowledge_base_id": kb_id,
            "user_id": int(current_user_id) if str(current_user_id).isdigit() else current_user_id,
            "name": kb_name,
            "description": kb_description,
            "business_type": business_type,
            "embedding_model": setting.EMBEDDING_MODEL,
            "embedding_dimension": setting.EMBEDDING_DIMENSION,
            "chunk_size": setting.RAG_CHUNK_SIZE,
            "chunk_overlap": setting.RAG_CHUNK_OVERLAP,
            "document_count": 0,
            "chunk_count": 0,
            "documents": [],
            "path": kb_path,
            "absolute_path": abs_kb_path,
            "created_at": now,
            "updated_at": now,
        }
        write_metadata(kb_path, metadata)
        create_kb_to_db(kb_name=kb_name, kb_description=kb_description, kb_id=kb_id,
                        user_id=current_user_id, kb_path=kb_path)
        return ApiCommonResponseDTO(status=200, message="success", data={
            "knowledge_base_id": kb_id,
            "kb_id": kb_id,
            "path": kb_path,
        }).model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message=str(e)).model_dict()


def get_kb_list(token_checker: TokenChecker,
                page: int = Query(1, description="页数"),
                limit: int = Query(default=10, description="每页数据数"),
                user_id: Optional[int] = Query(None, description="用户ID")) -> ApiCommonResponseDTO:
    try:
        current_user_id = get_current_user_id(token_checker, user_id)
        if not current_user_id:
            return ApiCommonResponseDTO(message="用户未登录!", status=401).model_dict()
        rows = get_kb_list_from_db(user_id=current_user_id, page_no=page, page_size=limit) or []
        data = []
        for row in rows:
            item = dict(row)
            try:
                metadata = read_metadata(row.get("kb_path"))
                item.update({
                    "business_type": metadata.get("business_type"),
                    "embedding_model": metadata.get("embedding_model"),
                    "document_count": metadata.get("document_count", 0),
                    "chunk_count": metadata.get("chunk_count", 0),
                    "updated_at": metadata.get("updated_at"),
                })
            except BaseException as e:
                logger.error(e)
                item.update({"metadata_status": "error", "metadata_message": str(e)})
            data.append(item)
        return ApiCommonResponseDTO(status=200, message="success", data=data).model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message=str(e)).model_dict()


def get_kb_detail(token_checker: TokenChecker,
                  kb_id: str = Query(..., description="kb_id")) -> ApiCommonResponseDTO:
    try:
        record = get_kb_record(kb_id)
        metadata = read_metadata(record.get("kb_path"))
        return ApiCommonResponseDTO(status=200, message="success", data={**record, **metadata}).model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=400, message=str(e)).model_dict()


def delete_kb(token_checker: TokenChecker, kb_id: str = Body(..., description="kb_id")):
    try:
        if not token_checker:
            return ApiCommonResponseDTO(message="用户未登录!", status=401).model_dict()
        delete_kb_from_db(kb_id=kb_id)
        return ApiCommonResponseDTO().model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message=str(e)).model_dict()


def upload_file_to_kb(token_checker: TokenChecker,
                      kb_id: str = Form(..., description="kb_id"),
                      user_id: Optional[int] = Form(None, description="用户ID"),
                      file: UploadFile = File(..., description="上传文件")):
    try:
        current_user_id = get_current_user_id(token_checker, user_id)
        if not current_user_id:
            return ApiCommonResponseDTO(message="用户未登录!", status=401).model_dict()
        record = get_kb_record(kb_id)
        metadata = read_metadata(record.get("kb_path"))
        kb_path = record.get("kb_path")
        abs_kb_path = get_kb_absolute_path(kb_path)
        docs_path = os.path.join(abs_kb_path, "docs")
        os.makedirs(docs_path, exist_ok=True)
        original_filename = os.path.basename(file.filename)
        document_id = f"doc_{uuid.uuid4().hex[:12]}"
        filename = original_filename
        file_path = os.path.join(docs_path, filename)
        if os.path.exists(file_path):
            filename = f"{document_id}_{original_filename}"
            file_path = os.path.join(docs_path, filename)
        with open(file_path, "wb") as f:
            f.write(file.file.read())
        file_type = os.path.splitext(filename)[-1].lower().lstrip(".")
        base_metadata = {
            "document_id": document_id,
            "source": filename,
            "filename": filename,
            "original_filename": original_filename,
            "file_type": file_type,
        }
        loaded_docs = document_loader_service.load(file_path, metadata=base_metadata)
        chunks = document_chunker.split_documents(
            loaded_docs,
            chunk_size=metadata.get("chunk_size") or setting.RAG_CHUNK_SIZE,
            chunk_overlap=metadata.get("chunk_overlap") or setting.RAG_CHUNK_OVERLAP,
        )
        faiss_vector_store_service.save_chunks(
            abs_kb_path,
            chunks,
            embedding_model=metadata.get("embedding_model") or setting.EMBEDDING_MODEL,
        )
        doc_meta = {
            "document_id": document_id,
            "filename": filename,
            "original_filename": original_filename,
            "file_path": os.path.join("docs", filename),
            "file_type": file_type,
            "chunk_count": len(chunks),
            "created_at": get_now(),
        }
        metadata.setdefault("documents", []).append(doc_meta)
        metadata["document_count"] = len(metadata.get("documents", []))
        metadata["chunk_count"] = sum([item.get("chunk_count", 0) for item in metadata.get("documents", [])])
        metadata["updated_at"] = get_now()
        write_metadata(kb_path, metadata)
        add_file_to_db(AddFileToDBDTO(file_id=document_id,
                                      file_name=filename,
                                      file_path=doc_meta.get("file_path"),
                                      meta_data={"chunk_count": len(chunks), "kb_path": kb_path},
                                      file_extension=file_type,
                                      biz_type=FileTypeEnum.KB_FILE,
                                      biz_id=kb_id,
                                      created_user_id=current_user_id))
        return ApiCommonResponseDTO(status=200, message="success", data={
            "knowledge_base_id": kb_id,
            "filename": filename,
            "chunk_count": len(chunks),
            "embedding_model": metadata.get("embedding_model"),
            "status": "success",
        }).model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message=str(e)).model_dict()


def upload_text_to_kb(token_checker: TokenChecker, kb_id: str = Body(..., description="kb_id")):
    try:
        if not token_checker:
            return ApiCommonResponseDTO(message="用户未登录!", status=401).model_dict()
        return ApiCommonResponseDTO(status=400, message="not supported yet").model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message=str(e)).model_dict()


def get_file_progress(token_checker: TokenChecker, kb_id: str = Query(..., description="kb_id"),
                      batch: str = Query(None, description="batch")):
    try:
        if not token_checker:
            return ApiCommonResponseDTO(message="用户未登录!", status=401).model_dict()
        record = get_kb_record(kb_id)
        abs_kb_path = get_kb_absolute_path(record.get("kb_path"))
        indexing_status = UploadRagFileTypeEnum.COMPLETED.value if faiss_vector_store_service.index_file_exists(
            abs_kb_path) else UploadRagFileTypeEnum.EMBEDDING.value
        return ApiCommonResponseDTO(status=200, message="success", data={"indexing_status": indexing_status}).model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message=str(e)).model_dict()


def get_kb_file_list(token_checker: TokenChecker, kb_id: str = Query(..., description="kb_id")):
    return get_file_list(token_checker=token_checker, kb_id=kb_id)


def delete_file_to_kb():
    try:
        return ApiCommonResponseDTO(status=400, message="not supported yet").model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message=str(e)).model_dict()


def get_file_seg_list():
    try:
        return ApiCommonResponseDTO(status=400, message="not supported yet").model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message=str(e)).model_dict()


async def rag_retrieve(token_checker: TokenChecker,
                       kb_id: str = Body(..., description="kb_id"),
                       query: str = Body(..., description="query"),
                       top_k: Optional[int] = Body(None, description="最终召回数量"),
                       fetch_k: Optional[int] = Body(None, description="初始召回数量"),
                       score_threshold: Optional[float] = Body(None, description="相似度阈值"),
                       reranker: bool = Body(False, description="是否启用重排序")):
    try:
        valid, normalized_query = query_processor.validate(query)
        if not valid:
            return ApiCommonResponseDTO(status=400, message=normalized_query).model_dict()
        record = get_kb_record(kb_id)
        metadata = read_metadata(record.get("kb_path"))
        abs_kb_path = get_kb_absolute_path(record.get("kb_path"))
        docs = await retrieval_pipeline.retrieve(
            query=normalized_query,
            kb_path=abs_kb_path,
            top_k=top_k,
            fetch_k=fetch_k,
            score_threshold=score_threshold,
            embedding_model=metadata.get("embedding_model"),
            business_type=metadata.get("business_type"),
            enable_reranker=reranker,
        )
        sources = context_builder.to_sources(docs)
        records = [{"segment": {"content": item.get("content"), "metadata": item.get("metadata")},
                    "score": item.get("score")} for item in sources]
        return ApiCommonResponseDTO(status=200, message="success", data={
            "knowledge_base_id": kb_id,
            "sources": sources,
            "records": records,
            "reranker": reranker,
        }).model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message=str(e)).model_dict()


def get_file_list(token_checker: TokenChecker, kb_id: str = Query(..., description="kb_id")):
    try:
        if not token_checker:
            return ApiCommonResponseDTO(message="用户未登录!", status=401).model_dict()
        record = get_kb_record(kb_id)
        metadata = read_metadata(record.get("kb_path"))
        db_files = get_file_list_from_db(kb_id) or []
        return ApiCommonResponseDTO(status=200, message="success", data={
            "documents": metadata.get("documents", []),
            "db_files": db_files,
        }).model_dict()
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message=str(e)).model_dict()
