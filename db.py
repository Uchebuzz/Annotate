"""
Database connection and initialization module for PostgreSQL.

This module handles:
- Database connection management
- Schema initialization
- Connection pooling
"""

import os
import psycopg2
from psycopg2 import pool, sql
from psycopg2.extras import RealDictCursor
from typing import Optional, Dict, List
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Database configuration from environment variables
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "annotation_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")

# Connection pool (thread-safe)
_connection_pool: Optional[pool.ThreadedConnectionPool] = None

logger = logging.getLogger(__name__)


def init_connection_pool(min_conn: int = 1, max_conn: int = 10):
    """
    Initialize the database connection pool.
    
    Args:
        min_conn: Minimum number of connections in the pool
        max_conn: Maximum number of connections in the pool
    """
    global _connection_pool
    
    if _connection_pool is not None:
        return
    
    try:
        _connection_pool = pool.ThreadedConnectionPool(
            min_conn,
            max_conn,
            host=DB_HOST,
            port=DB_PORT,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        logger.info("Database connection pool initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing connection pool: {e}")
        raise


def get_connection():
    """
    Get a connection from the pool.
    
    Returns:
        psycopg2 connection object
        
    Raises:
        Exception if pool is not initialized or connection fails
    """
    if _connection_pool is None:
        init_connection_pool()
    
    return _connection_pool.getconn()


def return_connection(conn):
    """Return a connection to the pool."""
    if _connection_pool is not None:
        _connection_pool.putconn(conn)


def close_pool():
    """Close all connections in the pool."""
    global _connection_pool
    if _connection_pool is not None:
        _connection_pool.closeall()
        _connection_pool = None


def init_database():
    """
    Initialize the database schema.
    Creates tables if they don't exist.
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        
        # Create users table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(255) UNIQUE NOT NULL,
                password_hash VARCHAR(255) NOT NULL,
                role VARCHAR(50) NOT NULL DEFAULT 'tester',
                user_id VARCHAR(255) NOT NULL,
                password_changed BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_login TIMESTAMP,
                CONSTRAINT role_check CHECK (role IN ('admin', 'tester'))
            )
        """)
        
        # Create index on username for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)
        """)
        
        # Create index on user_id for faster lookups
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_users_user_id ON users(user_id)
        """)
        
        # Create user_sessions table to track sign-ins
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_sessions (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
                username VARCHAR(255) NOT NULL,
                login_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                logout_timestamp TIMESTAMP,
                ip_address VARCHAR(45),
                user_agent TEXT,
                CONSTRAINT fk_user FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        
        # Create index on user_id for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_user_id ON user_sessions(user_id)
        """)
        
        # Create index on login_timestamp for time-based queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sessions_login_time ON user_sessions(login_timestamp)
        """)
        
        conn.commit()
        logger.info("Database schema initialized successfully")
        
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error initializing database: {e}")
        raise
    finally:
        if conn:
            return_connection(conn)


def test_connection() -> bool:
    """
    Test database connection.
    
    Returns:
        True if connection successful, False otherwise
    """
    conn = None
    try:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False
    finally:
        if conn:
            return_connection(conn)


# Context manager for database connections
class DatabaseConnection:
    """Context manager for database connections."""
    
    def __init__(self):
        self.conn = None
    
    def __enter__(self):
        self.conn = get_connection()
        return self.conn
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            if exc_type is not None:
                self.conn.rollback()
            else:
                self.conn.commit()
            return_connection(self.conn)
        return False

