import datetime
from enum import Enum
import logging
from pydantic import BaseModel, Field, ValidationError, field_validator
from typing import Any, Optional

logger = logging.getLogger(__name__)

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
    message_id: str = Field(title="Message ID", default="", description="Ignore this field")
    message_from: str = Field(title="Sender details", default="",
                              description="Sender name in human-friendly format, with email address being a last resort")
    summary: str = Field(title="A one-line summary of the email", default=""),
    is_important: bool = Field(title="Is the email important?")
    has_task: bool = Field(title="Does the email contain a task?")
    due_date: Optional[datetime.date] = Field(title="Optional due date for the task in YYYY-MM-DD format", default=None)
    notify: bool = Field(title="Should the user be notified?")

    @field_validator("due_date", mode="before")
    @classmethod
    def check_due_date(cls, value: Any) -> str:
        logger.debug(f"Checking header analysis due date: {value}")
        if not value:
            return None
        return str(value)

class EmailAction(BaseModel):
    action: str = Field(title="Action to be taken on the email", default="")
    due_date: Optional[datetime.date] = Field(title="Optional due date for the action in YYYY-MM-DD format", default=None)
    is_important: bool = Field(title="Is the email important?", default=False)
    notify: bool = Field(title="Should the user be notified?", default=False)

    @field_validator("action", mode="before")
    @classmethod
    def check_action(cls, value: Any) -> str:
        logger.debug(f"Checking email action: {value}")
        if not value:
            return ""
        return str(value)

    @field_validator("due_date", mode="before")
    @classmethod
    def check_due_date(cls, value: Any) -> str:
        logger.debug(f"Checking email action due date: {value}")
        if not value:
            return None
        return str(value)

class Task(BaseModel):
    action: str
    due_date: str = ""

    @field_validator("due_date", mode="before")
    @classmethod
    def check_due_date(cls, value: Any) -> str:
        logger.debug(f"Validating task due date: {value}")
        return str(value)

class Notification(BaseModel):
    title: str
    message: str
