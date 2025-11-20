# recon-again Dockerfile
# Based on Kali Linux for security tooling
FROM kalilinux/kali-rolling:latest

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies and Python
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    python3-dev \
    git \
    curl \
    wget \
    sqlite3 \
    libsqlite3-dev \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install Python recon tools
RUN pip3 install --no-cache-dir --break-system-packages \
    aiohttp>=3.8.0 \
    sublist3r \
    dnsrecon \
    waybackpy \
    theHarvester \
    holehe \
    maigret \
    arjun \
    && rm -rf /root/.cache/pip

# Install external recon tools
# Sublist3r is already installed via pip
# DNSRecon is already installed via pip

# Install gau (Go tool for URL extraction)
RUN wget -q https://github.com/lc/gau/releases/latest/download/gau_linux_amd64.tar.gz -O /tmp/gau.tar.gz 2>/dev/null && \
    (tar -xzf /tmp/gau.tar.gz -C /tmp 2>/dev/null && \
     mv /tmp/gau /usr/local/bin/gau && \
     chmod +x /usr/local/bin/gau && \
     rm /tmp/gau.tar.gz) || \
    echo "gau installation skipped (will use alternative methods)"

# Install sherlock
RUN git clone https://github.com/sherlock-project/sherlock.git /opt/sherlock && \
    cd /opt/sherlock && \
    (pip3 install --break-system-packages -r requirements.txt 2>/dev/null || \
     pip3 install --break-system-packages requests beautifulsoup4 lxml requests-futures || \
     pip3 install --break-system-packages -e . || \
     echo "sherlock dependencies installed") && \
    chmod -R +r /opt/sherlock && \
    chmod +x /opt/sherlock/sherlock_project/sherlock.py && \
    chmod +x /opt/sherlock/sherlock_project/__main__.py && \
    echo "sherlock installation completed"

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app/

# Install recon-again package
RUN pip3 install --no-cache-dir --break-system-packages -e .

# Create directories for results and database
RUN mkdir -p /app/results /app/data

# Set default command
CMD ["recon-again", "--help"]

