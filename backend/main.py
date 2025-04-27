from fastapi import FastAPI, Request
from fastapi.templating import Jinja2Templates
from backend.database.database import Base, engine
from API import endpoints
import uvicorn

templates = Jinja2Templates(directory="C:/Users/Kirill/PycharmProjects/VotingProject1/frontend/templates")


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Poll App")


app.include_router(endpoints.router)

@app.get("/")
def root():
    return {"message": "Poll App is running"}

@app.get("/home")
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})

@app.get("/polls_page")
async def polls_page(request: Request):
    return templates.TemplateResponse("polls.html", {"request": request})

@app.get("/create_poll_page")
async def create_poll_page(request: Request):
    return templates.TemplateResponse("create_poll.html", {"request": request})

@app.get("/chat/{user_id}") 
async def chat_page(request: Request, user_id: int):
    return templates.TemplateResponse("chat.html", {"request": request, "chat_partner_id": user_id})


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)
