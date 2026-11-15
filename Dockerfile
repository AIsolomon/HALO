FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 UV_CACHE_DIR=/tmp/uv-cache
WORKDIR /app
RUN python -m pip install --no-cache-dir uv==0.13.6
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev --no-editable \
    && groupadd --gid 10001 halo \
    && useradd --uid 10001 --gid halo --no-create-home halo \
    && mkdir -p /app/work \
    && chown halo:halo /app/work
ENV PATH="/app/.venv/bin:$PATH"
USER halo
EXPOSE 8000
CMD ["uvicorn", "halo.api:create_app", "--factory", "--host", "0.0.0.0", "--port", "8000", "--no-access-log"]
