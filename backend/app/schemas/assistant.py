from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ChatMessage(BaseModel):
    role: str
    content: str
    
class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    
class ChatResponse(BaseModel):
    response: str
    generated_at: datetime = datetime.utcnow()
