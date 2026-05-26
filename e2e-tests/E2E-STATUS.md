# E2E Test-Status

## Playwright Container-Setup

### Konfiguration (docker-compose.yml)
```yaml
services:
  playwright:
    build: .
    volumes:
      - ./results:/app/results
    environment:
      - TEST_BASE_URL=http://host.docker.internal:9900
      - ADMIN_PASSWORD=${ADMIN_PASSWORD}
    network_mode: host
```

### Dockerfile
```dockerfile
FROM mcr.microsoft.com/playwright:v1.50.0-jammy
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
CMD ["npx", "playwright", "test"]
```

### Test-Dateien
- `01-auth.spec.ts` - Login/Logout Tests
- `02-board.spec.ts` - Board-Anzeige (enthält Drag-and-Drop Test-Stub)
- `03-task-detail.spec.ts` - Task-Detail Seite

## Aktueller Stand
- Container-Image definiert ✅
- Tests vorhanden ✅
- Playwright-Image verfügbar ✅

## Nächste Schritte
1. Docker-Build ausführen
2. Container starten
3. Test-Report prüfen
