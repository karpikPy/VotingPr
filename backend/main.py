from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from database.database import Base, engine
from API import endpoints
import uvicorn
import os


current_script_path = os.path.dirname(os.path.abspath(__file__))

project_root_dir = os.path.join(current_script_path, '..')
templates_dir = os.path.join(project_root_dir, "frontend", "templates")


templates = Jinja2Templates(directory=templates_dir)


Base.metadata.create_all(bind=engine)

app = FastAPI(title="Poll App")

app.include_router(endpoints.router, prefix="/api")


@app.get("/")
def root():
    return RedirectResponse("http://127.0.0.1:8000/home")


@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})


@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request})


@app.get("/home")
async def polls_page(request: Request):
    return templates.TemplateResponse("polls.html", {"request": request})


@app.get("/create_poll_page")
async def create_poll_page(request: Request):
    return templates.TemplateResponse("create_poll.html", {"request": request})


@app.get("/users")
async def users_list_page(request: Request):
    try:
        return templates.TemplateResponse("users_list.html", {"request": request})
    except Exception as e:
        print(f"Error rendering users_list.html: {e}")
        raise


@app.get("/chat/{user_id}")
async def chat_page(request: Request, user_id: int):
    return templates.TemplateResponse("chat.html", {"request": request, "chat_partner_id": user_id})


if __name__ == "__main__":
    print("--- main.py: Starting Uvicorn server ---")
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
