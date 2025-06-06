from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Form, Query
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.sql import func
from datetime import datetime, timedelta
from typing import Optional
from database import get_db
from .schemas import (
    ChatMessageBase,
    PollOptionBase,
    Token,
    PollCreate,
    VoteCreate,
    Poll as PollSchema,
    PollOption as PollOptionSchema,
    User as UserSchema
)
from .models import ChatMessage, User, Poll, PollOption, Vote
from auth.auth import (get_password_hash,
                       verify_password,
                       create_access_token,
                       get_user_by_email,
                       get_current_user,
                       get_current_admin_user)

router = APIRouter()


@router.get("/users/me", response_model=UserSchema)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/users", response_model=list[UserSchema])
async def get_all_users(db: Session = Depends(get_db), current_user: User = Depends(get_current_user)):
    users = db.query(User).filter(User.id != current_user.id).all()
    return users


@router.get("/polls", response_model=list[PollSchema])
def get_polls(
        db: Session = Depends(get_db),
        activity: Optional[str] = Query(None),
        time: Optional[str] = Query(None)
):
    query = db.query(Poll).options(
        joinedload(Poll.options).joinedload(PollOption.vote_records)
    ).order_by(Poll.created_at.desc())

    now_utc = datetime.utcnow()

    if activity == "active":
        query = query.filter(
            (Poll.expires_at == None) | (Poll.expires_at > now_utc)
        )
    elif activity == "inactive":
        query = query.filter(
            (Poll.expires_at != None) & (Poll.expires_at <= now_utc)
        )

    if time:
        today_utc_date = now_utc.date()
        if time == "today":
            query = query.filter(func.date(Poll.created_at) == today_utc_date)
        elif time == "week":
            start_of_week_utc = today_utc_date - timedelta(days=today_utc_date.weekday())
            end_of_week_utc = start_of_week_utc + timedelta(days=6)
            query = query.filter(func.date(Poll.created_at) >= start_of_week_utc,
                                 func.date(Poll.created_at) <= end_of_week_utc)
        elif time == "month":
            query = query.filter(func.extract('year', Poll.created_at) == now_utc.year,
                                 func.extract('month', Poll.created_at) == now_utc.month)

    polls = query.all()

    for poll in polls:
        for option in poll.options:
            option.votes = len(option.vote_records)

    return polls


@router.get("/polls/{poll_id}", response_model=PollSchema)
def get_poll(poll_id: int, db: Session = Depends(get_db)):
    poll = db.query(Poll).options(joinedload(Poll.options)).filter(Poll.id == poll_id).first()
    if poll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Опитування не знайдено")
    return poll


@router.post("/polls", response_model=PollSchema)
async def create_poll(
        poll: PollCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    db_poll = Poll(
        title=poll.title,
        creator_id=current_user.id,
        expires_at=poll.expires_at
    )
    db.add(db_poll)
    db.commit()
    db.refresh(db_poll)
    return db_poll


@router.post("/polls/{poll_id}/options/", response_model=PollOptionSchema)
def create_poll_option(poll_id: int, option: PollOptionBase, db: Session = Depends(get_db)):
    db_poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if db_poll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Опитування не знайдено")

    db_option = PollOption(poll_id=poll_id, text=option.text)
    db.add(db_option)
    db.commit()
    db.refresh(db_option)
    return db_option


@router.put("/polls/{poll_id}", response_model=PollSchema)
async def update_poll(
        poll_id: int,
        poll_update: PollCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    db_poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if db_poll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Опитування не знайдено")

    if not current_user.is_admin and db_poll.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted",
        )

    db_poll.title = poll_update.title
    if poll_update.expires_at is not None:
        db_poll.expires_at = poll_update.expires_at
    db.commit()
    db.refresh(db_poll)
    return db_poll


@router.put("/polls/options/{option_id}", response_model=PollOptionSchema)
async def update_poll_option(
        option_id: int,
        option_update: PollOptionBase,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    db_option = db.query(PollOption).options(joinedload(PollOption.poll)).filter(PollOption.id == option_id).first()
    if db_option is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Опція опитування не знайдена")

    db_poll = db_option.poll

    if not current_user.is_admin and db_poll.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted",
        )

    db_option.text = option_update.text
    db.commit()
    db.refresh(db_option)
    return db_option


@router.post("/votes/", response_model=PollOptionSchema)
async def vote_for_option(
        vote: VoteCreate,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    db_option = db.query(PollOption).options(joinedload(PollOption.poll)).filter(
        PollOption.id == vote.poll_option_id).first()
    if db_option is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Опція опитування не знайдена")

    if db_option.poll.expires_at and db_option.poll.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Опитування закінчилося")

    existing_vote = db.query(Vote).join(PollOption).filter(
        Vote.user_id == current_user.id,
        PollOption.poll_id == db_option.poll_id
    ).first()

    if existing_vote:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ви вже проголосували в цьому опитуванні"
        )

    new_vote = Vote(
        user_id=current_user.id,
        poll_option_id=vote.poll_option_id
    )
    db.add(new_vote)

    db_option.votes += 1

    db.commit()
    db.refresh(db_option)
    return db_option


@router.delete("/polls/{poll_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poll(
        poll_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    db_poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if db_poll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Опитування не знайдено")

    if not current_user.is_admin and db_poll.creator_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation not permitted",
        )

    db.delete(db_poll)
    db.commit()

    return {"detail": "Опитування успішно видалено"}


@router.websocket("/ws/{client_id}")
async def websocket_chat(websocket: WebSocket, client_id: int):
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            await websocket.send_text(f"Повідомлення від клієнта {client_id}: {data}")
    except WebSocketDisconnect:
        await websocket.close()
        print(f"Клієнт {client_id} відключився")


@router.post("/send_message", response_model=ChatMessageBase)
async def send_message(message: ChatMessageBase, db: Session = Depends(get_db)):
    new_message = ChatMessage(
        sender_id=message.sender_id,
        receiver_id=message.receiver_id,
        content=message.content
    )
    db.add(new_message)
    db.commit()
    db.refresh(new_message)
    return new_message


@router.get("/get_messages", response_model=list[ChatMessageBase])
async def get_messages(db: Session = Depends(get_db)):
    messages = db.query(ChatMessage).all()
    return messages


@router.get("/messages/{other_user_id}", response_model=list[ChatMessageBase])
async def get_messages_between_users(
        other_user_id: int,
        db: Session = Depends(get_db),
        current_user: User = Depends(get_current_user)
):
    current_user_id = current_user.id

    messages = db.query(ChatMessage).filter(
        ((ChatMessage.sender_id == current_user_id) & (ChatMessage.receiver_id == other_user_id)) |
        ((ChatMessage.sender_id == other_user_id) & (ChatMessage.receiver_id == current_user_id))
    ).order_by(ChatMessage.timestamp).all()

    return messages


@router.post("/register", response_model=Token)
async def register(
        username: str = Form(...),
        email: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db)
):
    db_user = get_user_by_email(db, email)
    if db_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Користувач з таким email вже існує")

    hashed_password = get_password_hash(password)

    db_user = User(username=username, email=email, password=hashed_password)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return {"access_token": create_access_token(data={"sub": db_user.email}), "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login(
        email: str = Form(...),
        password: str = Form(...),
        db: Session = Depends(get_db)
):
    db_user = get_user_by_email(db, email)
    if not db_user or not verify_password(password, db_user.password):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Неправильний email або пароль")
    return {"access_token": create_access_token(data={"sub": db_user.email}), "token_type": "bearer"}
