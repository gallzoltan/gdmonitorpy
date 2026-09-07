# Építő lépcső: a függőségeket az uv.lock alapján, reprodukálhatóan telepítjük.
FROM python:3.12-slim AS builder

ENV PYTHONDONTWRITEBYTECODE=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

RUN pip install --no-cache-dir uv

WORKDIR /app

# Előbb csak a függőségek: így a forrás módosítása nem érvényteleníti ezt a réteget.
COPY pyproject.toml uv.lock README.md LICENSE ./
RUN uv sync --frozen --no-dev --no-install-project --no-editable

# Majd a projekt maga. A --no-editable miatt a csomag a .venv-be kerül,
# nem a forrásra mutató .pth-ként, így a futtató lépcsőnek nem kell a src.
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable


# Futtató lépcső: csak a kész virtuális környezet és a tanúsítvány.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    LANG=C.UTF-8 \
    TZ=Europe/Budapest \
    PATH="/app/.venv/bin:$PATH"

RUN apt-get update \
    && apt-get install -y --no-install-recommends tzdata \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 1000 gdmonitor \
    && mkdir -p /data \
    && chown gdmonitor:gdmonitor /data

WORKDIR /app

COPY --from=builder /app/.venv /app/.venv
COPY certificates ./certificates

USER gdmonitor

# A DB_PATH és a DOWNLOAD_PATH abszolút útvonalként a /data alá mutat,
# amit a hosztról csatolunk be.
CMD ["gdmonitor", "--analyze", "--email"]
