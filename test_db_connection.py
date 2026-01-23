"""
Test script to verify PostgreSQL database connection and schema.

Run this script to check if:
1. Database connection is working
2. Schema is properly initialized
3. Default admin user can be created
"""

import db
import auth

def test_connection():
    """Test database connection and schema."""
    print("="*50)
    print("Testing PostgreSQL Database Connection")
    print("="*50)
    
    # Test 1: Connection
    print("\n1. Testing database connection...")
    try:
        if db.test_connection():
            print("   ✅ Database connection successful!")
        else:
            print("   ❌ Database connection failed!")
            return False
    except Exception as e:
        print(f"   ❌ Error: {e}")
        return False
    
    # Test 2: Schema initialization
    print("\n2. Initializing database schema...")
    try:
        db.init_database()
        print("   ✅ Database schema initialized!")
    except Exception as e:
        print(f"   ❌ Error initializing schema: {e}")
        return False
    
    # Test 3: Default users
    print("\n3. Checking default users...")
    try:
        auth.initialize_default_users()
        print("   ✅ Default users initialized!")
    except Exception as e:
        print(f"   ❌ Error initializing users: {e}")
        return False
    
    # Test 4: Query test
    print("\n4. Testing database queries...")
    try:
        users = auth.get_all_users()
        print(f"   ✅ Found {len(users)} user(s) in database")
        for username in users:
            print(f"      - {username} ({users[username]['role']})")
    except Exception as e:
        print(f"   ❌ Error querying users: {e}")
        return False
    
    print("\n" + "="*50)
    print("✅ All tests passed! Database is ready to use.")
    print("="*50)
    return True

if __name__ == "__main__":
    try:
        test_connection()
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted by user")
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
    finally:
        db.close_pool()

