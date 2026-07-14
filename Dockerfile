FROM node:22-slim AS frontend
WORKDIR /build
COPY webapp/package.json webapp/package-lock.json ./
RUN npm ci --legacy-peer-deps
COPY webapp/ ./
RUN npx ng build --configuration=production

FROM python:3.12-slim
RUN pip install uv
WORKDIR /app
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --no-dev --frozen
COPY backend/ ./
COPY --from=frontend /build/dist/app/browser /app/static

EXPOSE 8000
CMD ["sh", "-c", "uv run alembic upgrade head && uv run uvicorn app.main:app --host 0.0.0.0 --port 8000"]
