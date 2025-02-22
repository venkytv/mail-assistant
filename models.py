import pydantic

class EmailData(pydantic.BaseModel):
    from_: list[str]
    to: list[str]
    subject: str
    date: str
    message_id: str
    body: str

class EmailParseError(pydantic.BaseModel):
    sender: str
    date: str
    error: str

class Task(pydantic.BaseModel):
    action: str
    due_date: str = ""

class Notification(pydantic.BaseModel):
    title: str
    message: str
