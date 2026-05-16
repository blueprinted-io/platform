FROM python:3.12-slim

WORKDIR /app

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.11.14 /uv /usr/local/bin/uv

# Install dependencies first (layer caching)
COPY pyproject.toml .python-version uv.lock ./
RUN uv sync --no-dev --frozen

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
