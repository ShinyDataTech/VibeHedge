# ==========================================
# Stage 1: Build & Dependency Resolution
# ==========================================
FROM ghcr.io/astral-sh/uv:python3.11-bookworm-slim AS builder

WORKDIR /app

# Enable bytecode compilation
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Copy dependency definition files
COPY pyproject.toml uv.lock ./

# Install project dependencies into virtual environment
RUN uv sync --frozen --no-install-project --no-dev

# ==========================================
# Stage 2: Minimal Runtime for Cloud Run
# ==========================================
FROM python:3.11-slim AS runner

WORKDIR /app

# Set Cloud Run runtime environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/app/.venv/bin:$PATH" \
    PORT=8080 \
    HOST=0.0.0.0

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser -d /app appuser

# Copy virtualenv from builder
COPY --from=builder /app/.venv /app/.venv

# Copy source code, modules, training pipeline, and models
COPY src/ /app/src/
COPY training/ /app/training/
COPY models/ /app/models/
COPY pyproject.toml README.md /app/

# Set permissions for non-root execution
RUN chown -R appuser:appuser /app

USER appuser

# Expose standard Cloud Run port
EXPOSE 8080

# Healthcheck to verify container responsiveness
HEALTHCHECK --interval=30s --timeout=5s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request, os; urllib.request.urlopen('http://127.0.0.1:' + os.environ.get('PORT', '8080') + '/health', timeout=3)" || exit 0

# Entrypoint running FastMCP server
CMD ["python", "-m", "src.mcp_server.server"]
