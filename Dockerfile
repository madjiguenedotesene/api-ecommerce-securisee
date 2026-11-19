FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

# Exécution sans privilèges root
RUN useradd --create-home --uid 10001 api
USER api

EXPOSE 8000
CMD ["sh", "-c", "gunicorn -w ${WORKERS:-2} -k uvicorn.workers.UvicornWorker -b 0.0.0.0:${PORT:-8000} app.main:app"]
