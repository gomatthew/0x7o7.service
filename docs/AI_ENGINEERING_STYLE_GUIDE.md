# AI Engineering Style Guide

> An internal handbook reverse-engineered from the actual code in `0x7o7.service`.
> The goal is for AI assistants and human contributors to write new code that is
> **indistinguishable in style and philosophy** from what already exists.
>
> This is not generic Python advice. Every rule here is grounded in observations
> from this repo. When in doubt, **match the existing code**, not external best
> practices.

---

## 0. TL;DR — The Mental Model

This codebase is a **single-developer pragmatic FastAPI monolith**. It is built to
ship features fast, integrate quickly with third-party AI services (Dify, Baidu
OCR, MinIO, SiliconFlow, Ollama), and keep the layout flat enough that one
person can reason about everything at once.

The author's working principle is roughly:

- **Flat over deep.** Keep folders shallow, modules small, files focused.
- **Procedural over OOP.** Most "services" are top-level `def` functions, not
  classes. Classes are reserved for things that genuinely hold state
  (`MinioInstance`, `BcryptLib`, `TokenHandleJWT`) and are usually exposed as
  module-level singletons (`bp`, `dt`, `ep`, `redis_store`, `token_handler`).
- **Routers are wiring, not logic.** A router file is typically 5–15 lines.
- **Settings are a class hierarchy with hardcoded values.** No `.env`, no Pydantic
  Settings, no envvar fallbacks. `BaseSetting` → `DevSetting` / `ProdSetting` /
  `UnitTestSetting`.
- **MVP-oriented.** Stub endpoints (`comment_service.add_comment`, several
  `kb_service` functions) return success with empty data and exist purely so the
  frontend has something to call. They are not technical debt — they are
  scaffolding that will be filled in when the feature is actually needed.
- **Iteration speed > theoretical purity.** The repo contains commented-out
  legacy code (`ai_service.py`), an unused YOLO playground script, and minor
  inconsistencies. These are intentional artifacts of fast iteration, not bugs
  to fix unless the user asks.

If you only remember one thing: **write the simplest, most procedural,
fewest-files solution that the existing patterns already use.** Do not
introduce dependency injection, ABCs, factories, repository interfaces, or
any other "enterprise" pattern that is not already present.

---

## 1. Project Layout

```
0x7o7.service/
├── main.py                  # entry point — uvicorn.run(app)
├── requirements.txt         # pinned, plain pip (no poetry/uv/pyproject.toml)
├── start.sh / shutdown.sh   # raw shell scripts, not a CLI
├── deploy/                  # gunicorn_conf.py, nginx.conf, systemd file
├── log/                     # runtime log output (loguru rotates here)
├── scripts/                 # one-off scripts; Chinese filenames are fine
└── src/
    ├── __init__.py
    ├── configs/             # settings.py + log_config.py + __init__ helper
    ├── enum/                # all StrEnums in one file (emuns.py — note typo, keep it)
    └── server/
        ├── utils.py             # cross-cutting helpers (token_identify, http_stream_request)
        ├── api_router/          # one file per resource: *_router.py
        ├── service/             # one file per resource: *_service.py
        ├── dto/                 # Pydantic DTOs
        ├── libs/                # third-party wrappers (bcrypt, jwt, redis, smtp, arrow)
        ├── db/
        │   ├── base.py          # engine, SessionLocal, declarative_base
        │   ├── session.py       # session_scope() + with_session decorator
        │   ├── models/          # business-domain SQLAlchemy models
        │   ├── ai_models/       # AI-domain SQLAlchemy models (separate folder!)
        │   └── repository/      # raw DB access functions
        └── ai/
            ├── ai_service.py
            ├── chat_history_service.py
            ├── llm_utils.py
            ├── agent/
            │   ├── agent_factory.py     # custom Qwen agent
            │   ├── agents_registry.py
            │   └── tools/tools_registry.py
            ├── callback_handler/        # LangChain callback subclasses
            ├── memory/memory.py
            ├── prompt/prompt.py
            └── rag/kb_service.py
```

### Layout rules

- **One file per resource per layer.** A new "order" feature gets `order_router.py`,
  `order_service.py`, `order_model.py` — never `routers/orders/create.py` or
  similar deeply-nested patterns.
- **Suffix files with their layer name.** `*_router.py`, `*_service.py`,
  `*_model.py`, `*_lib.py`, `*_dto.py`, `*_repository.py`. This is rigid.
- **`ai/` is a parallel sub-app.** It has its own `models/` (called `ai_models/`),
  its own services, its own callback handlers. Anything LLM- or RAG-related
  goes there, not in the regular `service/` folder.
- **`libs/` is for stateless/util third-party wrappers.** A class with `@staticmethod`
  methods plus a module-level singleton (`bp = BcryptLib()`). Never a heavy
  abstraction layer.
- **Do not create an `interfaces/`, `abstract/`, `core/`, or `domain/` folder.**
  None exist and none are wanted.

---

## 2. Coding Style

### 2.1 File header

**Every Python file starts with `# -*- coding: utf-8 -*-`.** Always include it
on new files, even though Python 3 doesn't need it. It is a marker of "this
file belongs to the project." Some files use `# -*- coding: UTF-8 -*-` (capital);
either is fine — match neighboring files.

### 2.2 Naming conventions

| Thing                       | Convention                                                      | Example                                   |
| --------------------------- | --------------------------------------------------------------- | ----------------------------------------- |
| Module                      | `snake_case` + layer suffix                                     | `auth_service.py`, `user_dto.py`          |
| Function                    | `snake_case`, verb-first                                        | `user_login`, `add_file_to_db`            |
| Class                       | `PascalCase`, often suffixed `Lib`, `DTO`, `Model`, `Handler`   | `BcryptLib`, `UserDto`, `UserModel`       |
| Module-level singleton      | 2–3 letter lowercase alias of the class                         | `bp`, `dt`, `ep`, `setting`               |
| Pydantic DTO                | `PascalCase` ending in `Dto` or `DTO` (mixed — both occur)      | `UserDto`, `ApiCommonResponseDTO`         |
| SQLAlchemy model            | `PascalCase` ending in `Model`                                  | `UserModel`, `ConversationModel`          |
| Enum class                  | `PascalCase` ending in `Enum`, member values are strings        | `RecordStatusEnum.ACTIVATE = '1'`         |
| Constants in settings       | `SCREAMING_SNAKE_CASE`                                          | `TOKEN_EXPIRE_HOURS`, `OCR_FILE_LIMIT`    |
| Repository function         | `<verb>_<noun>_<from\|to>_db`                                   | `add_user`, `get_user_info_from_db`, `add_message_to_db` |
| Router prefix               | resource name, lowercase                                        | `/auth`, `/user`, `/ai`, `/rag`, `/service` |
| API path                    | `/<verb>_<noun>` or `/<verb>`                                   | `/add`, `/get_info`, `/upload_file`       |

**Do not** use camelCase variables. **Do not** use type-stutter prefixes
(`m_`, `s_`). **Do** use `_lib` suffix for stateless wrappers.

A note on the `Dto`/`DTO` casing inconsistency: `UserDto` (model objects) vs.
`ApiCommonResponseDTO` (response wrappers) co-exist. This is not worth
cleaning up — match the file you are editing.

### 2.3 Function size and shape

Functions are **medium-sized and procedural**. They commonly do all of:

1. validate / lookup / extract,
2. mutate state or call third-party,
3. return an `ApiCommonResponseDTO`,

inside a single function body, often with a top-level `try/except BaseException`.

Examples:

- `user_register` — ~20 lines: rate-limit check → duplicate check → hash →
  insert → fire email → return DTO.
- `ocr_chat` — ~40 lines: quota → encode → POST → stream → log → return.
- `chat_dify` — ~40 lines: retrieve RAG → build payload → stream SSE.

**Do not** split this into 5 helper functions. The existing style is to keep the
whole flow visible in one place. Helper extraction happens only when something
is genuinely reused across multiple services (e.g. `http_stream_request` in
`utils.py`, `rag_retrieve` in `kb_service.py`).

### 2.4 Imports

Order is conventional but loose:

```python
# -*- coding: utf-8 -*-
import os                           # stdlib
import json
import datetime
from typing import Optional, Annotated, Any

import bcrypt                       # third-party
import httpx
import requests
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from src.configs import logger, get_setting       # first-party — always `from src...`
from src.server.libs import token_handler, dt
from src.server.db.repository import add_user, get_user_info_from_db
from src.server.dto.response_dto import ApiCommonResponseDTO
```

- Always use **absolute imports rooted at `src.`**. No relative imports
  (`from ..libs import ...`) anywhere in the codebase.
- A blank line separates stdlib, third-party, and first-party — usually.
  Don't be religious; some files skip it.
- `from src.configs import logger, get_setting` is the canonical way to get
  the logger and settings. Do not call `loguru.logger` directly in business code.
- `setting = get_setting()` (or `settings = get_setting()` — both occur) at
  the **module top level** is the canonical way to read configuration.

### 2.5 Typing

Typing is **light and pragmatic**, not strict.

- Type hints are used **where they help readability or FastAPI**: route
  parameters, Pydantic fields, repository return types when a DTO is returned.
- Internal helpers are often **untyped or partially typed**:
  ```python
  def http_stream_request(url, http_method, headers=dict(), data=dict(), meta=dict()):
  ```
  Note: `dict()` as a default is used here. It is technically a mutable default
  but the function does not mutate it — match this style if you see it. Don't
  go on a crusade to fix it.
- `Optional[X]` is preferred over `X | None` in DTOs, but `str | int` and
  `str | None` both appear. Either is fine.
- `Any` is used liberally for fields that hold arbitrary JSON
  (`data: Any = Field(default={})`, `meta_data: Any = None`).
- Pydantic v2 syntax: `model_config = {"from_attributes": True}` (not the
  legacy `class Config` for `from_attributes`, although `class Config` *is*
  still used for `json_schema_extra`).

### 2.6 Comments

The repo has **almost no inline comments**. The few that exist are:

- **Chinese `comment=`** strings on SQLAlchemy columns:
  ```python
  status = Column(Integer, nullable=False, comment="用户状态 -1-无效 1-有效 0-未激活")
  ```
- **Chinese `description=`** strings on Pydantic fields:
  ```python
  data: Any = Field(default={}, description="返回数据")
  ```
- **Chinese `tags=`** and `summary=` on FastAPI routers:
  ```python
  APIRouter(prefix="/auth", tags=["用户登录注册服务"])
  service_router.post('/upload_file', summary='上传文件')(upload_file)
  ```
- Occasional `# todo:` or commented-out blocks of legacy code (kept as a
  reference, not deleted).

**Rules for new code:**

- Do not write English explanatory comments above functions.
- Do **write Chinese `comment=` / `description=` / `tags=` / `summary=`** on
  every new column, DTO field, and router. This is how the API and DB schema
  are self-documenting.
- Keep docstrings empty or omit them. Tools that auto-register (e.g.
  `regist_tool` in `tools_registry.py`) read the docstring as a tool
  description — those are the only docstrings you'll find.

### 2.7 Logging

- Always import logger as `from src.configs import logger`.
- Use `logger.info`, `logger.error`, `logger.debug`. No structured
  logging, no extra fields, no JSON.
- The canonical error pattern is:
  ```python
  except BaseException as e:
      logger.error(e)
      logger.error(traceback.format_exc())
  ```
  Yes, `BaseException` (not `Exception`). Yes, `traceback.format_exc()` is
  logged separately on its own line. Match this exactly.
- Lifecycle events use bracketed uppercase tags: `logger.info('[START SERVER]')`.

### 2.8 Error handling

The dominant pattern is:

```python
def some_service(...):
    try:
        # do everything
        return ApiCommonResponseDTO(status=200, message='success', data=...)
    except BaseException as e:
        logger.error(e)
        logger.error(traceback.format_exc())
        return ApiCommonResponseDTO(status=500, message=str(e))
```

- **Catch `BaseException`**, not `Exception`. This is unusual in
  general Python but consistent here.
- **Never raise HTTPException for business errors.** Return an
  `ApiCommonResponseDTO` with a non-200 `status` field instead. The HTTP
  response is always 200 OK; the *application* status is in the body.
- Validation/permission failures use `status=400`, `status=401`, `status=403`,
  `status=429` etc. inside a 200 HTTP response.
- Decorator-style transactional helpers (`with_session`, `session_scope`) wrap
  DB code:
  ```python
  @with_session
  def add_user(session, ...):
      ...
  ```
  The decorator injects `session` as the first arg, commits on success,
  rolls back on any `BaseException`. **All repository functions use this.**

### 2.9 Async style

Async is used **only where it provides real value** — primarily for streaming
endpoints (`ocr_chat`, `chat_dify`) and routes that need to fire background
tasks via `BackgroundTasks`.

- Sync `def` is the default for service functions, repository functions,
  and most routes.
- `async def` shows up for: SSE/stream handlers, `user_register` (because it
  needs `await` for rate-limit), and a few stub `chat_history` functions.
- **Do not async-ify code "because FastAPI is async."** If the code does not
  await anything, keep it sync `def` — FastAPI will run it in a threadpool.
- For streaming third-party APIs, use `httpx.stream` (not `aiohttp`) and
  yield from a generator. See `http_stream_request` and `chat_dify`.

### 2.10 API response conventions

There are exactly two response shapes:

```python
# response_dto.py
class ApiCommonResponseDTO(BaseResponseDTO):
    status: int = 200
    message: str = 'success'
    data: Any = Field(default={}, description="返回数据")

class OpenAIOutputDTO(BaseResponseDTO):
    content: str
    message_id: str
    tool: Any
    llm_status: str | int
```

- **Every standard endpoint returns `ApiCommonResponseDTO`.** No exceptions.
  Even success-with-no-payload returns `data={}`.
- **Streaming/SSE endpoints** return `EventSourceResponse` (from `sse_starlette`
  / starlette equivalent) and yield `OpenAIOutputDTO` JSON dumps.
- The HTTP status is **almost always 200**. Application-level status is in the
  body.
- Common application status codes used: `200` (ok), `400` (bad input),
  `401` (auth failed), `403` (forbidden), `429` (rate-limited), `500`
  (server error). Match these — don't invent new codes.

---

## 3. Architectural Preferences

### 3.1 Layering

```
api_router/   →   service/   →   db/repository/   →   SQLAlchemy models
                       ↓
                    libs/  (bcrypt, jwt, redis, email, smtp, etc.)
                       ↓
                    third-party APIs (Dify, Baidu OCR, MinIO, SMTP)
```

- **Routers wire functions to URLs.** They are not a place for logic, parameter
  validation (Pydantic does that), or response shaping.
- **Services own the business flow.** They take HTTP-shaped inputs (FastAPI
  parses them), call repositories and libs, and return `ApiCommonResponseDTO`.
- **Repositories own raw DB access.** They are decorated with `@with_session`,
  receive `session` as the first arg, and return DTOs (not ORM objects, when
  possible).
- **Libs wrap third parties or stdlib.** They never know about the database
  or the HTTP layer.

### 3.2 Routers are pure wiring

The canonical router file is **5–15 lines** of `router.<verb>(path)(handler)`
calls. Compare:

```python
# auth_router.py — the entire file
from fastapi import APIRouter
from src.server.service import user_login, reset_password

auth_router = APIRouter(prefix="/auth", tags=["用户登录注册服务"])
auth_router.post('/login')(user_login)
auth_router.post('/reset_password')(reset_password)
```

Notice the **call form**: `router.post(path)(handler)`, not the decorator
form `@router.post(path)` on the handler. This is deliberate — handlers live in
`service/` and are imported and bound here. This keeps services importable
in any context (including tests, scripts) without dragging in FastAPI metadata.

**Auth is router-wide, not per-endpoint:**

```python
ai_router = APIRouter(prefix="/ai", tags=["AI"], dependencies=[Depends(token_identify)])
```

When all endpoints in a router need auth, put it on the `APIRouter`. Per-endpoint
`dependencies=[Depends(token_identify)]` is only used in `user_router.py` because
`/user/add` (registration) is public.

### 3.3 Service functions

A service function is the **unit of business logic**. Conventions:

- Top-level `def` (or `async def` for streaming/awaiting).
- Takes either Pydantic DTOs or primitive args. FastAPI does the binding.
- Always returns `ApiCommonResponseDTO` (or a streaming response).
- May receive `response: Response` if it needs to set/clear cookies.
- May receive `background_tasks: BackgroundTasks` to fire-and-forget work
  (currently used for sending emails on register/login).
- Read settings via the module-level `setting = get_setting()`.
- Read the current user via `user_id: TokenChecker` (an `Annotated` dependency
  that lives in `utils.py`).

**Do not** turn a service into a class. Even when state is involved (e.g.
`MinioInstance`), the *service entry point* (`upload_file`, `download_file`)
is still a top-level function that uses the singleton.

### 3.4 Repository pattern

Repositories are **flat collections of functions**, not classes:

```python
# user_repository.py
@with_session
def add_user(session, user: AddUserDto):
    new_user = UserModel(**user.model_dump())
    session.add(new_user)
    session.flush()
    return new_user.id

@with_session
def get_user_info_from_db(session, user_id):
    user = session.query(UserModel).filter(UserModel.id == user_id, ...).first()
    return UserInfoDto.model_validate(user) if user else None
```

- Always `@with_session`, always `session` as the first param.
- Take primitive IDs or DTOs as input.
- Return DTOs (or primitives), not ORM objects, so the session can close
  cleanly.
- Use SQLAlchemy 2.0 `session.query(...)` style. (The codebase has not migrated
  to the 2.0 `select()` API and we are not in a hurry to do so.)
- Repository functions are exported from `db/repository/__init__.py` so callers
  do `from src.server.db.repository import add_user`.

### 3.5 Models

Two parallel hierarchies under `db/`:

- `db/models/` — business domain (User, Customer, Tenant, Order, Good, File).
- `db/ai_models/` — AI domain (Conversation, Message, KnowledgeBase).

Each has its own `base.py` declaring a `BaseModel(Base)` abstract that adds
`id`, `created_user`, `created_time`. Note these two `BaseModel`s are
**separate but nearly identical** — that's intentional (decoupling the
AI subsystem). Don't merge them.

Optimistic locking is added via `__mapper_args__ = {'version_id_col': version}`
on entities that need it (User, Customer, Tenant). Add it when the row will
be updated by multiple actors; skip it for append-only/log-style tables.

Column conventions:

- Always set `nullable=`, even when default.
- Always add Chinese `comment=` for non-obvious columns.
- `status` columns use `RecordStatusEnum` values stored as int/string `'1'`/`'0'`.
  Default to `RecordStatusEnum.ACTIVATE`.
- Timestamps use `default=func.current_timestamp()`. (Note: `func.now()`
  invoked-at-class-time is a known footgun — use `func.current_timestamp()`
  per the existing pattern.)

### 3.6 DTOs

Three kinds of Pydantic models:

1. **Entity DTOs** (`UserDto`, `UserInfoDto`) — used to ferry rows out of
   repositories. Set `model_config = {"from_attributes": True}`.
2. **Action DTOs** (`AddUserDto`, `UpdateUserDto`) — input shapes for service
   functions, especially for partial updates.
3. **Response DTOs** (`ApiCommonResponseDTO`, `OpenAIOutputDTO`) — the only two
   things ever sent to clients.

Use `Field(..., description="...")` (Chinese description) on user-facing fields.
For private internal DTOs, plain `Optional[str] = None` is enough.

### 3.7 Settings

`src/configs/settings.py` is a **plain class hierarchy**, not Pydantic Settings,
not envvars:

```python
class BaseSetting:
    APP_HOST = '0.0.0.0'
    APP_PORT = 8001
    SECRET_KEY = '...'
    REDIS_URL = "redis://127.0.0.1:6379/0"
    LLM_SETTING = [{...}, {...}]

class DevSetting(BaseSetting):
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://...service_data_dev...'

class ProdSetting(BaseSetting):
    SQLALCHEMY_DATABASE_URI = 'mysql+pymysql://...service_data_prod...'
```

`get_setting()` switches on `run_mode` (currently hardcoded to `'dev'`).
Secrets are committed in cleartext. **This is intentional for the current
phase of the project. Do not "fix" it by introducing `.env`, `pydantic-settings`,
or `os.getenv` — that's out of scope unless the user explicitly asks.**

When you need a new config value:

1. Add it as a `SCREAMING_SNAKE_CASE` attribute on `BaseSetting`.
2. Override in `DevSetting` / `ProdSetting` only if it differs per-env.
3. Import as `setting = get_setting()` and use `setting.MY_VALUE`.

### 3.8 Auth / sessions

- JWT in an `HttpOnly` cookie called `access_token`. Issued by
  `TokenHandleJWT.generate_token`, verified by `TokenHandleJWT.verify_token`.
- Cookie is set on login via `response.set_cookie("access_token", token, ...)`.
- The auth dependency is `token_identify` in `src/server/utils.py`. It returns
  the user id (as a string) or `None`. Combined into `TokenChecker = Annotated[Any, Depends(token_identify)]`.
- Public endpoints don't add the dependency. Whole-router protection: put
  `dependencies=[Depends(token_identify)]` on the `APIRouter`.
- Tokens are also persisted to `user.token` in the DB and verified on each
  request, so password reset / logout invalidates outstanding tokens.

### 3.9 Streaming, SSE, AI

- **SSE responses use `EventSourceResponse`.** The pattern is:
  ```python
  return EventSourceResponse(http_stream_request(url, "POST", headers, data))
  ```
- The streaming generator parses Dify's `data: {...}` SSE lines, dispatches on
  `event` via `match`/`case`, and yields the same line back to the client. This
  makes the backend a thin proxy — most "AI logic" lives in Dify workflows.
- `chat_dify` is the canonical AI endpoint. It (a) does a RAG retrieve via
  `rag_retrieve`, (b) injects retrieved chunks into the user query, (c)
  forwards to Dify chat, (d) streams the response.
- The LangChain agent / RAG infrastructure under `src/server/ai/agent/`,
  `callback_handler/`, `memory/` is **partially active**. Some flows go through
  Dify directly (`chat_dify`); legacy LangChain agent code is commented in
  `ai_service.py`. Don't delete it. Don't activate it without being asked.
- When integrating a new AI feature: **prefer adding it to the Dify workflow
  and creating a thin proxy endpoint here** over building a new LangChain
  pipeline locally.

---

## 4. Engineering Philosophy

### 4.1 What the author values

- **Shipping.** Stub endpoints exist so the frontend has something to call.
  Routers expose every planned URL even if the handler is `pass`.
- **Locality.** A feature lives in one router file, one service file, one
  model file. You should never need a tour of 12 directories to understand
  one endpoint.
- **Sane defaults over configurability.** `DEFAULT_LLM`, `DEFAULT_TEMPERATURE`,
  `DEFAULT_STREAM` in settings — most call sites just take the default.
- **Singletons.** Module-level instances (`bp`, `dt`, `ep`, `redis_store`,
  `setting`, `logger`, `token_handler`) are how dependencies are "injected."
  No DI container, no `Depends(get_db)` (sessions come from the `@with_session`
  decorator).
- **Procedural code.** When in doubt, write a `def`, not a class.
- **Pinned dependencies.** `requirements.txt` has every version pinned to an
  exact patch level. Match this when adding a dependency.

### 4.2 What the author avoids

- **Over-engineering.** No factories, no abstract base classes for
  business logic, no strategy pattern, no command bus, no CQRS.
- **Java-style boilerplate.** No interface + impl pairs, no
  `UserServiceImpl`, no getters/setters.
- **Excessive abstraction.** A function is preferred over a class, a class is
  preferred over a metaclass, a flat module is preferred over sub-packages.
- **Premature optimization.** No caching layer beyond Redis, no async-everywhere,
  no connection pooling beyond SQLAlchemy's default (`pool_recycle=1800`).
- **Enterprise patterns.** No DDD, no hexagonal architecture, no "ports and
  adapters." There is exactly one adapter (`libs/`) and it just wraps SDKs.
- **Heavy validation.** Pydantic does input validation. Beyond that, code
  trusts itself.

### 4.3 MVP-orientation: stubs are fine

These are all in the codebase and all intentional:

- `comment_service.add_comment`: just `pass`.
- `kb_service.upload_text_to_kb`: returns `status=400, message='not supported yet'`.
- `kb_service.delete_file_to_kb`, `get_file_seg_list`, `get_kb_file_list`:
  return `status=200, data={}`.
- `goods_service`: returns hardcoded sample data.

**When asked to add a new feature, it is acceptable and often correct to
ship a stub for everything except the one critical path.** The existing code
embraces this.

### 4.4 What "good code" looks like here

- Short. A 30-line service function is normal; 100 is on the long side.
- Procedural. Top-down read like a script.
- Boring. Uses the same patterns as its neighbors.
- Self-routed. Adding a feature means adding files, not editing many.

---

## 5. Backend Style — Detailed

### 5.1 FastAPI app construction

`src/server/__init__.py` defines `create_app()` and `create_tables()`.
`main.py` calls `create_app()` and runs uvicorn.

- CORS is wide-open in dev (`allow_credentials=True, allow_methods=["*"]`).
- One redirect from `/` to `/docs`.
- All routers are included in `create_app`. **When you add a new router,
  remember to import it in `api_router/__init__.py` and `app.include_router(...)` it.**
- `create_tables()` calls `Base.metadata.create_all(bind=engine)`. There is
  **no Alembic, no migration tool**. Schema changes are applied by adding
  the column and letting `create_all` add it on startup. (Live altering of
  existing columns must be done by hand.) Don't introduce Alembic without
  being asked.

### 5.2 Database access

```python
from src.server.db.session import with_session

@with_session
def update_user_to_db(session, user_id, update_dto: UpdateUserDto):
    user = session.query(UserModel).filter(
        UserModel.id == user_id,
        UserModel.status == RecordStatusEnum.ACTIVATE
    ).first()
    if not user:
        return None
    for k, v in update_dto.model_dump(exclude_none=True).items():
        setattr(user, k, v)
    session.flush()
    return user.id
```

Rules:

- Always `@with_session`, always commit/rollback handled by the decorator.
- Always filter `status == RecordStatusEnum.ACTIVATE` for "active record" reads —
  rows are soft-deleted, not removed.
- Use `model_dump(exclude_none=True)` for partial updates.
- Return DTOs or primitives, never live ORM objects.

### 5.3 Pydantic DTO patterns

```python
class UserDto(BaseModel):
    id: int = Field(..., description="id")
    user_nick_name: Optional[str] = Field(None, max_length=32, description="用户昵称")
    phone_number: Optional[str] = Field(None, max_length=11, description="手机号")
    password: str = Field(..., description="密码")
    mail: Optional[str] = Field(None, description="邮箱")
    status: Optional[int] = Field(1, description="用户状态 -1-无效 1-有效 0-未激活")
    model_config = {"from_attributes": True}
```

- Required fields: `Field(..., description="...")`.
- Optional fields: `Optional[X] = Field(None, ...)`.
- Add `max_length` matching the SQLAlchemy column length.
- Chinese description for everything user-facing.
- `model_config = {"from_attributes": True}` for DTOs that are loaded from ORM rows.

### 5.4 Streaming pattern

```python
def chat_dify(query: str, conversation_id: str, user_id: TokenChecker):
    # 1. RAG retrieve
    rag_result = rag_retrieve(kb_id, query)
    # 2. Build payload with retrieved context prepended to query
    payload = {"inputs": {}, "query": ..., "user": user_id, ...}
    # 3. Forward to Dify SSE
    headers = {"Authorization": f"Bearer {setting.DIFY_CHAT_SECRET_KEY}", ...}
    return EventSourceResponse(
        http_stream_request(urljoin(setting.DIFY_SERVER_URL, "chat-messages"),
                            "POST", headers=headers, data=payload)
    )
```

When adding a new streaming endpoint:

1. Build a request payload.
2. Use `httpx.stream` inside a generator function in `utils.py` (or extend the
   existing `http_stream_request`).
3. Wrap with `EventSourceResponse`.
4. Persist conversation/message to DB **inside the streaming callback**
   (on the `workflow_finished` event), not before — the response only counts
   when it actually completes.

### 5.5 WebSockets

There are no WebSocket endpoints in the codebase yet. If asked to add one:

- Match the SSE convention: thin proxy, persist on completion, return
  `OpenAIOutputDTO`-shaped messages.
- Don't introduce a connection registry or pub/sub layer until two endpoints
  actually need it.

### 5.6 Background tasks

```python
def user_login(login_dto: UserLoginDto, response: Response,
               background_tasks: BackgroundTasks):
    ...
    background_tasks.add_task(send_mail, "...", user.mail, "登录提醒")
    return ApiCommonResponseDTO(status=200, ...)
```

Use FastAPI's `BackgroundTasks` for fire-and-forget side effects (emails,
analytics events). Don't reach for Celery/RQ/Arq — they aren't in the project.

### 5.7 Rate limiting

The pattern is in `redis_lib.py`:

```python
def register_rate_limit(request: Request, email):
    block_key = f"register:block:{request.client.host}:{email}"
    request_count = redis_store.incr(block_key)
    redis_store.expire(block_key, settings.REDIS_BLOCK_TIME)
    return request_count > settings.REDIS_REQUEST_REQUEST_LIMIT
```

When you need to rate-limit a new endpoint, write a similar function next to
`register_rate_limit` and call it explicitly inside the service function.
Don't reach for `slowapi` or middleware — match this style.

---

## 6. AI Workflow Integration Style

The AI subsystem is split between **direct Dify proxying** (the active path)
and **a custom LangChain agent stack** (mostly dormant, kept for reference).

### 6.1 Direct Dify proxying (the main pattern)

- `chat_dify` (in `ai_service.py`) and `ocr_chat` (in `ocr_service.py`) both
  follow the pattern: build payload → forward to a third-party SSE endpoint →
  stream tokens through.
- The backend is intentionally **not where prompts live**. Prompts live in
  Dify; the backend supplies inputs and persists outputs.

### 6.2 Custom Qwen agent (LangChain)

`agent_factory.py` implements a custom prompt template, output parser, and
non-streaming planner specifically for Qwen models. Notes:

- Qwen does not support tool-calling-with-streaming; the patch replaces
  `RunnableAgent.plan` with `.invoke`-based versions.
- Tools register themselves with `@regist_tool`, which wraps LangChain's
  `@tool` and adds the tool to a global `_TOOLS_REGISTRY`. This is
  inspired by Chatchat-style registries.
- Wrap any tool return with `BaseToolOutput(...)` so it has both a
  string form (for the LLM) and a structured form (for downstream).

If you must add a new local LangChain agent flow (not via Dify):

1. Register tools with `@regist_tool` in `tools_registry.py`.
2. Use `agents_registry()` to construct the executor.
3. Use `AgentExecutorAsyncIteratorCallbackHandler` for SSE streaming.
4. Persist messages via `update_message` on `on_llm_end`.

### 6.3 RAG

- The KB is hosted in Dify; `kb_service.py` only mirrors metadata in our DB.
- `rag_retrieve` does hybrid search with reranking, `top_k=1`, score threshold
  enabled. These defaults are deliberate — don't tune them without being asked.
- KB list reads come from **our DB**, not Dify. KB delete is a soft-delete
  in **our DB**, not Dify. This is intentional: Dify is a content store, we
  own the user-facing catalog.

---

## 7. Forbidden / Anti-Patterns

Patterns that the existing code intentionally avoids. Do **not** introduce
them in new code unless the user explicitly asks.

### 7.1 Architectural anti-patterns

- ❌ **Repository / service interfaces.** No `IUserRepository`, `UserService(IUserService)`.
- ❌ **Dependency injection containers** (no `dependency_injector`, no
  hand-rolled IoC). Singletons + module-level imports are how it's done.
- ❌ **CQRS, mediator, event bus.** Not present, not wanted.
- ❌ **Hexagonal / DDD layout** (no `application/`, `domain/`, `infrastructure/`).
- ❌ **Pydantic Settings / dotenv.** Settings are class attributes.
- ❌ **Alembic / migration tool.** Schema is created with `create_all` on boot.
- ❌ **Async-everywhere.** Sync `def` is the default.
- ❌ **Inheritance hierarchies for business logic.** OK for SQLAlchemy `BaseModel`;
  not OK for services.

### 7.2 Code anti-patterns

- ❌ **HTTPException for business errors.** Return `ApiCommonResponseDTO(status=4xx, ...)` instead.
- ❌ **Raising errors out of services.** Catch `BaseException`, log, return error DTO.
- ❌ **`@router.post("/x")` on the handler.** Bind in the router file:
  `router.post("/x")(handler)`.
- ❌ **Raw `print`.** Use `logger.info` / `logger.error`.
  *(There are 1–2 stray `print(e)` in `token_lib.py`. Don't add more.)*
- ❌ **English docstrings explaining what a function does.** Use a Chinese
  `description=`/`comment=`/`summary=` instead.
- ❌ **Magic helpers folder named `core/`, `utils/` (plural), `common/`.**
  We have `utils.py` (singular, top-level), `libs/` (third-party wrappers),
  `configs/` (settings). Don't add another.
- ❌ **Splitting a 40-line service function into 6 helpers.** Keep it linear.
- ❌ **Generic `Exception` swallowing without logging.** Always
  `logger.error(e); logger.error(traceback.format_exc())`.
- ❌ **New SQL libraries.** Project uses SQLAlchemy + PyMySQL + raw `session.query`. No SQLModel, no Tortoise, no Peewee, no asyncpg.
- ❌ **New auth libraries.** No `fastapi-users`, no `authlib`, no OAuth2 password flow. Bcrypt + PyJWT + cookie is it.
- ❌ **Type-checking strictness.** Don't add `mypy.ini`, don't add `from __future__ import annotations`, don't decorate everything with `@beartype`.

### 7.3 Project-management anti-patterns

- ❌ **Adding `pyproject.toml` / poetry / uv** without being asked. Stay on
  `requirements.txt`.
- ❌ **Adding a test framework** without being asked. There are no tests yet;
  one is not blocking shipping.
- ❌ **Adding pre-commit hooks, ruff, black, isort** without being asked.
- ❌ **Cleaning up minor inconsistencies as a side-effect of another change.**
  (Examples: `Dto` vs `DTO` casing, the duplicate `TenantModel` import in
  `db/models/__init__.py`, the typo `emuns.py`, the `_init_` instead of
  `__init__` in `EncryptLib`, the `setting`/`settings` variable-name
  inconsistency, the dead-code `response.delete_cookie` after `return` in
  `auth_service.py`.) Either leave them, or surface them to the user as a
  separate concern.

---

## 8. How to Add New Features

### 8.1 Adding a new resource (e.g. "invoice")

1. **Model** — `src/server/db/models/invoice_model.py`:
   ```python
   # -*- coding: utf-8 -*-
   from sqlalchemy import Column, String, Integer, DateTime, func
   from src.server.db.models.base import BaseModel
   from src.enum.emuns import RecordStatusEnum

   class InvoiceModel(BaseModel):
       __tablename__ = 'invoice'
       invoice_no = Column(String(64), nullable=False, unique=True, comment="发票号")
       amount = Column(Integer, nullable=False, comment="金额(分)")
       status = Column(String(2), default=RecordStatusEnum.ACTIVATE, comment="状态")
   ```
   Then export it in `src/server/db/models/__init__.py`.

2. **DTOs** — `src/server/dto/invoice_dto.py`:
   ```python
   class InvoiceDto(BaseModel):
       id: int
       invoice_no: str = Field(..., description="发票号")
       amount: int = Field(..., description="金额（分）")
       model_config = {"from_attributes": True}

   class AddInvoiceDto(BaseModel):
       invoice_no: str
       amount: int
       created_user: str
   ```

3. **Repository** — `src/server/db/repository/invoice_repository.py`:
   ```python
   # -*- coding: utf-8 -*-
   from src.server.db.session import with_session
   from src.server.db.models import InvoiceModel
   from src.server.dto.invoice_dto import InvoiceDto, AddInvoiceDto

   @with_session
   def add_invoice_to_db(session, dto: AddInvoiceDto):
       row = InvoiceModel(**dto.model_dump())
       session.add(row); session.flush()
       return row.id

   @with_session
   def get_invoice_from_db(session, invoice_id: int):
       row = session.query(InvoiceModel).filter(
           InvoiceModel.id == invoice_id,
           InvoiceModel.status == RecordStatusEnum.ACTIVATE,
       ).first()
       return InvoiceDto.model_validate(row) if row else None
   ```
   Export it in `db/repository/__init__.py`.

4. **Service** — `src/server/service/invoice_service.py`:
   ```python
   # -*- coding: utf-8 -*-
   import traceback
   from src.configs import logger
   from src.server.dto.response_dto import ApiCommonResponseDTO
   from src.server.dto.invoice_dto import AddInvoiceDto
   from src.server.db.repository import add_invoice_to_db, get_invoice_from_db
   from src.server.utils import TokenChecker

   def create_invoice(dto: AddInvoiceDto, user_id: TokenChecker):
       try:
           if user_id is None:
               return ApiCommonResponseDTO(status=401, message='未登录')
           invoice_id = add_invoice_to_db(dto)
           return ApiCommonResponseDTO(status=200, message='success',
                                       data={'invoice_id': invoice_id})
       except BaseException as e:
           logger.error(e); logger.error(traceback.format_exc())
           return ApiCommonResponseDTO(status=500, message=str(e))
   ```
   Export it in `service/__init__.py`.

5. **Router** — `src/server/api_router/invoice_router.py`:
   ```python
   # -*- coding: utf-8 -*-
   from fastapi import APIRouter, Depends
   from src.server.utils import token_identify
   from src.server.service import create_invoice, get_invoice_detail

   invoice_router = APIRouter(prefix="/invoice", tags=["发票"],
                              dependencies=[Depends(token_identify)])
   invoice_router.post('/create', summary='创建发票')(create_invoice)
   invoice_router.get('/get_detail', summary='获取发票详情')(get_invoice_detail)
   ```
   Wire it in `api_router/__init__.py` and `server/__init__.py:create_app`.

That's the entire process. **Five files. No interfaces. No DI registration.**

### 8.2 Adding a new third-party integration

- Wrapper goes in `src/server/libs/<name>_lib.py`.
- Stateless: a class with `@staticmethod` methods, plus a 2–3 letter singleton
  alias at module bottom.
- Stateful (e.g. SDK client): a class with an `__init__` that constructs the
  client, exposed as a singleton.
- Configuration values land in `BaseSetting` as `SCREAMING_SNAKE_CASE` attrs.

### 8.3 Adding a new AI capability

- **First instinct:** add it to Dify and write a thin proxy endpoint here.
- **Second instinct:** if it must be local, add it under `src/server/ai/`.
- Persist conversation/message via the existing `add_conversation_to_db`/
  `add_message_to_db`/`update_message` repo functions.
- Stream via `EventSourceResponse`.

### 8.4 Adding a new background task

- Just call `background_tasks.add_task(fn, *args)` from inside the service
  function. Don't introduce Celery/RQ.

---

## 9. How AI Assistants Should Behave in This Repo

This section is specifically aimed at LLM coding agents (Claude, etc.).

### 9.1 Default behaviors

- **Match the existing style first.** Read 2–3 neighboring files before writing
  a new one.
- **Be procedural.** Top-level `def` is your default. Reach for a class only
  when the existing code already has a class for that role
  (e.g. SQLAlchemy model, Pydantic DTO, third-party wrapper singleton).
- **Five files for a new feature.** Model, DTO, repository, service, router.
  Resist the urge to add a sixth.
- **Use existing helpers.** Don't recreate token verification, password hashing,
  email sending, MinIO upload, Redis access — they all exist in `libs/` or
  `utils.py`.
- **Return `ApiCommonResponseDTO` from every endpoint.** Never raise for
  business errors.
- **Always wrap repository functions in `@with_session`.** Always pass
  `session` first.
- **Always set `RecordStatusEnum.ACTIVATE` filters on reads** for soft-delete tables.
- **Always include `# -*- coding: utf-8 -*-`** at the top of new files.
- **Always write Chinese `comment=`/`description=`/`summary=`** on user-facing
  schema/API surface.

### 9.2 What to avoid

- **Do not refactor existing code unprompted.** The "messy" parts (commented-out
  legacy code, `BaseException` everywhere, hardcoded secrets, dead-code returns,
  the duplicate import in `models/__init__.py`, the typo in `emuns.py`)
  are intentional artifacts of fast iteration. Touching them breaks
  somebody's mental map. If you spot something genuinely broken, **mention it
  in chat** and let the user decide.
- **Do not propose Alembic, Pydantic Settings, dotenv, mypy, ruff, black,
  pytest, poetry, uv, or any new framework.** If the user asks for one, fine.
  Otherwise stay in your lane.
- **Do not create a `core/`, `domain/`, `application/`, `interfaces/`,
  `abstract/`, or `services/<resource>/` folder.** Five files, flat.
- **Do not async-ify code that does not await.** Sync `def` is correct.
- **Do not split a service function into helpers** unless the helper is
  reused across services.
- **Do not introduce structured logging, OpenTelemetry, Sentry, or other
  observability tooling** unless asked. `logger.info` / `logger.error` is enough.
- **Do not "improve" the response format.** No `{"success": True, "data": ...}`,
  no JSON:API, no envelope versioning. `ApiCommonResponseDTO` is the contract.

### 9.3 When you genuinely don't know

- Ask. The author would rather answer one question than receive a 600-line
  unrequested refactor.
- Or ship a stub that returns `ApiCommonResponseDTO(status=200, data={})`
  with a `# todo:` and surface the incomplete part in chat.

### 9.4 Documents and tests

- **Don't auto-generate `README.md` updates, CHANGELOGs, design docs, or
  ADRs.** None exist. None are wanted unless asked.
- **Don't auto-generate tests.** No `tests/` directory exists. Adding one is
  a real decision and belongs to the user.

---

## 10. Quick Reference Card

| Need to…                          | Do this                                                                                       |
| --------------------------------- | --------------------------------------------------------------------------------------------- |
| Add a new endpoint                | Create handler in `service/`, bind via `router.<verb>(path)(handler)` in `api_router/`        |
| Talk to the DB                    | `@with_session def fn(session, ...)` in `db/repository/`                                      |
| Read settings                     | `setting = get_setting()` at module top, `setting.MY_VALUE`                                   |
| Read auth user id                 | `user_id: TokenChecker` parameter in service signature                                        |
| Send an email                     | `send_mail(body, to, subject)` from `libs/email_lib.py`, usually via `BackgroundTasks`        |
| Upload/download a file            | `upload_file` / `download_file` in `service/oss_service.py`, MinIO-backed                     |
| Stream from a third-party LLM     | `EventSourceResponse(http_stream_request(url, "POST", headers, payload))`                     |
| Rate-limit an action              | Add a function to `libs/redis_lib.py` mirroring `register_rate_limit`, call inside service    |
| Add an enum                       | New `StrEnum` class in `src/enum/emuns.py`                                                    |
| Add a new third-party integration | New `*_lib.py` in `libs/` + config attrs in `BaseSetting`                                     |
| Add an AI capability              | Prefer Dify + thin proxy. Fall back to `src/server/ai/` only if necessary                     |
| Persist a chat message            | `add_conversation_to_db` / `add_message_to_db` / `update_message`                             |
| Soft-delete a row                 | Set `status = RecordStatusEnum.INACTIVATE` and `flush`, never `session.delete(row)`           |
| Hash / verify a password          | `bp.hash_password(p)` / `bp.verify_password(p, hashed)`                                       |
| Issue / verify a JWT              | `token_handler.generate_token(user_id)` / `token_handler.verify_token(t)`                     |
| Log an exception                  | `except BaseException as e: logger.error(e); logger.error(traceback.format_exc())`            |

---

*This guide reflects the codebase as of 2026-05-19. When the conventions
documented here drift from the actual code, **the actual code wins** — read it
first and update this document second.*
