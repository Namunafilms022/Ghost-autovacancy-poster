FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt fastapi uvicorn

COPY . .

RUN mkdir -p output/posters output/captions data

ENV PYTHONPATH=/app
ENV APP_ENVIRONMENT=production

EXPOSE 5000 8000

CMD ["python", "main.py", "--dashboard"]
