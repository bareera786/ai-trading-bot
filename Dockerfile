# Use a base image with Python 3.11
FROM python:3.11-slim

# Create non-root user
RUN useradd --create-home --shell /bin/bash trader

# Install system dependencies for building TA-Lib
RUN apt-get update && apt-get install -y \
    build-essential \
    wget \
    autoconf \
    automake \
    libtool \
    pkg-config \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Build and install TA-Lib (robust extraction and parallel build)
RUN wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz -O /tmp/ta-lib.tar.gz && \
    tar -xzf /tmp/ta-lib.tar.gz -C /tmp && \
    DIR=$(tar -tzf /tmp/ta-lib.tar.gz | head -1 | cut -f1 -d"/") && \
    cd /tmp/$DIR && \
    ./configure --prefix=/usr && \
    # Try a parallel build first; if it fails (race in gen_code), fall back to single-threaded make
    make -j$(nproc) || make && \
    make install && \
    rm -rf /tmp/$DIR /tmp/ta-lib.tar.gz

# Create a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Set work directory
WORKDIR /app

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code with proper ownership
COPY --chown=trader:trader . .

# Ensure directories used at runtime exist and are writable by the non-root user
RUN mkdir -p /app/optimized_models /app/optimized_trade_data /app/ultimate_models && \
    chown -R trader:trader /app/optimized_models /app/optimized_trade_data /app/ultimate_models

# Expose port before CMD
EXPOSE 5000

# Switch to non-root user
USER trader

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import requests; exit(0) if requests.get('http://localhost:5000/health').status_code == 200 else exit(1)"

CMD ["python", "start_server.py"]
