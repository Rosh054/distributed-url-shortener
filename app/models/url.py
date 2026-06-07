from datetime import datetime
from typing import Optional

from sqlmodel import Field, SQLModel


class Url(SQLModel, table=True):
    __tablename__ = "urls"

    id: Optional[int] = Field(default=None, primary_key=True)
    short_code: str = Field(index=True, unique=True, max_length=64)
    long_url: str = Field(max_length=2048)
    custom_alias: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow, index=True)
    expires_at: Optional[datetime] = Field(default=None, index=True)
    deleted_at: Optional[datetime] = Field(default=None)
    total_clicks: int = Field(default=0)
