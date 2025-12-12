"""
Database initialization script for Recruitment Management System
Creates database and runs schema setup
"""

import psycopg2
from psycopg2 import sql
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
import os
from dotenv import load_dotenv
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

DB_NAME = os.getenv("DB_NAME", "recruitment_management_system")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD")
DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")


def create_database():
    """Create the database if it doesn't exist"""
    try:
        # Connect to PostgreSQL server (default postgres database)
        conn = psycopg2.connect(
            dbname="postgres",
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Check if database exists
        cursor.execute(
            "SELECT 1 FROM pg_catalog.pg_database WHERE datname = %s",
            (DB_NAME,)
        )
        exists = cursor.fetchone()
        
        if not exists:
            # Create database
            cursor.execute(
                sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DB_NAME))
            )
            logger.info(f"✅ Database '{DB_NAME}' created successfully")
        else:
            logger.info(f"ℹ️  Database '{DB_NAME}' already exists")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error creating database: {e}")
        return False


def run_schema():
    """Run the schema SQL file to create tables"""
    try:
        # Connect to the target database
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        # Read schema file
        schema_file = Path(__file__).parent / "database_schema.sql"
        
        if not schema_file.exists():
            logger.error(f"❌ Schema file not found: {schema_file}")
            return False
        
        with open(schema_file, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # Execute schema
        cursor.execute(schema_sql)
        conn.commit()
        
        logger.info("✅ Database schema created successfully")
        
        # Verify tables were created
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        
        tables = cursor.fetchall()
        logger.info(f"📊 Created {len(tables)} tables:")
        for table in tables:
            logger.info(f"   - {table[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error running schema: {e}")
        if 'conn' in locals():
            conn.rollback()
            conn.close()
        return False


def verify_database():
    """Verify database setup is correct"""
    try:
        conn = psycopg2.connect(
            dbname=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD,
            host=DB_HOST,
            port=DB_PORT
        )
        cursor = conn.cursor()
        
        # Check required tables exist
        required_tables = [
            'candidates',
            'job_descriptions',
            'screening_results',
            'screening_history',
            'vacancy_recommendations',
            'email_logs',
            'analytics_metrics',
            'system_config'
        ]
        
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = set(required_tables) - set(existing_tables)
        
        if missing_tables:
            logger.warning(f"⚠️  Missing tables: {missing_tables}")
            return False
        
        logger.info("✅ All required tables exist")
        
        # Check system_config has default values
        cursor.execute("SELECT COUNT(*) FROM system_config")
        config_count = cursor.fetchone()[0]
        logger.info(f"✅ System configuration entries: {config_count}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error verifying database: {e}")
        return False


def initialize_database():
    """Main initialization function"""
    logger.info("🚀 Starting database initialization...")
    logger.info(f"📋 Target database: {DB_NAME}")
    logger.info(f"📋 Host: {DB_HOST}:{DB_PORT}")
    logger.info(f"📋 User: {DB_USER}")
    
    # Step 1: Create database
    if not create_database():
        logger.error("❌ Failed to create database. Exiting.")
        return False
    
    # Step 2: Run schema
    if not run_schema():
        logger.error("❌ Failed to run schema. Exiting.")
        return False
    
    # Step 3: Verify setup
    if not verify_database():
        logger.error("❌ Database verification failed. Exiting.")
        return False
    
    logger.info("=" * 60)
    logger.info("🎉 Database initialization completed successfully!")
    logger.info("=" * 60)
    logger.info("Next steps:")
    logger.info("  1. Install dependencies: pip install -r requirements.txt")
    logger.info("  2. Run the application: streamlit run app.py")
    logger.info("=" * 60)
    
    return True


if __name__ == "__main__":
    try:
        success = initialize_database()
        if not success:
            exit(1)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Initialization cancelled by user")
        exit(1)
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}")
        exit(1)
