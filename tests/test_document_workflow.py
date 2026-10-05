# -*- coding: utf-8 -*-
import asyncio
import json

import pytest

from src.server.ai.document_workflow_service import stream_document_analysis


CONTEXT = '[SOURCE 1]\nSOURCE_FILE: brief.md; SOURCE_ID: source-1\nCONTENT:\n项目：远山。负责人：张敏。交付：每月审计报告。验收：每条结论有引用。截止：2026-11-01。'
SOURCES = [{'source_id': 'source-1', 'filename': 'brief.md', 'excerpt': '项目：远山。', 'page': None, 'chunk_index': 0}]


def collect(inputs):
    async def run():
        return [event async for event in stream_document_analysis(inputs=inputs, user='1', sources=SOURCES)]
    return asyncio.run(run())


def test_graph_extracts_real_fields_and_blocks_unverified_evidence(monkeypatch):
    async def complete(system_prompt, messages, **kwargs):
        assert 'UNTRUSTED DOCUMENT' in messages[0]['content']
        return json.dumps({'document_type': 'client_brief', 'fields': [
            {'id': 'project_client', 'value': '远山', 'evidence': [{'source_id': 'source-1', 'quote': '项目：远山'}]},
            {'id': 'required_outputs', 'value': '每月审计报告', 'evidence': [{'source_id': 'source-1', 'quote': '交付：每月审计报告'}]},
            {'id': 'owner', 'value': '张敏', 'evidence': [{'source_id': 'source-1', 'quote': '负责人：张敏'}]},
            {'id': 'timeline', 'value': '2026-11-01', 'evidence': [{'source_id': 'invented-source', 'quote': '截止：2026-11-01'}]},
            {'id': 'acceptance_criteria', 'value': 'Unsupported value', 'evidence': [{'source_id': 'source-1', 'quote': 'invented quote'}]},
        ]}, ensure_ascii=False)
    monkeypatch.setattr('src.server.ai.document_workflow_service.llm_service.complete', complete)
    events = collect({'analysis_type': 'delivery_handoff', 'lang': 'zh', 'context': CONTEXT})
    assert [event['stage'] for event in events if event['event'] == 'status'] == ['identify', 'extract', 'validate', 'review']
    result = events[-1]['delivery_package']
    fields = {field['id']: field for field in result['fields']}
    assert fields['project_client']['value'] == '远山'
    assert fields['required_outputs']['value'] == '每月审计报告'
    assert fields['owner']['status'] == 'confirmed'
    assert fields['timeline']['status'] == 'review'
    assert fields['acceptance_criteria']['status'] == 'review'
    assert fields['primary_users']['value'] is None
    assert fields['primary_users']['source_ids'] == []
    assert result['handoff']['ready'] is False
    assert result['handoff']['mode'] == 'preview_only'


def test_graph_rejects_malformed_extraction(monkeypatch):
    async def complete(*args, **kwargs):
        return 'not JSON'
    monkeypatch.setattr('src.server.ai.document_workflow_service.llm_service.complete', complete)
    with pytest.raises(json.JSONDecodeError):
        collect({'analysis_type': 'delivery_handoff', 'lang': 'en', 'context': CONTEXT})


def test_graph_streams_answer_and_propagates_provider_failure(monkeypatch):
    async def stream(*args, **kwargs):
        yield '远山 [source-1]'
    monkeypatch.setattr('src.server.ai.document_workflow_service.llm_service.stream_complete', stream)
    events = collect({'analysis_type': 'free_question', 'lang': 'zh', 'question': '项目名称？', 'context': CONTEXT})
    assert events[-1]['answer'] == '远山 [source-1]'
    assert any(event['event'] == 'text' for event in events)
    async def fail(*args, **kwargs):
        raise RuntimeError('Provider unavailable')
        yield
    monkeypatch.setattr('src.server.ai.document_workflow_service.llm_service.stream_complete', fail)
    with pytest.raises(RuntimeError, match='Provider unavailable'):
        collect({'analysis_type': 'free_question', 'lang': 'en', 'context': CONTEXT})
