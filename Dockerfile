# syntax=docker/dockerfile:1
FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
# 成果物は /app/src/annotorch/server/static に出る（vite の outDir 設定）

FROM python:3.13-slim
WORKDIR /app

COPY pyproject.toml ./
RUN mkdir -p src/annotorch && touch src/annotorch/__init__.py
RUN --mount=type=cache,target=/root/.cache/pip pip install ".[server]"

COPY README.md ./
COPY src ./src
COPY --from=frontend /app/src/annotorch/server/static ./src/annotorch/server/static
RUN --mount=type=cache,target=/root/.cache/pip pip install --no-deps .

EXPOSE 8000
CMD ["annotorch", "serve", "--root", "/data", "--host", "0.0.0.0", "--port", "8000", "--no-browser"]
