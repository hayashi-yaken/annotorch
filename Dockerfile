FROM python:3.13-slim
WORKDIR /app
COPY pyproject.toml README.md ./
COPY src ./src
RUN pip install --no-cache-dir ".[server]"
EXPOSE 8000
CMD ["annotorch", "serve", "--root", "/data", "--host", "0.0.0.0", "--port", "8000", "--no-browser"]
