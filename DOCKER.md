# Docker Setup for recon-again

## Quick Start

### Build the Image

```bash
docker build -t recon-again:latest .
```

### Run with Docker Compose

```bash
# Start container
docker-compose up -d

# Execute reconnaissance
docker-compose exec recon-again recon-again example.com

# View logs
docker-compose logs -f recon-again

# Stop container
docker-compose down
```

### Run Directly with Docker

```bash
# Run a reconnaissance
docker run --rm -v $(pwd)/results:/app/results -v $(pwd)/data:/app/data recon-again:latest recon-again example.com

# Interactive shell
docker run --rm -it -v $(pwd)/results:/app/results -v $(pwd)/data:/app/data recon-again:latest /bin/bash
```

## Container Details

### Base Image
- **Kali Linux Rolling** - Latest Kali Linux with all security tools

### Installed Tools
- Python 3 with pip
- SQLite3
- **Python tools** (via pip):
  - sublist3r
  - dnsrecon
  - waybackpy
- **External tools**:
  - sherlock (from GitHub)
  - waybackurls (Go binary, if available)

### Volumes
- `./results` - Reconnaissance results (JSON backups)
- `./data` - SQLite database files
- `./config.json` - Configuration file (read-only)

### Environment Variables
- `PYTHONUNBUFFERED=1` - Real-time Python output

## Database in Docker

The database is stored in `/app/data/recon_again.db` inside the container, which is mounted to `./data/recon_again.db` on the host.

### Initialize Database

```bash
# Inside container
docker-compose exec recon-again python -m recon_again.database.init_db

# Or from host
docker-compose exec recon-again python -m recon_again.database.init_db --db-path /app/data/recon_again.db
```

## Custom Configuration

1. Create `config.json` from `config.example.json`
2. Mount it in `docker-compose.yml`:
   ```yaml
   volumes:
     - ./config.json:/app/config.json:ro
   ```

## Troubleshooting

### Tool Not Found
Some tools may not be available in the container. Check logs:
```bash
docker-compose logs recon-again
```

### Database Permissions
Ensure the `./data` directory is writable:
```bash
chmod 755 ./data
```

### Build Issues
If build fails, try:
```bash
docker build --no-cache -t recon-again:latest .
```

## Development

### Rebuild After Changes
```bash
docker-compose build --no-cache
docker-compose up -d
```

### Access Container Shell
```bash
docker-compose exec recon-again /bin/bash
```

### View Database
```bash
# Inside container
sqlite3 /app/data/recon_again.db

# From host
sqlite3 ./data/recon_again.db
```

## Production Considerations

- Use Docker secrets for API keys
- Set resource limits in docker-compose.yml
- Use volumes for persistent storage
- Consider using Docker networks for isolation
- Monitor container resource usage

