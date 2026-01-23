"""
Authentication module for managing user sessions and credentials.

This module handles:
- User authentication with secure password hashing (bcrypt)
- Session state management
- User registration (for initial setup)
- Password change functionality
- User sign-in tracking with PostgreSQL
"""

import os
import bcrypt
import streamlit as st
from typing import Optional, Dict, Tuple, List
from dotenv import load_dotenv
from datetime import datetime
import logging

# Import database module
import db

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

DEFAULT_ADMIN_USER = "admin"
# Get default password from environment variable, fallback to secure default
# IMPORTANT: Set ADMIN_PASSWORD in .env file or environment variable
DEFAULT_ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "CHANGE_ME_ON_FIRST_LOGIN")

# Database will be initialized on first use


def hash_password(password: str) -> str:
    """
    Hash a password using bcrypt (secure password hashing).
    
    Args:
        password: Plain text password
        
    Returns:
        Bcrypt hashed password string
    """
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password_hash(hashed: str, password: str) -> bool:
    """
    Verify a password against a bcrypt hash.
    
    Args:
        hashed: Bcrypt hashed password
        password: Plain text password to verify
        
    Returns:
        True if password matches, False otherwise
    """
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        # Fallback for old SHA-256 hashes (migration support)
        import hashlib
        old_hash = hashlib.sha256(password.encode()).hexdigest()
        return old_hash == hashed


def load_users() -> Dict[str, Dict]:
    """Load users from the database."""
    users = {}
    try:
        with db.DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT username, password_hash, role, user_id, password_changed, created_at
                FROM users
            """)
            rows = cursor.fetchall()
            for row in rows:
                users[row[0]] = {
                    "password_hash": row[1],
                    "role": row[2],
                    "user_id": row[3],
                    "password_changed": row[4],
                    "created_at": row[5].isoformat() if row[5] else None
                }
    except Exception as e:
        logger.error(f"Error loading users: {e}")
    return users


def initialize_default_users():
    """
    Initialize default admin user if no users exist.
    
    Note: The default password should be changed immediately after first login.
    Set ADMIN_PASSWORD environment variable for a custom default password.
    """
    try:
        # Ensure database schema is initialized
        db.init_database()
        
        with db.DatabaseConnection() as conn:
            cursor = conn.cursor()
            # Check if any users exist
            cursor.execute("SELECT COUNT(*) FROM users")
            count = cursor.fetchone()[0]
            
            if count == 0:
                # Only create default admin if no users exist
                cursor.execute("""
                    INSERT INTO users (username, password_hash, role, user_id, password_changed)
                    VALUES (%s, %s, %s, %s, %s)
                """, (
                    DEFAULT_ADMIN_USER,
                    hash_password(DEFAULT_ADMIN_PASS),
                    "admin",
                    DEFAULT_ADMIN_USER,
                    False
                ))
                conn.commit()
                logger.info("Default admin user created")
    except Exception as e:
        logger.error(f"Error initializing default users: {e}")


def verify_password(username: str, password: str) -> bool:
    """
    Verify if the provided password matches the user's stored hash.
    
    Args:
        username: Username to verify
        password: Plain text password to verify
        
    Returns:
        True if password is correct, False otherwise
    """
    try:
        with db.DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT password_hash FROM users WHERE username = %s
            """, (username,))
            row = cursor.fetchone()
            if row:
                stored_hash = row[0]
                return verify_password_hash(stored_hash, password)
    except Exception as e:
        logger.error(f"Error verifying password: {e}")
    return False


def get_user_role(username: str) -> Optional[str]:
    """Get the role of a user (admin or tester)."""
    try:
        with db.DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
            row = cursor.fetchone()
            if row:
                return row[0]
    except Exception as e:
        logger.error(f"Error getting user role: {e}")
    return None


def get_user_id(username: str) -> Optional[str]:
    """Get the user ID for a username."""
    try:
        with db.DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id FROM users WHERE username = %s", (username,))
            row = cursor.fetchone()
            if row:
                return row[0]
    except Exception as e:
        logger.error(f"Error getting user ID: {e}")
    return None


def record_signin(username: str, ip_address: Optional[str] = None, user_agent: Optional[str] = None):
    """
    Record a user sign-in event in the database.
    
    Args:
        username: Username of the user signing in
        ip_address: Optional IP address of the user
        user_agent: Optional user agent string
    """
    try:
        with db.DatabaseConnection() as conn:
            cursor = conn.cursor()
            # Get user ID
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            user_row = cursor.fetchone()
            if user_row:
                user_db_id = user_row[0]
                # Record sign-in
                cursor.execute("""
                    INSERT INTO user_sessions (user_id, username, ip_address, user_agent)
                    VALUES (%s, %s, %s, %s)
                """, (user_db_id, username, ip_address, user_agent))
                # Update last_login timestamp
                cursor.execute("""
                    UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE id = %s
                """, (user_db_id,))
                conn.commit()
    except Exception as e:
        logger.error(f"Error recording sign-in: {e}")


def login(username: str, password: str) -> bool:
    """
    Authenticate a user and set session state.
    
    Returns:
        True if login successful, False otherwise
    """
    if verify_password(username, password):
        st.session_state["authenticated"] = True
        st.session_state["username"] = username
        st.session_state["user_id"] = get_user_id(username)
        st.session_state["role"] = get_user_role(username)
        
        # Record sign-in in database
        # Try to get IP and user agent from Streamlit (if available)
        try:
            # Streamlit doesn't directly expose these, but we can try
            ip_address = None
            user_agent = None
            # You can extend this to get actual request info if needed
            record_signin(username, ip_address, user_agent)
        except Exception as e:
            logger.warning(f"Could not record sign-in: {e}")
        
        return True
    return False


def logout():
    """Clear authentication from session state."""
    # Optionally record logout time (if we track active sessions)
    for key in ["authenticated", "username", "user_id", "role"]:
        if key in st.session_state:
            del st.session_state[key]


def is_authenticated() -> bool:
    """Check if the current session is authenticated."""
    return st.session_state.get("authenticated", False)


def get_current_user() -> Optional[str]:
    """Get the current authenticated username."""
    if is_authenticated():
        return st.session_state.get("username")
    return None


def get_current_user_id() -> Optional[str]:
    """Get the current authenticated user ID."""
    if is_authenticated():
        return st.session_state.get("user_id")
    return None


def is_admin() -> bool:
    """Check if the current user is an admin."""
    return st.session_state.get("role") == "admin"


def register_user(username: str, password: str, role: str = "tester") -> Tuple[bool, str]:
    """
    Register a new user.
    
    Returns:
        (success: bool, message: str)
    """
    if not username or not password:
        return False, "Username and password are required"
    
    if role not in ["admin", "tester"]:
        return False, "Invalid role. Must be 'admin' or 'tester'"
    
    try:
        with db.DatabaseConnection() as conn:
            cursor = conn.cursor()
            # Check if username already exists
            cursor.execute("SELECT COUNT(*) FROM users WHERE username = %s", (username,))
            if cursor.fetchone()[0] > 0:
                return False, "Username already exists"
            
            # Insert new user
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, user_id, password_changed)
                VALUES (%s, %s, %s, %s, %s)
            """, (
                username,
                hash_password(password),
                role,
                username,  # user_id defaults to username
                True  # New users set their own password, so it's "changed"
            ))
            conn.commit()
            return True, f"User {username} registered successfully"
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        return False, f"Error registering user: {str(e)}"


def get_all_users() -> Dict[str, Dict]:
    """
    Get all users from the database.
    
    Returns:
        Dictionary of all users {username: {role, user_id, ...}}
    """
    return load_users()


def get_all_testers() -> Dict[str, Dict]:
    """
    Get all tester users (non-admin users).
    
    Returns:
        Dictionary of tester users {username: {role, user_id, ...}}
    """
    users = load_users()
    return {username: user_data for username, user_data in users.items() 
            if user_data.get("role") != "admin"}


def change_password(username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
    """
    Change a user's password.
    
    Args:
        username: Username whose password to change
        old_password: Current password (for verification)
        new_password: New password to set
        
    Returns:
        (success: bool, message: str)
    """
    # Verify old password
    if not verify_password(username, old_password):
        return False, "Current password is incorrect"
    
    # Validate new password
    if not new_password or len(new_password) < 6:
        return False, "New password must be at least 6 characters long"
    
    try:
        with db.DatabaseConnection() as conn:
            cursor = conn.cursor()
            # Update password
            cursor.execute("""
                UPDATE users 
                SET password_hash = %s, password_changed = TRUE 
                WHERE username = %s
            """, (hash_password(new_password), username))
            
            if cursor.rowcount == 0:
                return False, "User not found"
            
            conn.commit()
            return True, "Password changed successfully"
    except Exception as e:
        logger.error(f"Error changing password: {e}")
        return False, f"Error changing password: {str(e)}"


def requires_password_change(username: str) -> bool:
    """
    Check if a user needs to change their password (e.g., using default password).
    
    Args:
        username: Username to check
        
    Returns:
        True if password change is required, False otherwise
    """
    try:
        with db.DatabaseConnection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT password_changed FROM users WHERE username = %s
            """, (username,))
            row = cursor.fetchone()
            if row:
                return not row[0]  # Returns True if password_changed is False
    except Exception as e:
        logger.error(f"Error checking password change requirement: {e}")
    return False


def delete_user(username: str, current_username: str) -> Tuple[bool, str]:
    """
    Delete a user from the system.
    
    Note: This does NOT delete their annotations - annotations are preserved
    with the user_id and username for historical record.
    
    Args:
        username: Username to delete
        current_username: Username of the person performing the deletion (for validation)
        
    Returns:
        (success: bool, message: str)
    """
    # Prevent self-deletion
    if username == current_username:
        return False, "You cannot delete your own account"
    
    try:
        with db.DatabaseConnection() as conn:
            cursor = conn.cursor()
            # Check if user exists and get role
            cursor.execute("SELECT role FROM users WHERE username = %s", (username,))
            row = cursor.fetchone()
            if not row:
                return False, "User not found"
            
            # Prevent deleting admin users (optional safety check)
            if row[0] == "admin":
                return False, "Cannot delete admin users"
            
            # Delete the user (cascade will delete sessions)
            cursor.execute("DELETE FROM users WHERE username = %s", (username,))
            conn.commit()
            
            if cursor.rowcount == 0:
                return False, "User not found"
            
            return True, f"User {username} deleted successfully. Their annotations have been preserved."
    except Exception as e:
        logger.error(f"Error deleting user: {e}")
        return False, f"Error deleting user: {str(e)}"


def get_signin_history(username: Optional[str] = None, limit: int = 100) -> List[Dict]:
    """
    Get sign-in history for a user or all users.
    
    Args:
        username: Optional username to filter by. If None, returns all sign-ins.
        limit: Maximum number of records to return
        
    Returns:
        List of sign-in records with username, login_timestamp, ip_address, etc.
    """
    try:
        with db.DatabaseConnection() as conn:
            cursor = conn.cursor()
            if username:
                cursor.execute("""
                    SELECT username, login_timestamp, ip_address, user_agent
                    FROM user_sessions
                    WHERE username = %s
                    ORDER BY login_timestamp DESC
                    LIMIT %s
                """, (username, limit))
            else:
                cursor.execute("""
                    SELECT username, login_timestamp, ip_address, user_agent
                    FROM user_sessions
                    ORDER BY login_timestamp DESC
                    LIMIT %s
                """, (limit,))
            
            rows = cursor.fetchall()
            return [
                {
                    "username": row[0],
                    "login_timestamp": row[1].isoformat() if row[1] else None,
                    "ip_address": row[2],
                    "user_agent": row[3]
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Error getting sign-in history: {e}")
        return []
