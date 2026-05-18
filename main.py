"""
Taskinator - Simple Kanban Board for Task Management
"""
import os
from fastapi import FastAPI, Request, Depends, HTTPException, status, Form
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Enum, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from datetime import datetime
from typing import Optional, List
import enum
from passlib.context import CryptContext
from jose import JWTError, jwt
import aiosqlite
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.ext.asyncio import async_sessionmaker
import asyncio

# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

SECRET_KEY = os.getenv("SECRET_KEY", "taskinator-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440  # 24 hours

DATABASE_URL = "sqlite+aiosqlite:///./taskinator.db"

# ─────────────────────────────────────────────────────────────────────────────
# Database Setup
# ─────────────────────────────────────────────────────────────────────────────

Base = declarative_base()

class Priority(enum.Enum):
    LOW = "niedrig"
    MEDIUM = "mittel"
    HIGH = "hoch"

class Category(enum.Enum):
    FEATURE = "feature"
    FIX = "fix"
    HOTFIX = "hotfix"

class TaskStatus(enum.Enum):
    BACKLOG = "backlog"
    TODO = "todo"
    DOING = "doing"
    DONE = "done"

class Task(Base):
    __tablename__ = "tasks"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(256), nullable=False)
    description = Column(String(1024), nullable=True)
    priority = Column(Enum(Priority), default=Priority.MEDIUM)
    category = Column(Enum(Category), default=Category.FEATURE)
    project = Column(String(100), nullable=True)
    documentation = Column(Text, nullable=True)
    status = Column(Enum(TaskStatus), default=TaskStatus.BACKLOG)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)

class ChangeLog(Base):
    __tablename__ = "changelog"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    title = Column(String(256), nullable=False)
    description = Column(String(1024), nullable=True)
    pr_number = Column(Integer, nullable=True)
    pr_link = Column(String(512), nullable=True)
    test_results = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

engine = create_async_engine(DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession)

# ─────────────────────────────────────────────────────────────────────────────
# Authentication
# ─────────────────────────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    from datetime import timedelta
    from datetime import datetime as dt
    expire = dt.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        return username
    except JWTError:
        return None

# ─────────────────────────────────────────────────────────────────────────────
# FastAPI App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(title="Taskinator", description="Simple Kanban Board")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# ─────────────────────────────────────────────────────────────────────────────
# Routes
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    return RedirectResponse(url="/board")

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    async with async_session() as db:
        user = await db.execute(User.__table__.select().where(User.username == username))
        user = user.fetchone()
        
        if not user or not verify_password(password, user.password_hash):
            return templates.TemplateResponse("login.html", {
                "request": request,
                "error": "Invalid credentials"
            })
    
    access_token = create_access_token(data={"sub": username})
    response = RedirectResponse(url="/board", status_code=302)
    response.set_cookie(key="access_token", value=access_token, httponly=True)
    return response

@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("access_token")
    return response

@app.get("/board", response_class=HTMLResponse)
async def board(request: Request):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    async with async_session() as db:
        result = await db.execute(Task.__table__.select().order_by(Task.created_at.desc()))
        tasks = result.fetchall()
    
    columns = {
        "backlog": [],
        "todo": [],
        "doing": [],
        "done": []
    }
    
    for task in tasks:
        columns[task.status].append(dict(task))
    
    # Sort by priority
    priority_order = {Priority.HIGH: 0, Priority.MEDIUM: 1, Priority.LOW: 2}
    for col in columns.values():
        col.sort(key=lambda x: priority_order.get(x['priority'], 1))
    
    return templates.TemplateResponse("board.html", {
        "request": request,
        "columns": columns,
        "user": user,
        "Priority": Priority,
        "Category": Category
    })

@app.post("/tasks/create")
async def create_task(
    request: Request,
    title: str = Form(...),
    description: str = Form(None),
    priority: str = Form("mittel"),
    category: str = Form("feature"),
    project: str = Form(None)
):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    # Hotfix automatically gets high priority
    if category == "hotfix":
        priority = "hoch"
    
    priority_enum = Priority(priority)
    category_enum = Category(category)
    
    async with async_session() as db:
        await db.execute(Task.__table__.insert().values(
            title=title,
            description=description,
            priority=priority_enum,
            category=category_enum,
            project=project,
            status=TaskStatus.BACKLOG
        ))
        await db.commit()
    
    return RedirectResponse(url="/board", status_code=302)

@app.post("/tasks/{task_id}/move")
async def move_task(request: Request, task_id: int, direction: str = Form(...)):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    status_order = ["backlog", "todo", "doing", "done"]
    
    async with async_session() as db:
        result = await db.execute(Task.__table__.select().where(Task.id == task_id))
        task = result.fetchone()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        current_idx = status_order.index(task.status)
        
        if direction == "forward" and current_idx < len(status_order) - 1:
            new_status = status_order[current_idx + 1]
        elif direction == "backward" and current_idx > 0:
            new_status = status_order[current_idx - 1]
        else:
            return RedirectResponse(url="/board", status_code=302)
        
        await db.execute(Task.__table__.update()
            .where(Task.id == task_id)
            .values(status=new_status, updated_at=datetime.utcnow()))
        await db.commit()
    
    return RedirectResponse(url="/board", status_code=302)

@app.post("/tasks/{task_id}/delete")
async def delete_task(request: Request, task_id: int):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    async with async_session() as db:
        await db.execute(Task.__table__.delete().where(Task.id == task_id))
        await db.commit()
    
    return RedirectResponse(url="/board", status_code=302)

@app.post("/tasks/{task_id}/update")
async def update_task(
    request: Request,
    task_id: int,
    documentation: str = Form(None)
):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    async with async_session() as db:
        await db.execute(Task.__table__.update()
            .where(Task.id == task_id)
            .values(documentation=documentation, updated_at=datetime.utcnow()))
        await db.commit()
    
    return RedirectResponse(url="/board", status_code=302)

@app.get("/changelog", response_class=HTMLResponse)
async def changelog(request: Request, search: str = None):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    async with async_session() as db:
        query = ChangeLog.__table__.select().order_by(ChangeLog.created_at.desc())
        if search:
            query = query.where(
                (ChangeLog.title.ilike(f"%{search}%")) |
                (ChangeLog.id.cast(String).ilike(f"%{search}%"))
            )
        result = await db.execute(query)
        changes = result.fetchall()
    
    return templates.TemplateResponse("changelog.html", {
        "request": request,
        "changes": changes,
        "search": search,
        "user": user
    })

@app.post("/changelog/create")
async def create_changelog(
    request: Request,
    task_id: int = Form(...),
    title: str = Form(...),
    description: str = Form(None),
    pr_number: int = Form(None),
    pr_link: str = Form(None),
    test_results: str = Form(None)
):
    user = await get_current_user(request)
    if not user:
        return RedirectResponse(url="/login")
    
    async with async_session() as db:
        await db.execute(ChangeLog.__table__.insert().values(
            task_id=task_id,
            title=title,
            description=description,
            pr_number=pr_number,
            pr_link=pr_link,
            test_results=test_results
        ))
        await db.commit()
    
    return RedirectResponse(url="/changelog", status_code=302)

# ─────────────────────────────────────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create admin user if not exists
    async with async_session() as db:
        result = await db.execute(User.__table__.select().where(User.username == "admin"))
        admin = result.fetchone()
        
        if not admin:
            await db.execute(User.__table__.insert().values(
                username="admin",
                password_hash=get_password_hash("Y5zQ7hrQ75ERuLjDYHfX")
            ))
            await db.commit()
            print("✅ Admin user created")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9900)
