from pydantic import BaseModel, field_validator
from datetime import datetime, timezone
from typing import List, Optional


class User(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool

    class Config:
        from_attributes = True


class PollOptionBase(BaseModel):
    text: str


class PollOptionCreate(PollOptionBase):
    poll_id: int


class PollOption(PollOptionBase):
    id: int
    votes: int

    class Config:
        from_attributes = True


class PollBase(BaseModel):
    title: str


class PollCreate(PollBase):
    expires_at: Optional[datetime] = None

    @field_validator('expires_at')
    def expires_at_must_be_in_future(cls, v):
        if v is not None:
            now_utc = datetime.now(timezone.utc)
            if v <= now_utc:
                raise ValueError('expires_at must be in the future')
        return v


class Poll(PollBase):
    id: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    creator_id: int
    options: List[PollOption] = []

    class Config:
        from_attributes = True


class VoteCreate(BaseModel):
    poll_option_id: int


class VoteBase(BaseModel):
    poll_option_id: int


class Vote(VoteBase):
    id: int
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


class ChatMessageBase(BaseModel):
    sender_id: int
    receiver_id: int
    content: str

    class Config:
        from_attributes = True


class UserCreate(BaseModel):
    username: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str