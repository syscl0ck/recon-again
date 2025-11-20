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
RUN pip3 install --no-cache-dir \
    aiohttp>=3.8.0 \
    sublist3r \
    dnsrecon \
    waybackpy \
    && rm -rf /root/.cache/pip

# Install external recon tools
# Sublist3r is already installed via pip
# DNSRecon is already installed via pip

# Install dirsearch
RUN git clone https://github.com/maurosoria/dirsearch.git /opt/dirsearch && \
    chmod +x /opt/dirsearch/dirsearch.py && \
    ln -s /opt/dirsearch/dirsearch.py /usr/local/bin/dirsearch

# Install waybackurls (Go tool - if available)
RUN wget -q https://github.com/tomnomnom/waybackurls/releases/latest/download/waybackurls-linux-amd64 -O /usr/local/bin/waybackurls && \
    chmod +x /usr/local/bin/waybackurls || echo "waybackurls installation skipped"

# Install sherlock
RUN git clone https://github.com/sherlock-project/sherlock.git /opt/sherlock && \
    cd /opt/sherlock && \
    pip3 install -r requirements.txt && \
    ln -s /opt/sherlock/sherlock/sherlock.py /usr/local/bin/sherlock

# Set working directory
WORKDIR /app

# Copy project files
COPY . /app/

# Install recon-again package
RUN pip3 install --no-cache-dir -e .

# Create directories for results and database
RUN mkdir -p /app/results /app/data

# Set default command
CMD ["recon-again", "--help"]

