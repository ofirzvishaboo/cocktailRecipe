FROM python:3.12-slim

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

# Set working directory
WORKDIR /app

# Copy dependency files
COPY pyproject.toml uv.lock* ./

# Install production dependencies only (skip dev group)
RUN uv sync --no-dev

# Copy application code
COPY . .

# Non-root runtime must own the project tree (including .venv); uv sync ran as root above.
RUN useradd -m app && chown -R app:app /app
USER app

# Expose port
EXPOSE 8000

# Bake deps at build time; skip implicit `uv sync` on start (it would reinstall dev-only groups).
CMD ["uv", "run", "--no-sync", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

