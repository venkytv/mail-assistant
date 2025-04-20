from enum import Enum
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import Any

class EmailData(BaseModel):
    from_: list[str] = Field(serialization_alias="from")
    to: list[str]
    subject: str
    date: str
    message_id: str
    body: str

class EmailParseError(BaseModel):
    sender: str
    date: str
    error: str

class HeaderAnalysis(BaseModel):
    clean_subject: str = Field(title="Cleaned subject line",
                               description="Subject line with tone being direct and professional conveying essential information concisely",
                               default="")
    is_important: bool = Field(title="Is the email important?")
    is_transactional: bool = Field(title="Is the email transactional?")
    due_date: str = Field(title="Optional due date for the action", default="")
    notify: bool = Field(title="Should the user be notified?")
    needs_analysis: bool = Field(title="Does the email need further analysis as header data is not sufficient?")
    analysis_reason: str = Field(title="Reason why further analysis is needed", default="")

class EmailAction(BaseModel):
    action: str = Field(title="Action to be taken on the email", default="")
    due_date: str = Field(title="Optional due date for the action", default="")
    is_important: bool = Field(title="Is the email important?", default=False)
    notify: bool = Field(title="Should the user be notified?", default=False)

    @field_validator("action", mode="before")
    @classmethod
    def check_action(cls, value: Any) -> str:
        if not value:
            return ""
        return str(value)

    @field_validator("due_date", mode="before")
    @classmethod
    def check_due_date(cls, value: Any) -> str:
        if not value:
            return ""
        return str(value)

class Task(BaseModel):
    action: str
    due_date: str = ""

class Notification(BaseModel):
    title: str
    message: str
