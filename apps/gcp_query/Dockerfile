FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY src/ ./src/

ENV PYTHONPATH=/app/src
ENV PORT=8080

CMD ["uvicorn", "query.main:app", "--host", "0.0.0.0", "--port", "8080"]
