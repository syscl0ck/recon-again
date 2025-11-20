#!/usr/bin/env python3
"""
Database initialization script
Run this to create/initialize the database
"""

import sys
import argparse
from pathlib import Path

from .connection import init_db, get_db


def main():
    parser = argparse.ArgumentParser(description='Initialize recon-again database')
    parser.add_argument(
        '--db-path',
        default='./data/recon_again.db',
        help='Path to database file (default: ./data/recon_again.db)'
    )
    parser.add_argument(
        '--reset',
        action='store_true',
        help='Reset database (WARNING: deletes all data)'
    )
    
    args = parser.parse_args()
    
    db_path = Path(args.db_path)
    
    if args.reset and db_path.exists():
        print(f"⚠️  WARNING: This will delete all data in {db_path}")
        response = input("Are you sure? (yes/no): ")
        if response.lower() != 'yes':
            print("Aborted.")
            sys.exit(0)
        db_path.unlink()
        print(f"Deleted existing database: {db_path}")
    
    print(f"Initializing database at: {db_path}")
    init_db(str(db_path))
    
    # Verify tables
    db = get_db(str(db_path))
    tables = db.fetchall(
        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
    )
    
    print("\n✅ Database initialized successfully!")
    print(f"\nTables created:")
    for table in tables:
        print(f"  - {table['name']}")
    
    # Show table schemas
    print("\n📊 Table schemas:")
    for table in tables:
        table_name = table['name']
        schema = db.fetchall(f"PRAGMA table_info({table_name})")
        print(f"\n{table_name}:")
        for col in schema:
            print(f"  {col['name']} ({col['type']})")


if __name__ == '__main__':
    main()

