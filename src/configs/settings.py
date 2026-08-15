# -*- coding: utf-8 -*-
"""Runtime configuration.

Production secrets must be supplied through the service environment file.  No
provider key, database password, or mail credential belongs in this module.
"""

import os


VERSION = "1.0.0"


def env_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


class BaseSetting:
    BASE_PATH = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    LOG_PATH = os.getenv("LOG_PATH", os.path.join(BASE_PATH, "log"))
    STORAGE_PATH = os.getenv("STORAGE_PATH", os.path.join(BASE_PATH, "storage"))
    KB_ROOT_PATH = os.getenv("KB_ROOT_PATH", os.path.join(BASE_PATH, "kb"))
    LOG_FILE_SIZE = os.getenv("LOG_FILE_SIZE", "10 MB")
    GUNICORN_WORKER_NUMBER = env_int("GUNICORN_WORKER_NUMBER", 1)
    GUNICORN_THREAD_NUMBER = env_int("GUNICORN_THREAD_NUMBER", 1)

    RUNTIME_ENV = os.getenv("RUNTIME_ENV", "dev")
    SECRET_KEY = os.getenv("SECRET_KEY", "local-development-secret-change-me")
    TOKEN_EXPIRE_HOURS = env_int("TOKEN_EXPIRE_HOURS", 24)
    COOKIE_SECURE = env_bool("COOKIE_SECURE", RUNTIME_ENV == "prod")
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = env_int("APP_PORT", 8000)
    PUBLIC_ORIGINS = [
        item.strip()
        for item in os.getenv(
            "PUBLIC_ORIGINS",
            "http://localhost:3000,https://preview.0x7o7.top,https://0x7o7.top,https://www.0x7o7.top",
        ).split(",")
        if item.strip()
    ]

    # Email
    SMTP_HOST = os.getenv("SMTP_HOST", "smtp.163.com")
    SMTP_PORT = env_int("SMTP_PORT", 465)
    SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
    SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
    SENDER = os.getenv("SENDER", SMTP_USERNAME)
    RECEIVER = os.getenv("LEAD_NOTIFICATION_EMAIL", "")

    # Object storage
    MINIO_SERVICE_URL = os.getenv("MINIO_SERVICE_URL", "127.0.0.1:9000")
    MINIO_ACCESS_KEY = os.getenv("MINIO_ACCESS_KEY", "")
    MINIO_SECRET_KEY = os.getenv("MINIO_SECRET_KEY", "")
    MINIO_BUCKET = os.getenv("MINIO_BUCKET", "service")

    # OCR (legacy demo compatibility)
    OCR_BASE_URL = os.getenv("OCR_BASE_URL", "https://aip.baidubce.com/rest/2.0/ocr/v1/accurate_basic")
    OCR_AUTH_URL = os.getenv("OCR_AUTH_URL", "https://aip.baidubce.com/oauth/2.0/token")
    OCR_API_KEY = os.getenv("OCR_API_KEY", "")
    OCR_API_SECRET = os.getenv("OCR_API_SECRET", "")
    OCR_APP_ID = os.getenv("OCR_APP_ID", "")
    OCR_FILE_LIMIT = env_int("OCR_FILE_LIMIT", 3)

    # Redis and abuse controls
    REDIS_URL = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
    REDIS_BLOCK_TIME = env_int("REDIS_BLOCK_TIME", 300)
    REDIS_REQUEST_REQUEST_LIMIT = env_int("REDIS_REQUEST_REQUEST_LIMIT", 5)
    VERIFY_CODE_TTL = env_int("VERIFY_CODE_TTL", 600)
    VERIFY_COOLDOWN_TTL = env_int("VERIFY_COOLDOWN_TTL", 60)
    VERIFY_IP_LIMIT = env_int("VERIFY_IP_LIMIT", 5)
    VERIFY_IP_TTL = env_int("VERIFY_IP_TTL", 60)
    VERIFY_FAIL_LIMIT = env_int("VERIFY_FAIL_LIMIT", 5)
    VERIFY_FAIL_TTL = env_int("VERIFY_FAIL_TTL", 300)
    LOGIN_IP_LIMIT = env_int("LOGIN_IP_LIMIT", 5)
    LOGIN_IP_TTL = env_int("LOGIN_IP_TTL", 60)
    AI_GUEST_LIMIT = env_int("AI_GUEST_LIMIT", 3)
    AI_GUEST_TTL = env_int("AI_GUEST_TTL", 86400)
    AI_USER_LIMIT = env_int("AI_USER_LIMIT", 20)
    AI_USER_TTL = env_int("AI_USER_TTL", 3600)
    AI_IP_LIMIT = env_int("AI_IP_LIMIT", 10)
    AI_IP_TTL = env_int("AI_IP_TTL", 60)
    DEMO_GUEST_QUESTION_LIMIT = env_int("DEMO_GUEST_QUESTION_LIMIT", 1)
    DEMO_USER_ANALYSIS_LIMIT = env_int("DEMO_USER_ANALYSIS_LIMIT", 5)
    DEMO_USER_ANALYSIS_TTL = env_int("DEMO_USER_ANALYSIS_TTL", 3600)
    ADMIN_ROLE = "admin"
    GUEST_ROLE = "guest"

    # Dify integrations. The flagship demo uses its own published Workflow key.
    DIFY_SERVER_URL = os.getenv("DIFY_SERVER_URL", "")
    DIFY_UPLOAD_FILE_LIMIT = env_int("DIFY_UPLOAD_FILE_LIMIT", 3)
    DIFY_KB_SECRET_KEY = os.getenv("DIFY_KB_SECRET_KEY", "")
    DIFY_CHAT_SECRET_KEY = os.getenv("DIFY_CHAT_SECRET_KEY", "")
    DIFY_OCR_SECRET_KEY = os.getenv("DIFY_OCR_SECRET_KEY", "")
    DIFY_DEMO_SECRET_KEY = os.getenv("DIFY_DEMO_SECRET_KEY", "")
    DIFY_PASSWORD = os.getenv("DIFY_PASSWORD", "")

    # OpenAI-compatible model provider
    LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.siliconflow.cn/v1")
    LLM_API_KEY = os.getenv("LLM_API_KEY", "")
    LLM_MODEL = os.getenv("LLM_MODEL", "Qwen/Qwen3-8B")
    LLM_TEMPERATURE = float(os.getenv("LLM_TEMPERATURE", "0.2"))
    LLM_MAX_TOKENS = env_int("LLM_MAX_TOKENS", 2048)
    LLM_TOP_P = float(os.getenv("LLM_TOP_P", "0.9"))
    LLM_REQUEST_TIMEOUT = env_int("LLM_REQUEST_TIMEOUT", 45)
    LLM_STREAM_TIMEOUT = env_int("LLM_STREAM_TIMEOUT", 90)
    LLM_MAX_RETRIES = env_int("LLM_MAX_RETRIES", 1)
    EMBEDDING_BASE_URL = os.getenv("EMBEDDING_BASE_URL", LLM_BASE_URL)
    EMBEDDING_API_KEY = os.getenv("EMBEDDING_API_KEY", LLM_API_KEY)
    EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-0.6B")
    EMBEDDING_DIMENSION = env_int("EMBEDDING_DIMENSION", 1024)
    RERANKER_MODEL = os.getenv("RERANKER_MODEL", "Qwen/Qwen3-Reranker-0.6B")
    DEFAULT_LLM = LLM_MODEL
    GENERATE_TRAINING_MATERIAL_LLM = LLM_MODEL
    DEFAULT_EMBED = EMBEDDING_MODEL
    DEFAULT_RERANKER = RERANKER_MODEL
    DEFAULT_TEMPERATURE = 0
    DEFAULT_STREAM = True
    DEFAULT_VERBOSE = False
    MAX_TOKENS = None
    LLM_SETTING = []

    # RAG and flagship demo limits
    RAG_TOP_K = env_int("RAG_TOP_K", 5)
    RAG_FETCH_K = env_int("RAG_FETCH_K", 20)
    RAG_SCORE_THRESHOLD = None
    RAG_MAX_CONTEXT_CHARS = env_int("RAG_MAX_CONTEXT_CHARS", 10000)
    RAG_CHUNK_SIZE = env_int("RAG_CHUNK_SIZE", 800)
    RAG_CHUNK_OVERLAP = env_int("RAG_CHUNK_OVERLAP", 120)
    VECTOR_PATH = os.path.join(STORAGE_PATH, "vector_file")
    DEMO_UPLOAD_ROOT = os.getenv("DEMO_UPLOAD_ROOT", os.path.join(STORAGE_PATH, "demo"))
    DEMO_UPLOAD_MAX_BYTES = env_int("DEMO_UPLOAD_MAX_BYTES", 10 * 1024 * 1024)
    DEMO_UPLOAD_MAX_PAGES = env_int("DEMO_UPLOAD_MAX_PAGES", 50)
    DEMO_UPLOAD_MAX_CHARS = env_int("DEMO_UPLOAD_MAX_CHARS", 250000)
    DEMO_RETENTION_HOURS = env_int("DEMO_RETENTION_HOURS", 24)

    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres@127.0.0.1:5432/service_data",
    )
    CRM_DATABASE_URL = os.getenv("CRM_DATABASE_URL", "")


class UnitTestSetting(BaseSetting):
    pass


class DevSetting(BaseSetting):
    pass


class ProdSetting(BaseSetting):
    pass
