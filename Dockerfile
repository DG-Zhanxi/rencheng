FROM node:24-alpine AS ui
WORKDIR /ui
COPY frontend/package*.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build
FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ backend/
COPY vendor/ vendor/
COPY data/ data/
COPY --from=ui /ui/dist frontend/dist/
RUN mkdir -p config && useradd -u 10001 appuser && chown -R appuser /app
USER appuser
EXPOSE 8027
CMD ["python","-m","uvicorn","backend.app:app","--host","0.0.0.0","--port","8027","--proxy-headers","--forwarded-allow-ips=127.0.0.1"]
