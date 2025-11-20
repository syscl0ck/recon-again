# Database Documentation

recon-again uses SQLite for persistent storage of all reconnaissance data.

## Database Schema

### Tables

#### `targets`
Stores target information (domains, IPs, emails, etc.)

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| target | TEXT | Target identifier (unique) |
| target_type | TEXT | Type: 'domain', 'ip', 'email', 'username' |
| created_at | TIMESTAMP | Creation timestamp |
| updated_at | TIMESTAMP | Last update timestamp |

#### `sessions`
Stores reconnaissance sessions

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| session_id | TEXT | Unique session identifier |
| target_id | INTEGER | Foreign key to targets |
| status | TEXT | 'running', 'completed', 'failed' |
| start_time | TIMESTAMP | Session start time |
| end_time | TIMESTAMP | Session end time |
| tools_executed | TEXT | JSON array of tool names |
| created_at | TIMESTAMP | Creation timestamp |

#### `tool_results`
Stores results from individual tools

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| session_id | TEXT | Foreign key to sessions |
| tool_name | TEXT | Name of the tool |
| target | TEXT | Target that was scanned |
| success | INTEGER | 1 for success, 0 for failure |
| data | TEXT | JSON data from tool |
| error | TEXT | Error message if failed |
| execution_time | REAL | Execution time in seconds |
| metadata | TEXT | JSON metadata |
| timestamp | TIMESTAMP | When result was recorded |

#### `ai_analysis`
Stores AI-generated analysis

| Column | Type | Description |
|--------|------|-------------|
| id | INTEGER | Primary key |
| session_id | TEXT | Foreign key to sessions (unique) |
| target | TEXT | Target analyzed |
| summary | TEXT | Summary of findings |
| key_findings | TEXT | JSON array of key findings |
| recommendations | TEXT | JSON array of recommendations |
| risk_level | TEXT | 'low', 'medium', 'high', 'critical' |
| interesting_targets | TEXT | JSON array of interesting targets |
| analysis_data | TEXT | Full JSON analysis |
| created_at | TIMESTAMP | Creation timestamp |

## Usage

### Initialize Database

```bash
# Using CLI command
recon-again-init-db

# With custom path
recon-again-init-db --db-path /path/to/database.db

# Reset database (WARNING: deletes all data)
recon-again-init-db --reset
```

### Python API

```python
from recon_again.database import init_db, get_db, Session, ToolResult, AIAnalysis

# Initialize database
init_db('./data/recon_again.db')

# Get session
session = Session.get_by_session_id('example.com_20240101_120000')

# Get tool results
results = ToolResult.get_by_session('example.com_20240101_120000')

# Get AI analysis
analysis = AIAnalysis.get_by_session('example.com_20240101_120000')
```

### Query Examples

#### List Recent Sessions

```python
from recon_again.database import Database

db = Database()
sessions = db.list_sessions(limit=10)
for session in sessions:
    print(f"{session.session_id}: {session.status}")
```

#### Get Target Statistics

```python
from recon_again.database import Database

db = Database()
stats = db.get_target_stats('example.com')
print(f"Sessions: {stats['session_count']}")
print(f"Tool Results: {stats['tool_results_count']}")
```

#### SQL Queries

```bash
# Using sqlite3 CLI
sqlite3 ./data/recon_again.db

# List all sessions
SELECT session_id, status, start_time FROM sessions ORDER BY start_time DESC;

# Count tool results by tool
SELECT tool_name, COUNT(*) as count 
FROM tool_results 
GROUP BY tool_name 
ORDER BY count DESC;

# Find sessions with AI analysis
SELECT s.session_id, s.target_id, a.risk_level, a.summary
FROM sessions s
JOIN ai_analysis a ON s.session_id = a.session_id
ORDER BY s.start_time DESC;

# Get all subdomains found
SELECT DISTINCT json_extract(data, '$.subdomains') as subdomains
FROM tool_results
WHERE tool_name = 'crt_sh' AND success = 1;
```

## Data Migration

### From JSON to Database

If you have existing JSON result files, you can import them:

```python
import json
from pathlib import Path
from recon_again.database import init_db, Target, Session, ToolResult, AIAnalysis

init_db()

# Load JSON file
with open('results/example.com_20240101_120000.json', 'r') as f:
    data = json.load(f)

# Create target
target = Target.get_or_create(data['target'])

# Create session
session = Session(
    session_id=data['session_id'],
    target_id=target.id,
    status=data['status'],
    start_time=datetime.fromisoformat(data['start_time']),
    tools_executed=data['tools_executed']
)
session.save()

# Import tool results
for tool_name, result in data['results'].items():
    if tool_name == 'ai_analysis':
        continue
    
    tr = ToolResult(
        session_id=session.session_id,
        tool_name=tool_name,
        target=data['target'],
        success=result.get('success', False),
        data=result.get('data'),
        error=result.get('error'),
        execution_time=result.get('execution_time', 0.0),
        metadata=result.get('metadata', {})
    )
    tr.save()

# Import AI analysis if present
if 'ai_analysis' in data['results']:
    analysis_data = data['results']['ai_analysis']
    ai = AIAnalysis(
        session_id=session.session_id,
        target=data['target'],
        summary=analysis_data.get('summary'),
        key_findings=analysis_data.get('key_findings', []),
        recommendations=analysis_data.get('recommendations', []),
        risk_level=analysis_data.get('risk_level'),
        interesting_targets=analysis_data.get('interesting_targets', []),
        analysis_data=analysis_data
    )
    ai.save()
```

## Backup and Restore

### Backup

```bash
# Simple copy
cp ./data/recon_again.db ./backups/recon_again_$(date +%Y%m%d).db

# With compression
sqlite3 ./data/recon_again.db ".backup './backups/recon_again.db'"
```

### Restore

```bash
# Stop recon-again if running
# Copy backup over database
cp ./backups/recon_again_20240101.db ./data/recon_again.db
```

## Performance

### Indexes

The database includes indexes on:
- `sessions.target_id`
- `sessions.status`
- `tool_results.session_id`
- `tool_results.tool_name`
- `targets.target`

### Optimization

```sql
-- Analyze tables for better query planning
ANALYZE;

-- Vacuum to reclaim space
VACUUM;

-- Reindex
REINDEX;
```

## Best Practices

1. **Regular Backups**: Backup your database regularly
2. **Vacuum**: Run `VACUUM` periodically to optimize
3. **Indexes**: Don't add too many indexes (already optimized)
4. **Transactions**: Use transactions for bulk operations
5. **Connection Pooling**: SQLite handles connections well, but don't keep too many open

## Troubleshooting

### Database Locked
- Ensure only one process accesses the database at a time
- Close connections properly
- Check for stale lock files

### Corrupted Database
```bash
# Check integrity
sqlite3 ./data/recon_again.db "PRAGMA integrity_check;"

# Recover if needed
sqlite3 ./data/recon_again.db ".recover" | sqlite3 recovered.db
```

### Large Database
- Consider archiving old sessions
- Use `VACUUM` to reclaim space
- Consider splitting into multiple databases by date

