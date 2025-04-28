from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, Text, Boolean
from sqlalchemy.orm import relationship
from backend.database.database import Base
from datetime import datetime


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True)
    email = Column(String(100), unique=True, index=True)
    password = Column(String(100))
    is_admin = Column(Boolean, default=False) 
    messages_sent = relationship("ChatMessage", back_populates="sender", foreign_keys="ChatMessage.sender_id")
    messages_received = relationship("ChatMessage", back_populates="receiver", foreign_keys="ChatMessage.receiver_id")

    created_polls = relationship("Poll", back_populates="creator")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True)
    content = Column(Text)
    timestamp = Column(DateTime, default=datetime.now)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    sender = relationship("User", foreign_keys=[sender_id], back_populates="messages_sent")
    receiver = relationship("User", foreign_keys=[receiver_id], back_populates="messages_received")

class Poll(Base):
    __tablename__ = 'polls'

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    creator_id = Column(Integer, ForeignKey("users.id")) 

    options = relationship("PollOption", back_populates="poll", cascade="all, delete")
    creator = relationship("User", back_populates="created_polls") 

class PollOption(Base):
    __tablename__ = 'poll_options'

    id = Column(Integer, primary_key=True, index=True)
    poll_id = Column(Integer, ForeignKey('polls.id'))
    text = Column(String, nullable=False)
    votes = Column(Integer, default=0)

    poll = relationship("Poll", back_populates="options")
