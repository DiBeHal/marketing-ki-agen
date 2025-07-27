# agent/schemas.py

from typing import Optional, Dict
from pydantic import BaseModel

class Customer(BaseModel):
    id: Optional[str] = None
    name: str
    email: Optional[str] = None
    notes: Optional[str] = None

class MemoryEntry(BaseModel):
    id: Optional[str] = None
    content: str

class ActivityItem(BaseModel):
    timestamp: str
    user: str
    action: str
    metadata: Optional[Dict[str, str]] = None

class FeedbackItem(BaseModel):
    user: str
    message: str
    created_at: str

class ReportStatus(BaseModel):
    status: str
    result: Optional[str] = None
