from contextlib import asynccontextmanager
import os
import json
import secrets
from fastapi import FastAPI, Request, Depends, Form, Query, HTTPException, status
from fastapi.responses import HTMLResponse, RedirectResponse, Response, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, Enum, text, Boolean
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timedelta, timezone
import enum
from jose import JWTError, jwt

import re

# --- Centralized Configuration ---
from backend.config import config
from backend.security import hash_password, verify_password, validate_password_strength

config.validate()

SECRET_KEY = config.SECRET_KEY
ALGORITHM = config.ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = config.ACCESS_TOKEN_EXPIRE_MINUTES
DATABASE_URL = config.DATABASE_URL

# Ensure data directory exists for SQLite
if DATABASE_URL.startswith('sqlite'):
    db_path = DATABASE_URL.replace('sqlite:///', '').replace('sqlite://', '')
    if db_path and not db_path.startswith('/'):
        db_path = os.path.join(os.getcwd(), db_path)
    if db_path:
        data_dir = os.path.dirname(db_path)
        if data_dir and not os.path.exists(data_dir):
            os.makedirs(data_dir, exist_ok=True)
            print(f"✅ Created data directory: {data_dir}")

Base = declarative_base()

# --- Enums ---
class Priority(enum.Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"

class Category(enum.Enum):
    FEATURE = "feature"
    FIX = "fix"
    HOTFIX = "hotfix"

class TaskStatus(enum.Enum):
    BACKLOG = "BACKLOG"
    TODO = "TODO"
    DOING = "DOING"
    DONE = "DONE"

class UserRole(enum.Enum):
    ADMIN = "admin"
    MEMBER = "member"

# --- Models ---
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
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(100), unique=True)
    password_hash = Column(String(256))
    role = Column(Enum(UserRole), default=UserRole.MEMBER, nullable=False)
    is_active = Column(Boolean, default=True)

class ChangeLog(Base):
    __tablename__ = "changelog"
    id = Column(Integer, primary_key=True)
    task_id = Column(Integer, ForeignKey("tasks.id"))
    title = Column(String(256))
    description = Column(String(1024))
    pr_number = Column(Integer)
    pr_link = Column(String(512))
    test_results = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class Project(Base):
    __tablename__ = "projects"
    id = Column(Integer, primary_key=True)
    name = Column(String(100), unique=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

# --- Auth Helpers ---

def create_token(data: dict) -> str:
    to_encode = data.copy()
    exp = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    to_encode.update({"exp": exp})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

def get_user(request: Request):
    token = request.cookies.get("access_token")
    if not token:
        return None
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username = payload.get("sub")
        if not username:
            return None
        db = SessionLocal()
        try:
            db_user = db.query(User).filter(User.username == username).first()
            if not db_user or not db_user.is_active:
                return None
            return username
        finally:
            db.close()
    except JWTError:
        return None

def get_current_user(request: Request = Depends()):
    user = get_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user

def require_admin(request: Request):
    user = get_user(request)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    db = SessionLocal()
    try:
        db_user = db.query(User).filter(User.username == user).first()
        if not db_user or db_user.role != UserRole.ADMIN:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    finally:
        db.close()
    return user

# --- CSRF Helpers ---
CSRF_COOKIE_NAME = "csrf_token"

def generate_csrf_token() -> str:
    return secrets.token_urlsafe(32)

def _check_csrf(request: Request, form_csrf: str = ""):
    cookie_token = request.cookies.get(CSRF_COOKIE_NAME, "")
    header_token = request.headers.get("X-CSRF-Token", "")
    provided = header_token or form_csrf
    if not provided or not secrets.compare_digest(provided, cookie_token):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="CSRF token missing or invalid")

# --- Removed: duplicate validate_password_strength; imported from backend.security ---

def validate_task_enums(priority: str, category: str):
    if priority not in ("LOW", "MEDIUM", "HIGH"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid priority")
    if category not in ("feature", "fix", "hotfix"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid category")

# --- Lifespan ---
@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    print("✅ Database initialized")

    admin_password = config.ADMIN_PASSWORD
    if admin_password:
        if len(admin_password) < 8:
            print("⚠️ ADMIN_PASSWORD is too short (min 8 characters). Admin user will not be auto-created.")
        else:
            db = SessionLocal()
            try:
                admin = db.query(User).filter(User.username == "admin").first()
                if not admin:
                    admin = User(
                        username="admin",
                        password_hash=hash_password(admin_password),
                        role=UserRole.ADMIN,
                        is_active=True
                    )
                    db.add(admin)
                    db.commit()
                    print("✅ Admin user created")
                else:
                    print("✅ Admin user already exists")

                task_count = db.query(Task).count()
                if task_count == 0:
                    sample_tasks = [
                        Task(title="Test Task 1", description="Sample task for testing", project="Test", status=TaskStatus.TODO),
                        Task(title="Test Task 2", description="Another sample task", project="Test", status=TaskStatus.DOING),
                        Task(title="Test Task 3", description="Completed task", project="Test", status=TaskStatus.DONE),
                    ]
                    for task in sample_tasks:
                        db.add(task)
                    db.commit()
                    print("✅ Sample tasks created")
                else:
                    print(f"✅ {task_count} tasks already exist")
            except Exception as e:
                print(f"❌ Error: {e}")
                db.rollback()
            finally:
                db.close()
    else:
        print("⚠️ No ADMIN_PASSWORD set. Admin user will not be auto-created.")

    yield

# --- App Setup ---
app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
# FIX 2: Serve new AdminLTE 4 templates from frontend/templates/
templates = Jinja2Templates(directory="frontend/templates")

@app.middleware("http")
async def add_charset_header(request: Request, call_next):
    response = await call_next(request)
    content_type = response.headers.get("content-type", "")
    if not content_type or content_type.startswith("text/html"):
        response.headers["content-type"] = "text/html; charset=utf-8"
    return response

# --- Helper: Response with CSRF cookie ---
COOKIE_SECURE = config.COOKIE_SECURE

def set_access_token_cookie(resp: Response, token: str):
    resp.set_cookie("access_token", token, httponly=True, samesite="lax", secure=COOKIE_SECURE)

def set_csrf_cookie(resp: Response, token: str):
    resp.set_cookie(CSRF_COOKIE_NAME, token, httponly=False, samesite="lax", secure=COOKIE_SECURE)

def sanitize_hex_color(color: str) -> str:
    color = color.strip()
    if re.fullmatch(r'#[0-9a-fA-F]{6}', color):
        return color
    return "#667eea"

def html_response_with_csrf(request: Request, template_name: str, context: dict, status_code: int = 200):
    csrf_val = request.cookies.get(CSRF_COOKIE_NAME, "")
    if not csrf_val:
        csrf_val = generate_csrf_token()
    # is_admin can be provided by caller (e.g. board page) to avoid extra DB query
    is_admin = context.pop("is_admin", None)
    if is_admin is None:
        user = get_user(request)
        is_admin = False
        if user:
            db = SessionLocal()
            try:
                db_user = db.query(User).filter(User.username == user).first()
                is_admin = db_user.role == UserRole.ADMIN if db_user else False
            finally:
                db.close()
    # Ensure csrf_token from context cannot override the real cookie token
    ctx = {"request": request, "is_admin": is_admin, **context, "csrf_token": csrf_val}
    html_content = templates.get_template(template_name).render(ctx)
    resp = Response(content=html_content, media_type="text/html; charset=utf-8", status_code=status_code)
    if not request.cookies.get(CSRF_COOKIE_NAME):
        set_csrf_cookie(resp, csrf_val)
    return resp

# --- Routes ---
@app.get("/", response_class=HTMLResponse)
def root(request: Request):
    if not get_user(request):
        return RedirectResponse("/login")
    return RedirectResponse("/board")

@app.get("/login")
def login_page(request: Request):
    return html_response_with_csrf(request, "pages/login.html", {})

@app.post("/login")
def login(request: Request, username: str = Form(...), password: str = Form(...), csrf_token: str = Form("")):
    _check_csrf(request, csrf_token)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.username == username).first()
        if not user or not verify_password(password, user.password_hash) or not user.is_active:
            return html_response_with_csrf(request, "pages/login.html", {"error": "Invalid credentials or account inactive"}, status_code=401)
        resp = RedirectResponse("/board", status_code=302)
        set_access_token_cookie(resp, create_token({"sub": username}))
        set_csrf_cookie(resp, generate_csrf_token())
        return resp
    finally:
        db.close()

@app.get("/logout")
def logout():
    resp = RedirectResponse("/login", status_code=302)
    resp.delete_cookie("access_token")
    resp.delete_cookie(CSRF_COOKIE_NAME)
    return resp

@app.get("/board")
def board(request: Request):
    user = get_user(request)
    if not user:
        return RedirectResponse("/login")
    db = SessionLocal()
    try:
        tasks = db.query(Task).order_by(Task.created_at.desc()).all()
        projects = db.query(Project).order_by(Project.name).all()
        cols = {"BACKLOG": [], "TODO": [], "DOING": [], "DONE": []}
        for t in tasks:
            cols[t.status.value].append({
                'id': t.id, 'title': t.title, 'description': t.description or '',
                'priority': t.priority.value, 'category': t.category.value,
                'status': t.status.value, 'project': t.project, 'documentation': t.documentation
            })
        prio = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
        for c in cols.values():
            c.sort(key=lambda x: prio.get(x['priority'], 1))

        return html_response_with_csrf(
            request, "pages/board.html",
            {"columns": cols, "user": user, "projects": projects}
        )
    finally:
        db.close()

@app.post("/tasks/create")
def create_task(request: Request, title: str = Form(...), description: str = Form(""),
                priority: str = Form("MEDIUM"), category: str = Form("feature"), project: str = Form(""),
                csrf_token: str = Form("")):
    if not get_user(request):
        return RedirectResponse("/login")
    _check_csrf(request, csrf_token)
    validate_task_enums(priority, category)
    if category == "hotfix":
        priority = "HIGH"
    db = SessionLocal()
    try:
        db.add(Task(title=title, description=description, priority=Priority(priority),
                    category=Category(category), project=project))
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/board", status_code=302)

@app.post("/tasks/{tid}/move")
async def move_task(request: Request, tid: int, ajax: str = Query(""), csrf_token: str = Form("")):
    if not get_user(request):
        if ajax:
            return JSONResponse({"success": False, "error": "Unauthorized"}, status_code=401)
        return RedirectResponse("/login")
    _check_csrf(request, csrf_token)
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == tid).first()
        if not task:
            if ajax:
                return JSONResponse({"success": False, "error": "Task not found"}, status_code=404)
            return RedirectResponse("/board", status_code=302)

        form_data = await request.form()
        direction = form_data.get("direction", "")
        status_val = form_data.get("status", "")

        order = ["BACKLOG", "TODO", "DOING", "DONE"]
        try:
            current_idx = order.index(task.status.value)
        except ValueError:
            if ajax:
                return JSONResponse({"success": False, "error": "Invalid status"}, status_code=400)
            return RedirectResponse("/board", status_code=302)

        try:
            if task.status.value.lower() == 'done' and status_val and status_val != 'done':
                if ajax:
                    return JSONResponse({"success": False, "error": "Tasks in DONE cannot be moved back"}, status_code=403)
                return RedirectResponse("/board", status_code=302)

            if status_val:
                if status_val not in order:
                    if ajax:
                        return JSONResponse({"success": False, "error": "Invalid status"}, status_code=400)
                    return RedirectResponse("/board", status_code=302)
                task.status = TaskStatus(status_val)
            elif direction:
                if direction == "forward" and current_idx < 3:
                    task.status = TaskStatus(order[current_idx+1])
                elif direction == "backward" and current_idx > 0:
                    task.status = TaskStatus(order[current_idx-1])

            db.commit()
            if ajax:
                return JSONResponse({"success": True, "status": task.status.value})
        except Exception as e:
            db.rollback()
            if ajax:
                return JSONResponse({"success": False, "error": "Database error"}, status_code=500)
            raise
    finally:
        db.close()
    return RedirectResponse("/board", status_code=302)

@app.post("/tasks/{tid}/delete")
def delete_task(request: Request, tid: int, csrf_token: str = Form("")):
    if not get_user(request):
        return RedirectResponse("/login")
    _check_csrf(request, csrf_token)
    db = SessionLocal()
    try:
        db.query(Task).filter(Task.id == tid).delete()
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/board", status_code=302)

@app.post("/tasks/{tid}/update")
def update_task(request: Request, tid: int, documentation: str = Form(""), csrf_token: str = Form("")):
    if not get_user(request):
        return RedirectResponse("/login")
    _check_csrf(request, csrf_token)
    db = SessionLocal()
    try:
        db.query(Task).filter(Task.id == tid).update({"documentation": documentation})
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/board", status_code=302)

@app.get("/tasks/{tid}/edit-form")
def edit_task_form(request: Request, tid: int):
    if not get_user(request):
        return RedirectResponse("/login")
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == tid).first()
        if not task:
            return Response(content="Task not found", status_code=404, media_type="text/plain")
        return html_response_with_csrf(
            request, "pages/edit_task.html",
            {"task": task}
        )
    finally:
        db.close()

@app.post("/tasks/update-details")
def update_task_details(request: Request, task_id: int = Form(...), title: str = Form(...),
                        description: str = Form(""), priority: str = Form("MEDIUM"),
                        category: str = Form("feature"), project: str = Form(""),
                        csrf_token: str = Form("")):
    if not get_user(request):
        return RedirectResponse("/login")
    _check_csrf(request, csrf_token)
    validate_task_enums(priority, category)
    if category == "hotfix":
        priority = "HIGH"
    db = SessionLocal()
    try:
        db.query(Task).filter(Task.id == task_id).update({
            "title": title, "description": description,
            "priority": Priority(priority), "category": Category(category), "project": project
        })
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/board", status_code=302)

@app.get("/changelog")
def changelog(request: Request, search: str = ""):
    if not get_user(request):
        return RedirectResponse("/login")
    db = SessionLocal()
    try:
        q = db.query(ChangeLog).order_by(ChangeLog.created_at.desc())
        if search:
            safe_search = search.replace("%", "\\%").replace("_", "\\_")
            q = q.filter((ChangeLog.title.ilike(f"%{safe_search}%")) | (ChangeLog.id.cast(String).ilike(f"%{safe_search}%")))
        changes = q.all()
        return html_response_with_csrf(
            request, "pages/changelog.html",
            {"changes": changes, "search": search, "user": get_user(request)}
        )
    finally:
        db.close()

@app.post("/changelog/create")
def create_changelog(request: Request, task_id: int = Form(...), title: str = Form(...),
                     description: str = Form(""), pr_number: int = Form(None),
                     pr_link: str = Form(""), test_results: str = Form(""),
                     csrf_token: str = Form("")):
    if not get_user(request):
        return RedirectResponse("/login")
    _check_csrf(request, csrf_token)
    db = SessionLocal()
    try:
        db.add(ChangeLog(task_id=task_id, title=title, description=description,
                         pr_number=pr_number, pr_link=pr_link, test_results=test_results))
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/changelog", status_code=302)

# --- Admin Routes (RBAC: require_admin dependency) ---
@app.get("/admin/projects")
def admin_projects(request: Request):
    admin_user = require_admin(request)
    db = SessionLocal()
    try:
        projects = db.query(Project).order_by(Project.name).all()
        return html_response_with_csrf(request, "pages/admin_projects.html", {"projects": projects, "user": admin_user})
    finally:
        db.close()

@app.post("/admin/projects/create")
def admin_create_project(request: Request, name: str = Form(...), csrf_token: str = Form("")):
    admin_user = require_admin(request)
    _check_csrf(request, csrf_token)
    db = SessionLocal()
    try:
        existing = db.query(Project).filter(Project.name == name).first()
        if not existing and name.strip():
            db.add(Project(name=name.strip()))
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/admin/projects", status_code=302)

@app.post("/admin/projects/{pid}/delete")
def admin_delete_project(request: Request, pid: int, csrf_token: str = Form("")):
    admin_user = require_admin(request)
    _check_csrf(request, csrf_token)
    db = SessionLocal()
    try:
        db.query(Project).filter(Project.id == pid).delete()
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/admin/projects", status_code=302)

# --- User Management (Admin Only) ---
@app.get("/admin/users")
def admin_users(request: Request):
    admin_user = require_admin(request)
    db = SessionLocal()
    try:
        users = db.query(User).order_by(User.username).all()
        return html_response_with_csrf(request, "pages/admin_users.html", {"users": users, "user": admin_user})
    finally:
        db.close()

@app.post("/admin/users/create")
def admin_create_user(request: Request, username: str = Form(...), password: str = Form(...),
                      role: str = Form("member"), csrf_token: str = Form("")):
    admin_user = require_admin(request)
    _check_csrf(request, csrf_token)
    if not validate_password_strength(password):
        db = SessionLocal()
        try:
            users = db.query(User).order_by(User.username).all()
            return html_response_with_csrf(request, "pages/admin_users.html", {"error": "Password must be at least 8 characters", "users": users})
        finally:
            db.close()
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.username == username).first()
        if existing:
            return html_response_with_csrf(request, "pages/admin_users.html", {"error": "User already exists", "users": db.query(User).order_by(User.username).all()})
        db.add(User(username=username, password_hash=hash_password(password),
                    role=UserRole(role) if role in ("admin", "member") else UserRole.MEMBER, is_active=True))
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/admin/users", status_code=302)

@app.post("/admin/users/{uid}/toggle")
def admin_toggle_user(request: Request, uid: int, csrf_token: str = Form("")):
    admin_user = require_admin(request)
    _check_csrf(request, csrf_token)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == uid).first()
        if user:
            if user.username == admin_user:
                return html_response_with_csrf(request, "pages/admin_users.html", {"error": "You cannot deactivate your own account", "users": db.query(User).order_by(User.username).all()})
            user.is_active = not user.is_active
            db.commit()
    finally:
        db.close()
    return RedirectResponse("/admin/users", status_code=302)

@app.post("/admin/users/{uid}/delete")
def admin_delete_user(request: Request, uid: int, csrf_token: str = Form("")):
    admin_user = require_admin(request)
    _check_csrf(request, csrf_token)
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.id == uid).first()
        if user and user.username == admin_user:
            return html_response_with_csrf(request, "pages/admin_users.html", {"error": "You cannot delete your own account", "users": db.query(User).order_by(User.username).all()})
        db.query(User).filter(User.id == uid).delete()
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/admin/users", status_code=302)

# --- Settings: Priorities & Task Types (Admin Only) ---
class PrioritySetting(Base):
    __tablename__ = "priority_settings"
    id = Column(Integer, primary_key=True)
    label = Column(String(50), unique=True, nullable=False)
    color = Column(String(7))
    sort_order = Column(Integer, default=0)

class TaskTypeSetting(Base):
    __tablename__ = "task_type_settings"
    id = Column(Integer, primary_key=True)
    label = Column(String(50), unique=True, nullable=False)
    color = Column(String(7))

@app.get("/admin/settings/priorities")
def admin_priorities(request: Request):
    admin_user = require_admin(request)
    db = SessionLocal()
    try:
        priorities = db.query(PrioritySetting).order_by(PrioritySetting.sort_order).all()
        return html_response_with_csrf(request, "pages/admin_priorities.html", {"priorities": priorities, "user": admin_user})
    finally:
        db.close()

@app.post("/admin/settings/priorities/create")
def admin_create_priority(request: Request, label: str = Form(...), color: str = Form("#667eea"),
                            sort_order: int = Form(0), csrf_token: str = Form("")):
    admin_user = require_admin(request)
    _check_csrf(request, csrf_token)
    db = SessionLocal()
    try:
        db.add(PrioritySetting(label=label.strip(), color=sanitize_hex_color(color), sort_order=sort_order))
        db.commit()
    except IntegrityError:
        db.rollback()
        return html_response_with_csrf(request, "pages/admin_priorities.html", {"error": "Priority label already exists", "priorities": db.query(PrioritySetting).order_by(PrioritySetting.sort_order).all()})
    finally:
        db.close()
    return RedirectResponse("/admin/settings/priorities", status_code=302)

@app.post("/admin/settings/priorities/{pid}/delete")
def admin_delete_priority(request: Request, pid: int, csrf_token: str = Form("")):
    admin_user = require_admin(request)
    _check_csrf(request, csrf_token)
    db = SessionLocal()
    try:
        db.query(PrioritySetting).filter(PrioritySetting.id == pid).delete()
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/admin/settings/priorities", status_code=302)

@app.get("/admin/settings/types")
def admin_types(request: Request):
    admin_user = require_admin(request)
    db = SessionLocal()
    try:
        types = db.query(TaskTypeSetting).order_by(TaskTypeSetting.label).all()
        return html_response_with_csrf(request, "pages/admin_types.html", {"types": types, "user": admin_user})
    finally:
        db.close()

@app.post("/admin/settings/types/create")
def admin_create_type(request: Request, label: str = Form(...), color: str = Form("#667eea"),
                        csrf_token: str = Form("")):
    admin_user = require_admin(request)
    _check_csrf(request, csrf_token)
    db = SessionLocal()
    try:
        db.add(TaskTypeSetting(label=label.strip(), color=sanitize_hex_color(color)))
        db.commit()
    except IntegrityError:
        db.rollback()
        return html_response_with_csrf(request, "pages/admin_types.html", {"error": "Type label already exists", "types": db.query(TaskTypeSetting).order_by(TaskTypeSetting.label).all()})
    finally:
        db.close()
    return RedirectResponse("/admin/settings/types", status_code=302)

@app.post("/admin/settings/types/{tid}/delete")
def admin_delete_type(request: Request, tid: int, csrf_token: str = Form("")):
    admin_user = require_admin(request)
    _check_csrf(request, csrf_token)
    db = SessionLocal()
    try:
        db.query(TaskTypeSetting).filter(TaskTypeSetting.id == tid).delete()
        db.commit()
    finally:
        db.close()
    return RedirectResponse("/admin/settings/types", status_code=302)

# --- Task Detail Page ---
@app.get("/tasks/{tid}")
def task_detail(request: Request, tid: int):
    if not get_user(request):
        return RedirectResponse("/login")
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == tid).first()
        if not task:
            return Response(content="Task not found", status_code=404, media_type="text/plain")
        changelog_entries = db.query(ChangeLog).filter(ChangeLog.task_id == tid).order_by(ChangeLog.created_at.desc()).all()

        if task.documentation is None:
            task.documentation = ""

        return html_response_with_csrf(
            request, "pages/task_detail.html",
            {"task": task, "changelog": changelog_entries, "user": get_user(request)}
        )
    finally:
        db.close()

# --- API Routes (JSON) ---
@app.get("/api/tasks")
def api_list_tasks(request: Request):
    if not get_user(request):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    db = SessionLocal()
    try:
        tasks = db.query(Task).order_by(Task.id).all()
        result = []
        for t in tasks:
            result.append({
                "id": t.id, "title": t.title, "description": t.description or "",
                "status": t.status.value, "priority": t.priority.value,
                "category": t.category.value, "project": t.project or "",
                "documentation": t.documentation or "",
                "created_at": t.created_at.isoformat() if t.created_at else None
            })
        return JSONResponse(result)
    finally:
        db.close()

# --- First-Run Admin Setup ---
@app.get("/setup-admin")
def setup_admin_page(request: Request):
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count > 0:
            return RedirectResponse("/login")
    finally:
        db.close()
    return html_response_with_csrf(request, "pages/setup_admin.html", {})

@app.post("/setup-admin")
def setup_admin(request: Request, username: str = Form(...), password: str = Form(...), csrf_token: str = Form("")):
    _check_csrf(request, csrf_token)
    if not validate_password_strength(password):
        return html_response_with_csrf(request, "pages/setup_admin.html", {"error": "Password must be at least 8 characters"})
    db = SessionLocal()
    try:
        user_count = db.query(User).count()
        if user_count > 0:
            return RedirectResponse("/login")
        db.add(User(username=username, password_hash=hash_password(password), role=UserRole.ADMIN, is_active=True))
        db.commit()
    except Exception:
        db.rollback()
        return RedirectResponse("/login", status_code=302)
    finally:
        db.close()
    return RedirectResponse("/login", status_code=302)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host=config.HOST, port=config.PORT)
