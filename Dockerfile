FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    SKILLLINT_WEB_HOST=0.0.0.0 \
    SKILLLINT_WEB_PORT=18110 \
    SKILLLINT_WEB_WORKERS=2 \
    SKILLLINT_WEB_LOG_LEVEL=info

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md LICENSE /app/
COPY config /app/config
COPY src /app/src

RUN pip install .

RUN useradd --create-home --shell /usr/sbin/nologin skilllint \
    && mkdir -p /app/.skilllint-work \
    && chown -R skilllint:skilllint /app

USER skilllint

EXPOSE 18110

CMD ["skilllint-web"]
