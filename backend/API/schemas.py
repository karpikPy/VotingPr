
from pydantic import BaseModel
from datetime import datetime
from typing import List, Optional




class User(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool 

    class Config:
        orm_mode = True



class PollOptionBase(BaseModel):
    text: str

class PollOptionCreate(PollOptionBase):
    poll_id: int

class PollOption(PollOptionBase):
    id: int
    votes: int

    class Config:
        orm_mode = True

class PollBase(BaseModel):
    title: str

class PollCreate(PollBase):
    pass

class Poll(PollBase):
    id: int
    created_at: datetime
    expires_at: Optional[datetime] = None
    is_active: bool
    options: List[PollOption] = [] 

    class Config:
        orm_mode = True

class VoteCreate(BaseModel):
    poll_option_id: int

class ChatMessageBase(BaseModel):
    sender_id: int
    receiver_id: int
    content: str

    class Config:
        orm_mode = True

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
