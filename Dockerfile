FROM node:22-slim AS frontend
WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build
# 成果物は /app/src/annotorch/server/static に出る（vite の outDir 設定）

FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
COPY --from=frontend /app/src/annotorch/server/static ./src/annotorch/server/static
RUN pip install --no-cache-dir ".[server]"
EXPOSE 8000
CMD ["annotorch", "serve", "--root", "/data", "--host", "0.0.0.0", "--port", "8000", "--no-browser"]
