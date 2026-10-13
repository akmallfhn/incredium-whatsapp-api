from typing import Literal

from pydantic import BaseModel


class AgentListRequest(BaseModel):
    tenant_id: str
    page: int = 1
    page_size: int = 20


class AgentDetailsRequest(BaseModel):
    tenant_id: str
    id: str


class AgentCreateRequest(BaseModel):
    tenant_id: str
    name: str


class AgentUpdateRequest(BaseModel):
    tenant_id: str
    id: str
    model_id: int | None = None
    name: str | None = None
    personality: str | None = None
    system_prompt: str | None = None
    transfer_conditions: str | None = None


class AgentDeleteRequest(BaseModel):
    tenant_id: str
    id: str


class AgentSelectRequest(BaseModel):
    tenant_id: str
    agent_id: str | None


class KnowledgeListRequest(BaseModel):
    tenant_id: str
    agent_id: str
    page: int = 1
    page_size: int = 20


class KnowledgeDetailsRequest(BaseModel):
    tenant_id: str
    agent_id: str
    id: str


class KnowledgeCreateRequest(BaseModel):
    tenant_id: str
    agent_id: str
    title: str
    kind: Literal["text", "url", "file"]
    source_uri: str | None = None
    content: str | None = None
    status: Literal["active", "inactive"] = "inactive"


class KnowledgeUpdateRequest(BaseModel):
    tenant_id: str
    agent_id: str
    id: str
    title: str | None = None
    kind: Literal["text", "url", "file"] | None = None
    source_uri: str | None = None
    content: str | None = None
    status: Literal["active", "inactive"] | None = None


class KnowledgeDeleteRequest(BaseModel):
    tenant_id: str
    agent_id: str
    id: str
