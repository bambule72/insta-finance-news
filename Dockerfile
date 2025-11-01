FROM python:3.11-slim

WORKDIR /app

# Ensure local package is importable during build/test
ENV PYTHONPATH=/app

# Install system deps needed for lxml and build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libxml2-dev \
    libxslt1-dev \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt ./
RUN python -m pip install --upgrade pip setuptools wheel && pip install -r requirements.txt

# Copy the source
COPY . /app

# Run tests at build time so the image build fails on broken tests.
RUN pytest -q || (echo "Tests failed" && exit 1)

# Default command: run the Functions Framework for local dev
CMD ["functions-framework", "--target=scrape_news", "--port=8080"]
