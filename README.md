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
