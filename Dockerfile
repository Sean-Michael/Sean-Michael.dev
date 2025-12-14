FROM python:3.12-slim

LABEL maintainer="Sean-Michael seanm.riesterer@gmail.com"

WORKDIR /code

ENV PORT=8000

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY app/ app/
COPY content/ content/

RUN useradd --create-home appuser
USER appuser

EXPOSE ${PORT}

CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT}"]
