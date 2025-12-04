#!/usr/bin/env python3
"""
MongoDB Backup Tool
Quick and easy backup of MongoDB collections to JSON files.
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path
from typing import List, Optional
from urllib.parse import quote_plus

try:
    from pymongo import MongoClient
    from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
except ImportError:
    print("Error: pymongo is not installed. Please run: pip install -r requirements.txt")
    sys.exit(1)


class MongoDBBackup:
    """Main class for MongoDB backup operations."""
    
    def __init__(self, connection_string: str = "mongodb://localhost:27017/", 
                 export_folder: str = "exports"):
        """
        Initialize MongoDB backup tool.
        
        Args:
            connection_string: MongoDB connection string (default: localhost)
            export_folder: Folder to export JSON files to
        """
        self.connection_string = connection_string
        self.export_folder = Path(export_folder)
        self.export_folder.mkdir(exist_ok=True)
        self.client = None
        
    def connect(self):
        """Establish connection to MongoDB."""
        try:
            self.client = MongoClient(self.connection_string, serverSelectionTimeoutMS=5000)
            # Test connection
            self.client.admin.command('ping')
            # Mask password in connection string for display
            display_conn = self._mask_connection_string(self.connection_string)
            print(f"✓ Connected to MongoDB: {display_conn}")
            return True
        except (ConnectionFailure, ServerSelectionTimeoutError) as e:
            print(f"✗ Failed to connect to MongoDB: {e}")
            return False
    
    def _mask_connection_string(self, conn_string: str) -> str:
        """Mask password in connection string for safe display."""
        if '@' in conn_string and '://' in conn_string:
            parts = conn_string.split('@', 1)
            if ':' in parts[0]:
                # Has credentials
                protocol_and_user = parts[0].split('://')[0] + '://'
                user_part = parts[0].split('://')[1]
                if ':' in user_part:
                    username = user_part.split(':')[0]
                    protocol_and_user += username + ':***@'
                else:
                    protocol_and_user += user_part + '@'
                return protocol_and_user + parts[1]
        return conn_string
    
    def get_databases(self) -> List[str]:
        """Get list of all database names."""
        return self.client.list_database_names()
    
    def get_collections(self, database_name: str) -> List[str]:
        """Get list of all collection names in a database."""
        db = self.client[database_name]
        return db.list_collection_names()
    
    def export_collection(self, database_name: str, collection_name: str, 
                         show_progress: bool = True) -> bool:
        """
        Export a single collection to JSON file.
        
        Args:
            database_name: Name of the database
            collection_name: Name of the collection
            show_progress: Whether to show progress for large collections
            
        Returns:
            True if successful, False otherwise
        """
        try:
            db = self.client[database_name]
            collection = db[collection_name]
            
            # Get collection count for progress indication
            total_count = collection.count_documents({})
            
            if total_count == 0:
                print(f"  ⚠ Collection '{database_name}.{collection_name}' is empty, skipping...")
                return True
            
            # Generate filename: database_collection_datetime.json
            # Include database name to prevent collisions
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_db_name = database_name.replace('/', '_').replace('\\', '_')
            safe_collection_name = collection_name.replace('/', '_').replace('\\', '_')
            filename = f"{safe_db_name}_{safe_collection_name}_{timestamp}.json"
            filepath = self.export_folder / filename
            
            # For large collections, use streaming approach
            if total_count > 10000 and show_progress:
                print(f"  📊 Large collection detected ({total_count:,} documents), streaming export...")
                self._export_collection_streaming(collection, filepath, total_count)
            else:
                # For smaller collections, load all at once
                documents = list(collection.find())
                with open(filepath, 'w', encoding='utf-8') as f:
                    json.dump(documents, f, indent=2, default=str, ensure_ascii=False)
            
            print(f"  ✓ Exported {total_count:,} documents from '{database_name}.{collection_name}' -> {filepath}")
            return True
            
        except Exception as e:
            print(f"  ✗ Error exporting '{database_name}.{collection_name}': {e}")
            return False
    
    def _export_collection_streaming(self, collection, filepath: Path, total_count: int):
        """
        Export collection using streaming to handle large collections efficiently.
        
        Args:
            collection: MongoDB collection object
            filepath: Path to output file
            total_count: Total number of documents
        """
        batch_size = 1000
        exported = 0
        
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write('[\n')
            first = True
            
            cursor = collection.find().batch_size(batch_size)
            for doc in cursor:
                if not first:
                    f.write(',\n')
                json.dump(doc, f, indent=2, default=str, ensure_ascii=False)
                first = False
                exported += 1
                
                # Show progress every 1000 documents
                if exported % 1000 == 0:
                    progress = (exported / total_count) * 100
                    print(f"    Progress: {exported:,}/{total_count:,} ({progress:.1f}%)", end='\r')
            
            f.write('\n]')
        
        print()  # New line after progress
    
    def export_all_collections(self):
        """Export all collections from all databases."""
        print("\n📦 Exporting all collections from all databases...")
        databases = self.get_databases()
        
        # Filter out system databases
        databases = [db for db in databases if db not in ['admin', 'config', 'local']]
        
        total_collections = 0
        successful = 0
        
        for db_name in databases:
            collections = self.get_collections(db_name)
            if collections:
                print(f"\n📁 Database: {db_name}")
                for collection_name in collections:
                    total_collections += 1
                    if self.export_collection(db_name, collection_name):
                        successful += 1
        
        print(f"\n✅ Export complete: {successful}/{total_collections} collections exported successfully")
    
    def export_database(self, database_name: str):
        """Export all collections from a specific database."""
        print(f"\n📦 Exporting all collections from database '{database_name}'...")
        
        if database_name not in self.get_databases():
            print(f"✗ Database '{database_name}' not found")
            return
        
        collections = self.get_collections(database_name)
        if not collections:
            print(f"⚠ Database '{database_name}' has no collections")
            return
        
        print(f"📁 Database: {database_name}")
        successful = 0
        for collection_name in collections:
            if self.export_collection(database_name, collection_name):
                successful += 1
        
        print(f"\n✅ Export complete: {successful}/{len(collections)} collections exported successfully")
    
    def export_databases(self, database_names: List[str]):
        """Export all collections from multiple databases."""
        print(f"\n📦 Exporting all collections from databases: {', '.join(database_names)}...")
        
        available_databases = self.get_databases()
        total_collections = 0
        successful = 0
        
        for db_name in database_names:
            if db_name not in available_databases:
                print(f"⚠ Database '{db_name}' not found, skipping...")
                continue
            
            collections = self.get_collections(db_name)
            if collections:
                print(f"\n📁 Database: {db_name}")
                for collection_name in collections:
                    total_collections += 1
                    if self.export_collection(db_name, collection_name):
                        successful += 1
        
        print(f"\n✅ Export complete: {successful}/{total_collections} collections exported successfully")
    
    def export_collection_specific(self, database_name: str, collection_name: str):
        """Export a specific collection."""
        print(f"\n📦 Exporting collection '{database_name}.{collection_name}'...")
        
        if database_name not in self.get_databases():
            print(f"✗ Database '{database_name}' not found")
            return
        
        collections = self.get_collections(database_name)
        if collection_name not in collections:
            print(f"✗ Collection '{collection_name}' not found in database '{database_name}'")
            return
        
        if self.export_collection(database_name, collection_name):
            print(f"\n✅ Export complete")
    
    def export_collections_specific(self, collection_specs: List[str]):
        """
        Export specific collections.
        
        Args:
            collection_specs: List of strings in format "database.collection"
        """
        print(f"\n📦 Exporting specific collections...")
        
        successful = 0
        for spec in collection_specs:
            if '.' not in spec:
                print(f"⚠ Invalid format '{spec}'. Expected format: 'database.collection'")
                continue
            
            db_name, collection_name = spec.split('.', 1)
            if self.export_collection(db_name, collection_name):
                successful += 1
        
        print(f"\n✅ Export complete: {successful}/{len(collection_specs)} collections exported successfully")
    
    def close(self):
        """Close MongoDB connection."""
        if self.client:
            self.client.close()


def build_connection_string(host: str, port: int, username: Optional[str], 
                           password: Optional[str], database: Optional[str],
                           auth_source: Optional[str]) -> str:
    """Build MongoDB connection string from components."""
    if username and password:
        credentials = f"{quote_plus(username)}:{quote_plus(password)}@"
        base = f"mongodb://{credentials}{host}:{port}/"
    else:
        base = f"mongodb://{host}:{port}/"
    
    if database:
        base += database
    
    if auth_source:
        if '?' in base:
            base += f"&authSource={auth_source}"
        else:
            base += f"?authSource={auth_source}"
    
    return base


def main():
    """Main entry point for CLI."""
    parser = argparse.ArgumentParser(
        description="Quick and easy backup of MongoDB collections to JSON files",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Export all collections from all databases
  python mongodb_backup.py --all
  
  # Export all collections from a specific database
  python mongodb_backup.py --database mydb
  
  # Export all collections from multiple databases
  python mongodb_backup.py --databases mydb1 mydb2
  
  # Export a specific collection
  python mongodb_backup.py --collection mydb.mycollection
  
  # Export multiple specific collections
  python mongodb_backup.py --collections mydb.col1 mydb.col2 otherdb.col3
  
  # Use custom connection string
  python mongodb_backup.py --all --connection "mongodb://user:pass@host:27017/"
  
  # Use connection components
  python mongodb_backup.py --all --host remote-host --port 27017 --username user --password pass
        """
    )
    
    # Connection options
    parser.add_argument('--host', default='localhost',
                       help='MongoDB host (default: localhost)')
    parser.add_argument('--port', type=int, default=27017,
                       help='MongoDB port (default: 27017)')
    parser.add_argument('--username', '-u',
                       help='MongoDB username')
    parser.add_argument('--password', '-p',
                       help='MongoDB password (or set MONGODB_PASSWORD env var)')
    parser.add_argument('--auth-source',
                       help='Authentication database')
    parser.add_argument('--connection', '-c',
                       help='Full MongoDB connection string (overrides host/port/username/password)')
    
    # Export options (mutually exclusive)
    export_group = parser.add_mutually_exclusive_group(required=True)
    export_group.add_argument('--all', '-a', action='store_true',
                             help='Export all collections from all databases')
    export_group.add_argument('--database', '-d',
                             help='Export all collections from a specific database')
    export_group.add_argument('--databases', nargs='+',
                             help='Export all collections from multiple databases')
    export_group.add_argument('--collection',
                             help='Export a specific collection (format: database.collection)')
    export_group.add_argument('--collections', nargs='+',
                             help='Export multiple specific collections (format: database.collection)')
    
    # Export folder
    parser.add_argument('--export-folder', '-e', default='exports',
                       help='Folder to export JSON files to (default: exports)')
    
    args = parser.parse_args()
    
    # Get password from environment variable if not provided via CLI
    password = args.password
    if not password:
        password = os.environ.get('MONGODB_PASSWORD')
    
    # Build connection string
    if args.connection:
        connection_string = args.connection
    else:
        connection_string = build_connection_string(
            args.host, args.port, args.username, password,
            None, args.auth_source
        )
    
    # Initialize backup tool
    backup = MongoDBBackup(connection_string, args.export_folder)
    
    # Connect to MongoDB
    if not backup.connect():
        sys.exit(1)
    
    try:
        # Perform export based on arguments
        if args.all:
            backup.export_all_collections()
        elif args.database:
            backup.export_database(args.database)
        elif args.databases:
            backup.export_databases(args.databases)
        elif args.collection:
            if '.' not in args.collection:
                print("✗ Error: Collection format must be 'database.collection'")
                sys.exit(1)
            db_name, collection_name = args.collection.split('.', 1)
            backup.export_collection_specific(db_name, collection_name)
        elif args.collections:
            backup.export_collections_specific(args.collections)
    finally:
        backup.close()


if __name__ == "__main__":
    main()

