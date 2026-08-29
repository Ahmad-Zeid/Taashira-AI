# Runtime image for the Taashira API service.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Dependencies first, so source edits do not invalidate this layer.
COPY requirements-api.txt ./
RUN pip install --no-cache-dir -r requirements-api.txt

COPY taashira/ ./taashira/
COPY packs/ ./packs/

# Cloud Run supplies PORT; the default keeps `docker run` working locally.
ENV PORT=8080
EXPOSE 8080
CMD ["sh", "-c", "uvicorn taashira.main:app --host 0.0.0.0 --port ${PORT}"]
