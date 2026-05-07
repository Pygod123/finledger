FROM python:3.13-slim

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc curl && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps first (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Create staticfiles dir
RUN mkdir -p staticfiles media

EXPOSE 8000

CMD ["gunicorn", "finledger.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
