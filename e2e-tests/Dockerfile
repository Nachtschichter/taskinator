FROM mcr.microsoft.com/playwright:v1.50.0-jammy

WORKDIR /app

COPY package*.json ./
RUN npm ci && npx playwright install chromium

COPY . .

CMD ["node", "node_modules/@playwright/test/cli.js", "test"]
