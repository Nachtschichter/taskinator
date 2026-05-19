"""Taskinator - Simple Kanban Board"""
import os
from fastapi import FastAPI, Request, Depends, Form
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Enum
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta
import enum
from passlib.context import CryptContext
from jose import JWTError, jwt

SECRET_KEY = os.getenv("SECRET_KEY", "taskinator-secret")
ALGORITHM = "HS256"
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:////app/data/taskinator.db")
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
    id = Column(Integer, primary_key=True)
    title = Column(String(256), nullable=False)
    description = Column(String(1024))
    priority = Column(Enum(Priority), default=Priority.MEDIUM)
    category = Column(Enum(Category), default=Category.FEATURE)
    project = Column(String(100))
    documentation = Column(Text)
    status = Column(Enum(TaskStatus), default=TaskStatus.BACKLOG)
    created_at = Column(DateTime, default=datetime.utcnow)

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True)
    password_hash = Column(String(256))

class ChangeLog(Base):
    __tablename__ = "changelog"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    title = Column(String(256))
    description = Column(String(1024))
    pr_number = Column(Integer)
    pr_link = Column(String(512))
    test_results = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain, hashed): return pwd_context.verify(plain, hashed)
def hash_password(pw): return pwd_context.hash(pw)
def create_token(data):
    exp = datetime.utcnow() + timedelta(minutes=1440)
    return jwt.encode({**data, "exp": exp}, SECRET_KEY, algorithm=ALGORITHM)

def get_user(request):
    token = request.cookies.get("access_token")
    if not token: return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except: return None

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Middleware für UTF-8 Content-Type
@app.middleware("http")
async def add_charset_header(request: Request, call_next):
    response = await call_next(request)
    if response.headers.get("content-type", "").startswith("text/html"):
        response.headers["content-type"] = "text/html; charset=utf-8"
    return response

@app.on_event("startup")
def startup():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    if not db.query(User).filter(User.username == "admin").first():
        db.add(User(username="admin", password_hash=hash_password("Taskinator2026!")))
        db.commit()
        print("✅ Admin created")
    db.close()

@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    if not get_user(request): return RedirectResponse("/login")
    return RedirectResponse("/board")

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...)):
    db = SessionLocal()
    user = db.query(User).filter(User.username == username).first()
    db.close()
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse("login.html", {"request": request, "error": "Invalid"})
    resp = RedirectResponse("/board", status_code=302)
    resp.set_cookie("access_token", create_token({"sub": username}), httponly=True)
    return resp

@app.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("access_token")
    return resp

@app.get("/board")
def board(request: Request):
    user = get_user(request)
    if not user: return RedirectResponse("/login")
    db = SessionLocal()
    tasks = db.query(Task).order_by(Task.created_at.desc()).all()
    db.close()
    cols = {"backlog": [], "todo": [], "doing": [], "done": []}
    for t in tasks:
        cols[t.status.value].append({'id': t.id, 'title': t.title, 'description': t.description or '', 'priority': t.priority.value, 
            'category': t.category.value, 'project': t.project, 'documentation': t.documentation})
    prio = {"hoch": 0, "mittel": 1, "niedrig": 2}
    for c in cols.values(): c.sort(key=lambda x: prio.get(x['priority'], 1))
    html_content = templates.get_template("board.html").render({"request": request, "columns": cols, "user": user})
    return Response(content=html_content, media_type="text/html; charset=utf-8")

@app.post("/tasks/create")
def create_task(request: Request, title: str = Form(...), description: str = Form(""), 
                priority: str = Form("mittel"), category: str = Form("feature"), project: str = Form("")):
    if not get_user(request): return RedirectResponse("/login")
    if category == "hotfix": priority = "hoch"
    db = SessionLocal()
    db.add(Task(title=title, description=description, priority=Priority(priority), 
                category=Category(category), project=project))
    db.commit()
    db.close()
    return RedirectResponse("/board", status_code=302)

@app.post("/tasks/{tid}/move")
def move_task(request: Request, tid: int, direction: str = Form(...)):
    if not get_user(request): return RedirectResponse("/login")
    db = SessionLocal()
    task = db.query(Task).filter(Task.id == tid).first()
    if task:
        order = ["backlog", "todo", "doing", "done"]
        idx = order.index(task.status.value)
        if direction == "forward" and idx < 3: task.status = TaskStatus(order[idx+1])
        elif direction == "backward" and idx > 0: task.status = TaskStatus(order[idx-1])
        db.commit()
    db.close()
    return RedirectResponse("/board", status_code=302)

@app.post("/tasks/{tid}/delete")
def delete_task(request: Request, tid: int):
    if not get_user(request): return RedirectResponse("/login")
    db = SessionLocal()
    db.query(Task).filter(Task.id == tid).delete()
    db.commit()
    db.close()
    return RedirectResponse("/board", status_code=302)

@app.post("/tasks/{tid}/update")
def update_task(request: Request, tid: int, documentation: str = Form("")):
    if not get_user(request): return RedirectResponse("/login")
    db = SessionLocal()
    db.query(Task).filter(Task.id == tid).update({"documentation": documentation})
    db.commit()
    db.close()
    return RedirectResponse("/board", status_code=302)

@app.post("/tasks/update-details")
def update_task_details(request: Request, task_id: int = Form(...), title: str = Form(...), 
                        description: str = Form(""), priority: str = Form("mittel"), 
                        category: str = Form("feature"), project: str = Form("")):
    if not get_user(request): return RedirectResponse("/login")
    if category == "hotfix": priority = "hoch"
    db = SessionLocal()
    db.query(Task).filter(Task.id == task_id).update({
        "title": title,
        "description": description,
        "priority": Priority(priority),
        "category": Category(category),
        "project": project
    })
    db.commit()
    db.close()
    return RedirectResponse("/board", status_code=302)

@app.get("/changelog")
def changelog(request: Request, search: str = ""):
    if not get_user(request): return RedirectResponse("/login")
    db = SessionLocal()
    q = db.query(ChangeLog).order_by(ChangeLog.created_at.desc())
    if search: q = q.filter((ChangeLog.title.ilike(f"%{search}%")) | (ChangeLog.id.cast(String).ilike(f"%{search}%")))
    changes = q.all()
    db.close()
    html_content = templates.get_template("changelog.html").render({"request": request, "changes": changes, "search": search, "user": get_user(request)})
    return Response(content=html_content, media_type="text/html; charset=utf-8")

@app.post("/changelog/create")
def create_changelog(request: Request, task_id: int = Form(...), title: str = Form(...), 
                     description: str = Form(""), pr_number: int = Form(None), pr_link: str = Form(""), test_results: str = Form("")):
    if not get_user(request): return RedirectResponse("/login")
    db = SessionLocal()
    db.add(ChangeLog(task_id=task_id, title=title, description=description, pr_number=pr_number, pr_link=pr_link, test_results=test_results))
    db.commit()
    db.close()
    return RedirectResponse("/changelog", status_code=302)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=9900)
