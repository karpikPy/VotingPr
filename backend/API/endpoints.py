
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session, joinedload
from backend.database.database import get_db
from backend.API.schemas import (
    ChatMessageBase, PollOptionBase, UserCreate, UserLogin, Token,
    PollCreate, PollOptionCreate, VoteCreate, Poll as PollSchema, PollOption as PollOptionSchema,
    User as UserSchema 
)
from backend.API.models import ChatMessage, User, Poll, PollOption
from backend.auth.auth import get_password_hash, verify_password, create_access_token, get_user_by_email, get_current_user, get_current_admin_user

router = APIRouter()



@router.get("/users/me", response_model=UserSchema) 
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user


@router.get("/polls", response_model=list[PollSchema])
def get_polls(db: Session = Depends(get_db)):
    polls = db.query(Poll).options(joinedload(Poll.options)).all()
    return polls


@router.get("/polls/{poll_id}", response_model=PollSchema)
def get_poll(poll_id: int, db: Session = Depends(get_db)):
    poll = db.query(Poll).options(joinedload(Poll.options)).filter(Poll.id == poll_id).first()
    if poll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Опитування не знайдено")
    return poll


@router.post("/polls", response_model=PollSchema)
def create_poll(poll: PollCreate, db: Session = Depends(get_db)):
    db_poll = Poll(title=poll.title)
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
    current_admin_user: User = Depends(get_current_admin_user)
):
    db_poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if db_poll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Опитування не знайдено")

    db_poll.title = poll_update.title

    db.commit()
    db.refresh(db_poll)
    return db_poll


@router.put("/polls/options/{option_id}", response_model=PollOptionSchema)
async def update_poll_option(
    option_id: int,
    option_update: PollOptionBase, 
    db: Session = Depends(get_db),
    current_admin_user: User = Depends(get_current_admin_user)
):
    db_option = db.query(PollOption).filter(PollOption.id == option_id).first()
    if db_option is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Опція опитування не знайдена")

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
    db_option = db.query(PollOption).filter(PollOption.id == vote.poll_option_id).first()
    if db_option is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Опція опитування не знайдена")

    db_option.votes += 1
    db.commit()
    db.refresh(db_option)
    return db_option


@router.delete("/polls/{poll_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_poll(
    poll_id: int,
    db: Session = Depends(get_db),
    current_admin_user: User = Depends(get_current_admin_user) 
):
    db_poll = db.query(Poll).filter(Poll.id == poll_id).first()
    if db_poll is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Опитування не знайдено")

    db.delete(db_poll)
    db.commit()


    return {"detail": "Опитування успішно видалено"}




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