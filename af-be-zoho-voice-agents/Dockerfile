# ---------- Builder Stage ----------
FROM python:3.12-slim AS builder

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    python3-dev \
&& rm -rf /var/lib/apt/lists/*

COPY requirements.txt .

RUN pip install --no-cache-dir --prefix=/install -r requirements.txt

# ---------- Production Stage ----------
FROM python:3.12-slim

WORKDIR /app

# Patch security vulnerabilities (e.g., CVE-2026-28390)
RUN apt-get update && apt-get upgrade -y --no-install-recommends \
    espeak \
&& rm -rf /var/lib/apt/lists/*

# Copy dependencies
COPY --from=builder /install /usr/local

# Copy source code
COPY . .

# Expose FastAPI port
EXPOSE 5002

# Run (Production)
CMD ["python", "main.py"]
