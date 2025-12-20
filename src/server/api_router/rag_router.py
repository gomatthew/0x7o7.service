# -*- coding: utf-8 -*-
from fastapi import APIRouter
from src.server.ai.rag.kb_service import create_kb, get_kb_list, delete_kb, upload_file_to_kb, upload_text_to_kb, \
    delete_file_to_kb, get_file_seg_list,get_file_progress

rag_router = APIRouter(prefix='/rag',tags=['rag'])
rag_router.post('/create_kb')(create_kb)
rag_router.get('/get_kb_list')(get_kb_list)
rag_router.post('/delete_kb')(delete_kb)
rag_router.post('/upload_file')(upload_file_to_kb)
rag_router.post('/delete_file')(delete_file_to_kb)
rag_router.get('/get_file_seg')(get_file_seg_list)
rag_router.get('/get_file_progress')(get_file_progress)
