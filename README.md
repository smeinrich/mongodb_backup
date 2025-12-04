# MongoDB Backup Tool

Quick and easy backup of MongoDB collections to JSON files.

## Features

- 🚀 **Fast and Simple**: One command to backup your MongoDB data
- 🔌 **Flexible Connection**: Defaults to localhost, but supports any MongoDB connection
- 📁 **Organized Exports**: JSON files named after collections with timestamps
- 🎯 **Selective Backup**: Export all collections, specific databases, or individual collections
- 🔐 **Authentication Support**: Works with authenticated MongoDB instances
- 📊 **Progress Feedback**: Clear output showing export progress

## Installation

1. Clone this repository:
```bash
git clone <repository-url>
cd mongodb_backup
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

## Usage

### Basic Examples

**Export all collections from all databases:**
```bash
python mongodb_backup.py --all
```

**Export all collections from a specific database:**
```bash
python mongodb_backup.py --database myapp
```

**Export all collections from multiple databases:**
```bash
python mongodb_backup.py --databases myapp analytics logs
```

**Export a specific collection:**
```bash
python mongodb_backup.py --collection myapp.users
```

**Export multiple specific collections:**
```bash
python mongodb_backup.py --collections myapp.users myapp.products analytics.events
```

### Connection Options

**Default (localhost):**
```bash
python mongodb_backup.py --all
```

**Custom host and port:**
```bash
python mongodb_backup.py --all --host remote-server --port 27017
```

**With authentication (password via CLI):**
```bash
python mongodb_backup.py --all --host remote-server --username admin --password secret
```

**With authentication (password via environment variable - more secure):**
```bash
export MONGODB_PASSWORD=secret
python mongodb_backup.py --all --host remote-server --username admin
```

**Full connection string:**
```bash
python mongodb_backup.py --all --connection "mongodb://user:pass@host:27017/database?authSource=admin"
```

**Custom export folder:**
```bash
python mongodb_backup.py --all --export-folder my_backups
```

### Command Line Options

```
Connection Options:
  --host HOST              MongoDB host (default: localhost)
  --port PORT              MongoDB port (default: 27017)
  -u, --username USERNAME  MongoDB username
  -p, --password PASSWORD  MongoDB password (or set MONGODB_PASSWORD env var)
  --auth-source DB         Authentication database
  -c, --connection STRING  Full MongoDB connection string

Export Options (choose one):
  -a, --all                Export all collections from all databases
  -d, --database DB        Export all collections from a specific database
  --databases DB [DB ...]  Export all collections from multiple databases
  --collection DB.COLL     Export a specific collection (format: database.collection)
  --collections COLL ...   Export multiple specific collections

Other Options:
  -e, --export-folder DIR  Folder to export JSON files to (default: exports)
  -h, --help               Show help message
```

## Output Format

Exported files are saved in the `exports/` folder (or custom folder specified) with the naming format:
```
{database_name}_{collection_name}_{YYYYMMDD}_{HHMMSS}.json
```

Example:
- `myapp_users_20241215_143022.json`
- `myapp_products_20241215_143025.json`
- `analytics_events_20241215_143030.json`

Each JSON file contains an array of documents from the collection, formatted with proper indentation for readability. The database name is included in the filename to prevent collisions when the same collection name exists in multiple databases.

## Examples

### Scenario 1: Quick local backup
```bash
# Backup everything from local MongoDB
python mongodb_backup.py --all
```

### Scenario 2: Backup specific production database
```bash
# Backup only the production database
python mongodb_backup.py --database production \
  --host prod-mongodb.example.com \
  --username backup-user \
  --password backup-pass
```

### Scenario 3: Backup critical collections only
```bash
# Backup only important collections
python mongodb_backup.py --collections \
  production.users \
  production.orders \
  production.payments \
  --host prod-mongodb.example.com \
  --username backup-user \
  --password backup-pass
```

### Scenario 4: Scheduled backups
```bash
# Add to crontab for daily backups at 2 AM
0 2 * * * cd /path/to/mongodb_backup && python mongodb_backup.py --all
```

## Notes

- System databases (`admin`, `config`, `local`) are automatically excluded when using `--all`
- Empty collections are skipped with a warning
- The tool handles connection errors gracefully
- All exports are timestamped to prevent overwrites
- JSON files use UTF-8 encoding and preserve MongoDB document structure
- **Large collections**: Collections with more than 10,000 documents are automatically streamed to avoid memory issues, with progress indication
- **Password security**: Passwords passed via CLI are visible in process lists. Use the `MONGODB_PASSWORD` environment variable for better security
- **File naming**: Database name is included in filenames to prevent collisions when the same collection name exists in multiple databases

## Requirements

- Python 3.6+
- pymongo 4.6.0+

## License

MIT
