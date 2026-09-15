"""Model dan batas token agent Knowledge."""

import logging
from functools import lru_cache

from langchain_core.messages import HumanMessage
from langchain_core.runnables import Runnable

from app.modules.agents.llm import Tier, build_llm
from app.modules.knowledge.prompts import TITLE_PROMPT
from app.modules.knowledge.tools import ToolBox

logger = logging.getLogger(__name__)

# Node planner cuma memilih tool dan mengisi argumennya, jadi model kecil sudah cukup.
PLANNER_MAX_TOKENS = 500

# Node jawaban dilihat orang, jadi model penuh; 3000 = daftar 100 baris plus pengantar.
ANSWER_MAX_TOKENS = 3000

TITLE_MAX_TOKENS = 32

# Jawaban boleh lebih lama dari agent webhook: orangnya sedang menunggu di depan layar.
ANSWER_TIMEOUT = 180.0


@lru_cache(maxsize=1)
def planner_llm() -> Runnable:
    return build_llm(
        tier=Tier.FAST,
        max_tokens=PLANNER_MAX_TOKENS,
        tools=ToolBox.definitions(),
    )


@lru_cache(maxsize=1)
def answer_llm() -> Runnable:
    return build_llm(tier=Tier.FULL, max_tokens=ANSWER_MAX_TOKENS, timeout=ANSWER_TIMEOUT)


@lru_cache(maxsize=1)
def title_llm() -> Runnable:
    return build_llm(tier=Tier.FAST, max_tokens=TITLE_MAX_TOKENS)


async def generate_title(question: str) -> str:
    """Judul thread dari pertanyaan pertama; dipanggil sesudah jawaban selesai."""
    result = await title_llm().ainvoke(
        [HumanMessage(content=TITLE_PROMPT.format(question=question[:500]))],
        config={"run_name": "knowledge-title"},
    )
    return str(getattr(result, "content", "")).strip().strip('"').strip()
