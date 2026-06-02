FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --upgrade pip hatchling
RUN mkdir -p src/query && touch src/query/__init__.py
RUN pip install --no-cache-dir .

COPY src/ ./src/
RUN pip install --no-cache-dir .

ENV PYTHONPATH=/app/src
ENV PORT=8080

CMD ["uvicorn", "query.main:app", "--host", "0.0.0.0", "--port", "8080"]
