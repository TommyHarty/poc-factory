FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency files
COPY pyproject.toml .
COPY README.md .

# Install Python dependencies
RUN pip install --no-cache-dir -e ".[dev]"

# Copy application code
COPY app/ ./app/

# Create necessary directories
RUN mkdir -p /app/output /app/work /app/logs

# Set environment
ENV APP_ENV=production
ENV OUTPUT_ROOT=/app/output
ENV WORK_ROOT=/app/work
ENV PYTHONPATH=/app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
