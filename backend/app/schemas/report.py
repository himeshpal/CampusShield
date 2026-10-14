from datetime import datetime

from pydantic import BaseModel, Field


class ReportCreate(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    include_details: bool = True  # one page section per asset with its evidence


class ReportOut(BaseModel):
    id: int
    number: str
    title: str
    include_details: bool
    summary: dict
    pages: int
    size_bytes: int
    sha256: str
    generated_by: str | None
    created_at: datetime
