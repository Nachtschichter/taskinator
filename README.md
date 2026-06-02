# 🦀 Taskinator

Simple Kanban Board for Task Management.

## Features

- **4-Column Kanban Board**: Backlog → Todo → Doing → Done
- **Authentication**: Secure login system
- **Task Management**: Create, move, delete tasks
- **Priority System**: High, Medium, Low (Hotfix = High automatically)
- **Categories**: Feature, Fix, Hotfix
- **Documentation**: Add PR links and test results to tasks
- **Changelog**: Track all completed changes with search

## Quick Start

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run application
python main.py

# Open browser
http://localhost:9900
```

### Docker

```bash
# Build and run
docker compose up -d --build

# Open browser
http://localhost:9900
```

## Default Credentials

- **Username:** admin
- **Password:** Y5zQ7hrQ75ERuLjDYHfX

## Documentation

### PR Links in Tasks

When completing a task, add the PR link to the task documentation:

1. Move task to **Done**
2. Click the task to open details
3. Add PR link in the documentation field
4. Format: `https://github.com/<user>/<repo>/pull/<number>`
5. The PR link becomes part of the task's permanent documentation
6. This link will appear in the changelog for traceability

**Example:**
```
PR: https://github.com/micbit/taskinator/pull/42
Tested: ✅ Passed on staging
```

## Public Access

The application is publicly accessible at:

- **Production:** http://91.99.5.26:9900
- **Database Location:** `/root/storagebox/databases/taskinator`

### Security Notes

- Change the default credentials immediately
- Use HTTPS in production (reverse proxy recommended)
- Keep `SECRET_KEY` secure and unique

## Workflow

1. Create task in **Backlog**
2. Move to **Todo** when ready to work
3. Move to **Doing** when working on it
4. Move to **Done** when completed
5. Add documentation (PR link, test results)
6. Create changelog entry

## Tech Stack

- **Backend:** FastAPI (Python)
- **Database:** SQLite (Async)
- **Auth:** JWT + bcrypt
- **Frontend:** Jinja2 Templates + Vanilla JS

## License

MIT
 
