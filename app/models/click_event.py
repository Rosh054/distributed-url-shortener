from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class ClickEvent(SQLModel, table=True):
    __tablename__ = "click_events"

    id: Optional[int] = Field(default=None, primary_key=True)
    short_code: str = Field(index=True, max_length=64)
    ip_hash: str = Field(max_length=64)
    user_agent: Optional[str] = Field(default=None, max_length=512)
    referrer: Optional[str] = Field(default=None, max_length=2048)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
