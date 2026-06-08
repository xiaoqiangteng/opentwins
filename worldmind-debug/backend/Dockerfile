FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app
RUN mkdir -p /app/data

ENV DEBUG_API_HOST=0.0.0.0
ENV DEBUG_API_PORT=18080
ENV TRACE_DB_PATH=/app/data/debug_trace.sqlite

EXPOSE 18080

CMD ["sh", "-c", "uvicorn app.main:app --host ${DEBUG_API_HOST:-0.0.0.0} --port ${DEBUG_API_PORT:-18080}"]
