FROM python:3.11-slim

WORKDIR /app

# system deps for cryptography & pillow
RUN apt-get update && apt-get install -y --no-install-recommends gcc libffi-dev libssl-dev && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Render provides PORT but bot is polling (no http server) — keep worker
# Create assets dir if missing
RUN mkdir -p assets

CMD ["python", "main.py"]
