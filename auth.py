"""
Authentication module for managing user sessions and credentials.

This module handles:
- User authentication with password hashing
- Session state management
- User registration (for initial setup)
"""

import hashlib
import json
import os
import streamlit as  st
from typing import Optional, Dict, Tuple


USER_DB_FILE = "users.json"
DEFAULT_ADMIN_USER = "admin"
DEFAULT_ADMIN_PASS = "AI_admin1223"  # Should be changed in production


def hash_password(password: str) -> str:
    """Hash a password using SHA-256."""
    return hashlib.sha256(password.encode()).hexdigest()


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
    """Initialize default admin user if no users exist."""
    users = load_users()
    if not users:
        users[DEFAULT_ADMIN_USER] = {
            "password_hash": hash_password(DEFAULT_ADMIN_PASS),
            "role": "admin",
            "user_id": DEFAULT_ADMIN_USER
        }
        save_users(users)


def verify_password(username: str, password: str) -> bool:
    """Verify if the provided password matches the user's stored hash."""
    users = load_users()
    if username in users:
        password_hash = hash_password(password)
        return users[username]["password_hash"] == password_hash
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
        "user_id": username
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

