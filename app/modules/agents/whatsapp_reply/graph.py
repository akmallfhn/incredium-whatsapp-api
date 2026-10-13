"""Graph keputusan balas atau alihkan percakapan ke staf."""

import logging
from typing import Literal, TypedDict

from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel

from app.modules.agents.llm import build_agent_llm

logger = logging.getLogger(__name__)
MAX_OUTPUT_TOKENS = 1024


class ReplyDecision(BaseModel):
    action: Literal["reply", "transfer", "skip"]
    message: str = ""
    reason: str = ""


class ReplyState(TypedDict, total=False):
    provider: str
    api_model: str
    name: str
    personality: str | None
    system_prompt: str
    transfer_conditions: str
    transcript: str
    knowledge: str
    decision: ReplyDecision
    error: str


async def _decide(state: ReplyState) -> ReplyState:
    try:
        llm = build_agent_llm(
            provider_name=state["provider"],
            model_name=state["api_model"],
            max_tokens=MAX_OUTPUT_TOKENS,
            structured_output=ReplyDecision,
        )
        system = (
            f"{state['system_prompt']}\n\n"
            f"Nama agent: {state['name']}\n"
            f"Kepribadian dan latar agent:\n{state.get('personality') or 'Tidak ada.'}\n\n"
            f"Kondisi alihkan ke staf:\n{state['transfer_conditions'] or 'Tidak ada.'}\n\n"
            "Kembalikan JSON valid dengan field action (reply, transfer, atau skip), "
            "message, dan reason. Untuk reply, isi message singkat dalam bahasa percakapan. "
            "Jangan menjawab hal yang tidak didukung pengetahuan yang tersedia."
        )
        context = f"Pengetahuan:\n{state['knowledge']}\n\nRiwayat pesan:\n{state['transcript']}"
        result = await llm.ainvoke([SystemMessage(content=system), HumanMessage(content=context)])
        if isinstance(result, ReplyDecision):
            return {"decision": result}
        return {"error": "LLM response was not structured"}
    except Exception as exc:
        logger.exception("agent reply: node decide gagal")
        return {"error": f"{type(exc).__name__}: {exc}"}


def _route(state: ReplyState) -> str:
    if state.get("error") or "decision" not in state:
        return "skip"
    return state["decision"].action


async def _done(state: ReplyState) -> ReplyState:
    return {}


def build_reply_graph():
    graph = StateGraph(ReplyState)
    graph.add_node("decide", _decide)
    graph.add_node("reply", _done)
    graph.add_node("transfer", _done)
    graph.add_node("skip", _done)
    graph.add_edge(START, "decide")
    graph.add_conditional_edges(
        "decide", _route, {"reply": "reply", "transfer": "transfer", "skip": "skip"}
    )
    graph.add_edge("reply", END)
    graph.add_edge("transfer", END)
    graph.add_edge("skip", END)
    return graph.compile()
