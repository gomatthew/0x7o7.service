# -*- coding: utf-8 -*-
import asyncio
import io
import json
from datetime import datetime, timedelta

import httpx
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from starlette.datastructures import UploadFile

from src.server.service import ocr_service
from src.server.db.ai_models.conversation_model import ConversationModel
from src.server.db.ai_models.message_model import MessageModel
from src.server.db.repository.ai_repository import get_ocr_history_from_db


def test_ocr_requires_image_or_owned_conversation(monkeypatch):
    result = asyncio.run(ocr_service.ocr_chat('1', query='Hello', conversation_id=None, file=None, lang='en'))
    assert result['status'] == 400
    monkeypatch.setattr(ocr_service, 'get_ocr_history_from_db', lambda conversation_id, user_id: [])
    result = asyncio.run(ocr_service.ocr_chat('1', query='Follow-up', conversation_id='other-user', file=None, lang='en'))
    assert result['status'] == 404


def test_ocr_history_retains_initial_image_and_enforces_owner():
    engine = create_engine('sqlite://')
    ConversationModel.__table__.create(engine)
    MessageModel.__table__.create(engine)
    with Session(engine) as session:
        session.add(ConversationModel(conversation_id='ocr-owned', user_id='1'))
        for index in range(9):
            session.add(MessageModel(message_id=f'm-{index}', conversation_id='ocr-owned', user_id='1',
                                     user_query=f'Question {index}', ai_response=f'Answer {index}',
                                     create_time=datetime(2026, 10, 5) + timedelta(seconds=index),
                                     meta_data={'biz_type': 'ocr', 'ocr_context': 'Invoice TEST-2026' if index == 0 else None}))
        session.commit()
        read_history = get_ocr_history_from_db.__wrapped__
        assert read_history(session, 'ocr-owned', '2') == []
        history = read_history(session, 'ocr-owned', '1')
        assert history[0]['content'] == 'Invoice TEST-2026'
        assert history[-1]['content'] == 'Answer 8'
        assert len(history) == 14
        session.query(ConversationModel).filter_by(conversation_id='ocr-owned').update({'status': '0'})
        session.commit()
        assert read_history(session, 'ocr-owned', '1') == []


def test_ocr_preserves_user_question_language_and_persists_before_done(monkeypatch):
    captured = {}
    async def auth(*args):
        return 'test-token'
    class Client:
        def __init__(self, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def post(self, *args, **kwargs):
            return httpx.Response(200, json={'words_result': [{'words': 'Invoice total: 88'}]})
    async def stream(system_prompt, messages, **kwargs):
        captured['system'] = system_prompt
        captured['messages'] = messages
        yield '总额为 88'
    monkeypatch.setattr(ocr_service, 'ocr_auth', auth)
    monkeypatch.setattr(ocr_service.httpx, 'AsyncClient', Client)
    monkeypatch.setattr(ocr_service, 'is_admin_user', lambda user_id: True)
    monkeypatch.setattr(ocr_service, 'add_file_to_db', lambda dto: None)
    monkeypatch.setattr(ocr_service.llm_service, 'stream_complete', stream)
    monkeypatch.setattr(ocr_service, 'add_conversation_to_db', lambda **kwargs: captured.update(conversation=kwargs))
    monkeypatch.setattr(ocr_service, 'add_message_to_db', lambda **kwargs: captured.update(message=kwargs))
    async def run():
        response = await ocr_service.ocr_chat('1', query='只返回总额', conversation_id=None, lang='zh',
                                              file=UploadFile(filename='invoice.png', file=io.BytesIO(b'image')))
        events = []
        async for event in response.body_iterator:
            if event['event'] == 'done':
                assert captured['message']['ai_response'] == '总额为 88'
            events.append(event)
        return events
    events = asyncio.run(run())
    assert 'Chinese' in captured['system']
    assert '只返回总额' in captured['messages'][0]['content']
    assert 'Invoice total: 88' in captured['messages'][0]['content']
    assert captured['message']['meta_data']['biz_type'] == 'ocr'
    assert json.loads(events[-1]['data'])['conversation_id'].startswith('ocr_')


def test_ocr_stream_failure_is_not_reported_as_success(monkeypatch):
    async def stream(*args, **kwargs):
        raise RuntimeError('Provider failed')
        yield
    monkeypatch.setattr(ocr_service.llm_service, 'stream_complete', stream)
    async def run():
        return [event async for event in ocr_service.stream_ocr_result([], 'query', 'ocr-1', '1', 'en')]
    events = asyncio.run(run())
    assert events[-1]['event'] == 'error'
    assert not any(event['event'] == 'done' for event in events)
