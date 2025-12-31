from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Any

Role = Literal["system","user","assistant","tool"]

class Message(BaseModel):
    role: Role
    content: str

class ChatRequest(BaseModel):
    model: str
    messages: List[Message]
    temperature: Optional[float] = 0.7
    max_tokens: Optional[int] = 512
    stream: Optional[bool] = False  # để tương thích sau này

class Choice(BaseModel):
    index: int
    message: Message
    finish_reason: Optional[str] = "stop"

class Usage(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

class ChatResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Choice]
    usage: Usage = Field(default_factory=Usage)
