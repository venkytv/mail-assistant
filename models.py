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
