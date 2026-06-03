# Security & Flexibility Refactor — QA Verification Guide

**Branch:** `feature/security-url-refactor`  
**PR:** https://github.com/Nachtschichter/taskinator/pull/35  
**Date:** 2026-06-03

---

## 1. Objective

Implement a centralized, environment-driven configuration system and upgrade password hashing to Argon2id, while ensuring **no hardcoded URLs or plaintext secrets** remain in the codebase.

---

## 2. What Changed

### 2.1 Dynamic URL Construction (`backend/config.py`)

| Env Var | Default | Purpose |
|---------|---------|---------|
| `PROTOCOL` | `http` | URL scheme |
| `HOST` | `0.0.0.0` | Bind / advertised host |
| `PORT` | `9900` | Bind / advertised port |

- `Config.base_url` is assembled as `f"{PROTOCOL}://{HOST}:{PORT}"`.
- `main.py` now imports `config` and uses `config.HOST` / `config.PORT` for `uvicorn.run(...)`.
- `docker-compose.yml` healthcheck reads these variables instead of a hardcoded `http://localhost:9900/login`.

### 2.2 Password Hashing Upgrade (`backend/security.py`)

```python
pwd_context = CryptContext(
    schemes=["argon2", "bcrypt"],
    deprecated=["bcrypt"],
    argon2__type="ID",
    ...
)
```

- **Primary:** Argon2id (modern memory-hard password hashing).
- **Fallback:** bcrypt (existing hashes in the database remain valid).
- **Impact:** All new passwords are hashed with Argon2id. Old bcrypt hashes verify transparently.

### 2.3 Shared Security Module

All password operations now import from `backend/security.py`:
- `backend/main.py` — login, user creation, setup-admin
- `change_password.py`
- `change_admin_password.py`

This guarantees a single source of truth for hashing and validation.

### 2.4 Hardcoded URL Removals

| File | Before | After |
|------|--------|-------|
| `docker-compose.yml` | `http://localhost:9900/login` | `f"{proto}://{host}:{port}/login"` |
| `.github/workflows/ci.yml` | `http://localhost:9900/login` | `${TEST_BASE_URL:-http://localhost:9900}/login` |
| `e2e-tests/test_api_status.py` | `BASE_URL = "http://localhost:9900"` | `os.getenv("TEST_BASE_URL", "http://localhost:9900")` |
| `e2e-tests/test_status_dropdown.py` | `BASE_URL = "http://localhost:9900"` | `os.getenv("TEST_BASE_URL", "http://localhost:9900")` |
| `change_password.py` | `DB_PATH = "/home/storagebox/.../taskinator.db"` | `config.DATABASE_URL` |
| `change_admin_password.py` | `DB_PATH = "/app/data/taskinator.db"` | `config.DATABASE_URL` |

### 2.5 Secret Protection

- `.gitignore` added to exclude `.env`, `.env.local`, `.env.production`.
- `config.validate()` enforces at startup:
  - `SECRET_KEY` must be set and **not** the default placeholder.
  - `ADMIN_PASSWORD` (if provided) must be ≥ 8 characters.

---

## 3. QA Checklist

### 3.1 Absence of Plain-Text Secrets

Run these commands inside the repo root on `feature/security-url-refactor`:

```bash
# 1. Ensure .env is NOT tracked
git ls-files | grep -E "\.env" || echo "PASS: No .env files tracked"

# 2. No hardcoded SECRET_KEY values in Python files
grep -rn "taskinator-production-secret-key" backend/ || echo "PASS: Default secret removed"

# 3. No plaintext passwords in source
grep -rn "ADMIN_PASSWORD\s*=" --include="*.py" | grep -v "os.getenv\|config.ADMIN_PASSWORD" || echo "PASS: No plaintext admin passwords"
```

### 3.2 Absence of Hardcoded Internal URLs

```bash
# Should return ONLY external CDN URLs (cdn.jsdelivr.net, etc.)
grep -rn "http://\|https://" --include="*.py" --include="*.yml" --include="*.yaml" | grep -v "cdn.jsdelivr\|bootstrap-icons\|admin-lte\|alpinejs\|sortablejs\|registry.npmjs\|react.dev"
```

Expected: **empty** (or only matches in `e2e-tests/results/` which are generated artifacts).

### 3.3 Functional Tests

1. **Start the application** with a valid `.env`:
   ```bash
   cp .env.example .env
   # Edit .env: set a real SECRET_KEY and ADMIN_PASSWORD
   docker compose up --build -d
   ```

2. **Verify healthcheck uses dynamic URL**:
   ```bash
   docker compose ps
   # Container should show healthy status
   ```

3. **Login** with the admin user created from `ADMIN_PASSWORD`.

4. **Create a new user** via Admin → Users. Inspect the `password_hash` in the DB:
   ```sql
   SELECT password_hash FROM users ORDER BY id DESC LIMIT 1;
   ```
   It should start with `$argon2id$` (not `$2b$`).

5. **Test existing bcrypt hash compatibility**:
   - If you have an old database with bcrypt hashes, attempt login. It must still work (passlib fallback).

6. **Run password change scripts**:
   ```bash
   python change_password.py admin MyNewStrongPass123!
   python change_admin_password.py AnotherStrongPass456!
   ```
   Both should succeed and store Argon2id hashes.

### 3.4 CI / E2E Verification

```bash
# Export base URL if testing on a non-default host/port
export TEST_BASE_URL=http://localhost:9900
cd e2e-tests && docker compose up --build
```

---

## 4. Files Modified

- `backend/config.py` *(new)*
- `backend/security.py` *(new)*
- `backend/main.py`
- `backend/requirements.txt`
- `docker-compose.yml`
- `.env.example`
- `.gitignore` *(new)*
- `.github/workflows/ci.yml`
- `e2e-tests/docker-compose.yml`
- `e2e-tests/test_api_status.py`
- `e2e-tests/test_status_dropdown.py`
- `change_password.py`
- `change_admin_password.py`

---

## 5. Sign-Off

| Role | Name | Date | Result |
|------|------|------|--------|
| Developer | Clawsy | 2026-06-03 | ✅ Changes implemented |
| QA | — | — | ⬜ Pending verification |
| DevOps | — | — | ⬜ Pending merge & deploy |

---

*End of QA verification guide.*
