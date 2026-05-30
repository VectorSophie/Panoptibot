FROM python:3.11-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1
ENV UV_CACHE_DIR=/tmp/uv-cache

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock README.md ./
COPY panoptibot ./panoptibot
COPY scripts ./scripts

RUN uv sync --frozen --no-dev

CMD ["uv", "run", "panoptibot"]
