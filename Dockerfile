FROM python:3.11-slim

WORKDIR /app

# Set PYTHONPATH to ensure modules are found
ENV PYTHONPATH=/app

# Install dependencies
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port
EXPOSE 9900

CMD ["python", "backend/main.py"]
