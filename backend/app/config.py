import os
from langchain_openai import ChatOpenAI

# ── Model map ───

AGENT_MODEL_MAP: dict[str, str] = {
    "supervisor": "gpt-4o",
    "retrieval":  "gpt-4o",
    "analysis":   "gpt-4o",
    "synthesis":  "gpt-4o",
    "critic":     "gpt-4o",
}
DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "gpt-4o")


def get_llm(agent_id: str) -> ChatOpenAI:
    model = AGENT_MODEL_MAP.get(agent_id, DEFAULT_MODEL)
    return ChatOpenAI(model=model, temperature=0)


# ── Infrastructure 

CHROMA_HOST: str = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT: int = int(os.getenv("CHROMA_PORT", "8000"))

REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379")

SQLITE_PATH: str = os.getenv("SQLITE_PATH", "/data/sqlite/episodic.db")

# ── Feature flags 

DEBUG_MODE: bool = os.getenv("DEBUG_MODE", "true").lower() == "true"
LOG_LEVEL: str = os.getenv("LOG_LEVEL", "debug")

LLM_CACHE_ENABLED: bool = os.getenv("LLM_CACHE_ENABLED", "true").lower() == "true"
LLM_CACHE_TTL_SECONDS: int = int(os.getenv("LLM_CACHE_TTL_SECONDS", "3600"))

# ── Retrieval 

MAX_RETRIEVAL_STEPS: int = int(os.getenv("MAX_RETRIEVAL_STEPS", "8"))
MAX_TOOL_RETRIES: int = int(os.getenv("MAX_TOOL_RETRIES", "3"))
RETRIEVAL_TOP_K: int = int(os.getenv("RETRIEVAL_TOP_K", "10"))

# ── Critic 

MAX_REVISIONS: int = int(os.getenv("MAX_REVISIONS", "2"))
CRITIC_PASS_THRESHOLD: float = float(os.getenv("CRITIC_PASS_THRESHOLD", "0.75"))


MIN_SOURCES_PER_SUBQUESTION: float = float(os.getenv("MIN_SOURCES_PER_SUBQUESTION", "2.0"))
MIN_SOURCE_CREDIBILITY: float = float(os.getenv("MIN_SOURCE_CREDIBILITY", "0.6"))
MAX_RETRIEVAL_ATTEMPTS_PER_SUBQUESTION: int = int(os.getenv("MAX_RETRIEVAL_ATTEMPTS_PER_SUBQUESTION", "2"))
