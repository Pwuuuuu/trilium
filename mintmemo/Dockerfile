FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY pyproject.toml README.md LICENSE /app/
COPY mintmemo /app/mintmemo

RUN pip install --no-cache-dir -e .

EXPOSE 8000
ENV MINTMEMO_HOST=0.0.0.0
ENV MINTMEMO_PORT=8000
ENV MINTMEMO_DB_PATH=/data/mintmemo.db

VOLUME ["/data"]

CMD ["mintmemo", "run"]
