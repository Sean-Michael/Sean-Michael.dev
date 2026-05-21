# Stage 1: build frontend
FROM oven/bun:1 AS frontend-builder
WORKDIR /build
COPY frontend/package.json frontend/bun.lock ./
RUN bun install --frozen-lockfile
COPY frontend/ .
RUN bun run build

# Stage 2: Python runtime
FROM python:3.13.12-slim
LABEL maintainer="Sean-Michael seanm.riesterer@gmail.com"

WORKDIR /code

ENV PORT=8000
ENV CONTENT_SOURCE=s3
ENV S3_CONTENT_BUCKET=smr-webdev-content
ENV AWS_REGION=us-west-2

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app/ app/
COPY --from=frontend-builder /build/dist/ frontend/dist/

RUN useradd --create-home appuser
USER appuser

EXPOSE ${PORT}

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
