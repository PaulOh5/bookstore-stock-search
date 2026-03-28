FROM python:3.12-slim AS builder

RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libxml2-dev libxslt-dev && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /build
COPY pyproject.toml .
COPY app/ app/

RUN python -m venv /opt/venv && \
    /opt/venv/bin/pip install --no-cache-dir .

# --- Runtime stage ---
FROM python:3.12-slim

RUN apt-get update && \
    apt-get install -y --no-install-recommends libxml2 libxslt1.1 && \
    rm -rf /var/lib/apt/lists/*

RUN useradd --create-home appuser

COPY --from=builder /opt/venv /opt/venv
COPY app/ /home/appuser/app/

ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

WORKDIR /home/appuser
USER appuser

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--proxy-headers", "--forwarded-allow-ips", "*"]
