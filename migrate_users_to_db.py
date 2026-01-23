"""
Migration script to move users from users.json to PostgreSQL database.

This script:
1. Reads existing users.json file
2. Migrates all users to PostgreSQL
3. Preserves password hashes and user data
4. Creates a backup of users.json before migration
"""

import json
import os
import shutil
from datetime import datetime
import db
import auth

def migrate_users():
    """Migrate users from JSON file to PostgreSQL database."""
    users_file = "users.json"
    
    # Check if users.json exists
    if not os.path.exists(users_file):
        print(f"⚠️  {users_file} not found. No migration needed.")
        return
    
    # Create backup
    backup_file = f"users.json.backup.{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    shutil.copy2(users_file, backup_file)
    print(f"✅ Created backup: {backup_file}")
    
    # Load users from JSON
    try:
        with open(users_file, 'r', encoding='utf-8') as f:
            users = json.load(f)
    except Exception as e:
        print(f"❌ Error reading {users_file}: {e}")
        return
    
    if not users:
        print("ℹ️  No users found in JSON file.")
        return
    
    print(f"📦 Found {len(users)} users to migrate...")
    
    # Initialize database
    try:
        db.init_connection_pool()
        db.init_database()
    except Exception as e:
        print(f"❌ Error initializing database: {e}")
        return
    
    # Migrate each user
    migrated = 0
    skipped = 0
    errors = 0
    
    for username, user_data in users.items():
        try:
            with db.DatabaseConnection() as conn:
                cursor = conn.cursor()
                
                # Check if user already exists
                cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
                if cursor.fetchone()[0] > 0:
                    print(f"⏭️  User '{username}' already exists in database, skipping...")
                    skipped += 1
                    continue
                
                # Insert user
                cursor.execute("""
                    INSERT INTO users (username, password_hash, role, user_id, password_changed)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    username,
                    user_data.get("password_hash", ""),
                    user_data.get("role", "tester"),
                    user_data.get("user_id", username),
                    user_data.get("password_changed", True)
                ))
                conn.commit()
                print(f"✅ Migrated user: {username}")
                migrated += 1
        except Exception as e:
            print(f"❌ Error migrating user '{username}': {e}")
            errors += 1
    
    print("\n" + "="*50)
    print("Migration Summary:")
    print(f"  ✅ Migrated: {migrated}")
    print(f"  ⏭️  Skipped: {skipped}")
    print(f"  ❌ Errors: {errors}")
    print(f"  📦 Total: {len(users)}")
    print("="*50)
    
    if migrated > 0:
        print(f"\n💡 Tip: You can rename {users_file} to {users_file}.old after verifying the migration.")
    else:
        print(f"\n⚠️  No users were migrated. Check the errors above.")

if __name__ == "__main__":
    print("🚀 Starting user migration from JSON to PostgreSQL...")
    print("="*50)
    migrate_users()
    print("\n✅ Migration complete!")

