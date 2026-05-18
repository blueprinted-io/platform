FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /usr/local/bin/uv

# Install dependencies first (layer caching)
COPY pyproject.toml .python-version uv.lock ./
RUN uv sync --no-dev --frozen

# Install Playwright Chromium and its runtime deps.
# --with-deps fails on python:slim (Ubuntu font packages absent in Debian);
# install the Chromium system requirements explicitly instead.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libnss3 libnspr4 libdbus-1-3 libatk1.0-0 libatk-bridge2.0-0 \
    libcups2 libdrm2 libxkbcommon0 libxcomposite1 libxdamage1 \
    libxfixes3 libxrandr2 libgbm1 libasound2 \
    libpango-1.0-0 libcairo2 libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/* \
    && .venv/bin/playwright install chromium

# Copy application source
COPY api/ ./api/
COPY cli/ ./cli/
COPY workers/ ./workers/
COPY ingestion/ ./ingestion/
COPY migrations/ ./migrations/
COPY prompts/ ./prompts/

ENV PATH="/app/.venv/bin:$PATH"
ENV PYTHONPATH="/app"

EXPOSE 8000

CMD ["uvicorn", "api.main:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000"]
