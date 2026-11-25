FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    HOME=/app

WORKDIR /app
COPY demo/requirements.txt .
RUN python -m pip install --no-cache-dir -r requirements.txt \
    && chown 10001:10001 /app

COPY demo/retrieval.py .
COPY demo/notes/ notes/
USER 10001:10001
CMD ["python", "retrieval.py"]
