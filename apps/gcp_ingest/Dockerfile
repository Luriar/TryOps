# Use Python 3.11 slim image
FROM python:3.11-slim-bookworm

# Prevent Python from writing pyc files to disc and buffering stdout
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Upgrade pip and install standard dependencies
COPY pyproject.toml README.md ./
RUN pip install --upgrade pip hatchling

# Install the app dependencies
RUN mkdir -p src/ingest && touch src/ingest/__init__.py
RUN pip install .

# Copy application source
COPY . .
RUN pip install .

# Expose standard Cloud Run port
EXPOSE 8080

# Run FastAPI via uvicorn
CMD ["uvicorn", "ingest.main:app", "--host", "0.0.0.0", "--port", "8080", "--workers", "1"]
