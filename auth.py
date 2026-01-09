"""
Authentication module for managing user sessions and credentials.

This module handles:
- User authentication with secure password hashing (bcrypt)
- Session state management
- User registration (for initial setup)
- Password change functionality
"""

import json
import os
import bcrypt
import streamlit as st
from typing import Optional, Dict, Tuple
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

USER_DB_FILE = "users.json"
DEFAULT_ADMIN_USER = "admin"
# Get default password from environment variable, fallback to secure default
# IMPORTANT: Set ADMIN_PASSWORD in .env file or environment variable
DEFAULT_ADMIN_PASS = os.getenv("ADMIN_PASSWORD", "CHANGE_ME_ON_FIRST_LOGIN")


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
    """Load users from the users database file."""
    if os.path.exists(USER_DB_FILE):
        try:
            with open(USER_DB_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}
    return {}


def save_users(users: Dict[str, Dict]) -> None:
    """Save users to the users database file."""
    with open(USER_DB_FILE, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=2)


def initialize_default_users():
    """
    Initialize default admin user if no users exist.
    
    Note: The default password should be changed immediately after first login.
    Set ADMIN_PASSWORD environment variable for a custom default password.
    """
    users = load_users()
    if not users:
        # Only create default admin if no users exist
        users[DEFAULT_ADMIN_USER] = {
            "password_hash": hash_password(DEFAULT_ADMIN_PASS),
            "role": "admin",
            "user_id": DEFAULT_ADMIN_USER,
            "password_changed": False,  # Track if default password has been changed
            "created_at": None  # Can be used for tracking
        }
        save_users(users)


def verify_password(username: str, password: str) -> bool:
    """
    Verify if the provided password matches the user's stored hash.
    
    Args:
        username: Username to verify
        password: Plain text password to verify
        
    Returns:
        True if password is correct, False otherwise
    """
    users = load_users()
    if username in users:
        stored_hash = users[username]["password_hash"]
        return verify_password_hash(stored_hash, password)
    return False


def get_user_role(username: str) -> Optional[str]:
    """Get the role of a user (admin or tester)."""
    users = load_users()
    if username in users:
        return users[username].get("role", "tester")
    return None


def get_user_id(username: str) -> Optional[str]:
    """Get the user ID for a username."""
    users = load_users()
    if username in users:
        return users[username].get("user_id", username)
    return None


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
        return True
    return False


def logout():
    """Clear authentication from session state."""
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
    users = load_users()
    
    if username in users:
        return False, "Username already exists"
    
    if not username or not password:
        return False, "Username and password are required"
    
    users[username] = {
        "password_hash": hash_password(password),
        "role": role,
        "user_id": username,
        "password_changed": True  # New users set their own password, so it's "changed"
    }
    save_users(users)
    return True, f"User {username} registered successfully"


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
    users = load_users()
    
    if username not in users:
        return False, "User not found"
    
    # Verify old password
    if not verify_password(username, old_password):
        return False, "Current password is incorrect"
    
    # Validate new password
    if not new_password or len(new_password) < 6:
        return False, "New password must be at least 6 characters long"
    
    # Update password
    users[username]["password_hash"] = hash_password(new_password)
    users[username]["password_changed"] = True
    save_users(users)
    
    return True, "Password changed successfully"


def requires_password_change(username: str) -> bool:
    """
    Check if a user needs to change their password (e.g., using default password).
    
    Args:
        username: Username to check
        
    Returns:
        True if password change is required, False otherwise
    """
    users = load_users()
    if username in users:
        return not users[username].get("password_changed", True)
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
    users = load_users()
    
    if username not in users:
        return False, "User not found"
    
    # Prevent self-deletion
    if username == current_username:
        return False, "You cannot delete your own account"
    
    # Prevent deleting admin users (optional safety check)
    if users[username].get("role") == "admin":
        return False, "Cannot delete admin users"
    
    # Delete the user
    del users[username]
    save_users(users)
    
    return True, f"User {username} deleted successfully. Their annotations have been preserved."

