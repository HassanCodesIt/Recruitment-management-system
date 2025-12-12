"""
Database connection and utility module for Recruitment Management System
"""

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
from contextlib import contextmanager
import logging
from typing import Optional, Dict, List, Any

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

# Database configuration
DB_CONFIG = {
    "dbname": os.getenv("DB_NAME", "recruitment_management_system"),
    "user": os.getenv("DB_USER", "postgres"),
    "password": os.getenv("DB_PASSWORD"),
    "host": os.getenv("DB_HOST", "localhost"),
    "port": os.getenv("DB_PORT", "5432")
}


class DatabaseConnection:
    """Database connection pool manager"""
    
    _pool = None
    
    @classmethod
    def initialize_pool(cls, minconn=1, maxconn=10):
        """Initialize connection pool"""
        if cls._pool is None:
            try:
                cls._pool = psycopg2.pool.SimpleConnectionPool(
                    minconn,
                    maxconn,
                    **DB_CONFIG
                )
                logger.info("✅ Database connection pool initialized")
            except Exception as e:
                logger.error(f"❌ Failed to initialize connection pool: {e}")
                raise
    
    @classmethod
    def get_connection(cls):
        """Get a connection from the pool"""
        if cls._pool is None:
            cls.initialize_pool()
        return cls._pool.getconn()
    
    @classmethod
    def return_connection(cls, conn):
        """Return a connection to the pool"""
        if cls._pool is not None:
            cls._pool.putconn(conn)
    
    @classmethod
    def close_all_connections(cls):
        """Close all connections in the pool"""
        if cls._pool is not None:
            cls._pool.closeall()
            logger.info("✅ All database connections closed")


@contextmanager
def get_db_connection():
    """Context manager for database connection"""
    conn = None
    try:
        conn = DatabaseConnection.get_connection()
        yield conn
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Database error: {e}")
        raise
    finally:
        if conn:
            DatabaseConnection.return_connection(conn)


@contextmanager
def get_db_cursor(commit=True):
    """Context manager for database cursor with auto-commit"""
    conn = None
    cursor = None
    try:
        conn = DatabaseConnection.get_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        yield cursor
        if commit:
            conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"❌ Database error: {e}")
        raise
    finally:
        if cursor:
            cursor.close()
        if conn:
            DatabaseConnection.return_connection(conn)


def execute_query(query: str, params: tuple = None, fetch_one=False, fetch_all=False) -> Optional[Any]:
    """Execute a query and optionally fetch results"""
    with get_db_cursor() as cursor:
        cursor.execute(query, params)
        
        if fetch_one:
            return cursor.fetchone()
        elif fetch_all:
            return cursor.fetchall()
        return None


def insert_record(table: str, data: Dict[str, Any]) -> Optional[int]:
    """Insert a record and return the ID"""
    columns = ', '.join(data.keys())
    placeholders = ', '.join(['%s'] * len(data))
    query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders}) RETURNING id"
    
    with get_db_cursor() as cursor:
        cursor.execute(query, tuple(data.values()))
        result = cursor.fetchone()
        return result['id'] if result else None


def update_record(table: str, record_id: int, data: Dict[str, Any]) -> bool:
    """Update a record by ID"""
    set_clause = ', '.join([f"{k} = %s" for k in data.keys()])
    query = f"UPDATE {table} SET {set_clause} WHERE id = %s"
    
    with get_db_cursor() as cursor:
        cursor.execute(query, tuple(data.values()) + (record_id,))
        return cursor.rowcount > 0


def delete_record(table: str, record_id: int) -> bool:
    """Delete a record by ID"""
    query = f"DELETE FROM {table} WHERE id = %s"
    
    with get_db_cursor() as cursor:
        cursor.execute(query, (record_id,))
        return cursor.rowcount > 0


def get_record_by_id(table: str, record_id: int) -> Optional[Dict]:
    """Get a record by ID"""
    query = f"SELECT * FROM {table} WHERE id = %s"
    return execute_query(query, (record_id,), fetch_one=True)


def get_all_records(table: str, where: str = None, params: tuple = None, 
                    order_by: str = None, limit: int = None) -> List[Dict]:
    """Get all records from a table with optional filters"""
    query = f"SELECT * FROM {table}"
    
    if where:
        query += f" WHERE {where}"
    
    if order_by:
        query += f" ORDER BY {order_by}"
    
    if limit:
        query += f" LIMIT {limit}"
    
    return execute_query(query, params, fetch_all=True) or []


def test_connection() -> bool:
    """Test database connection"""
    try:
        with get_db_cursor() as cursor:
            cursor.execute("SELECT 1")
            result = cursor.fetchone()
            if result:
                logger.info("✅ Database connection successful")
                return True
    except Exception as e:
        logger.error(f"❌ Database connection failed: {e}")
        return False
    
    return False


# Initialize connection pool on module import
try:
    DatabaseConnection.initialize_pool()
except Exception as e:
    logger.warning(f"⚠️  Could not initialize database pool: {e}")


if __name__ == "__main__":
    # Test the database connection
    logging.basicConfig(level=logging.INFO)
    
    if test_connection():
        print("✅ Database module is working correctly")
        
        # Show available tables
        tables = execute_query("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """, fetch_all=True)
        
        print(f"\n📊 Available tables ({len(tables)}):")
        for table in tables:
            print(f"   - {table['table_name']}")
    else:
        print("❌ Database connection failed")
