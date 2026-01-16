import argparse
import pandas as pd
import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from tqdm import tqdm
from dotenv import load_dotenv
from urllib.parse import urlparse, urlunparse

try:
    import psycopg2
    from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False

# Configuration
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
CHUNK_SIZE = 10000  # Process 10k rows at a time
FIELDS = [
    "chunk_id",
    "key_sentences",
    "cell_type",
    "cytokine_name",
    "confidence_score",
    "cytokine_effect",
    "cytokine_effect_original",
    "regulated_genes",
    "gene_response_type",
    "regulated_pathways",
    "pathway_response_type",
    "regulated_cell_processes",
    "cell_process_category",
    "cell_process_response_type",
    "species",
    "necessary_condition",
    "experimental_concentration",
    "experimental_perturbation",
    "experimental_readout",
    "experimental_readout_category",
    "experimental_system_type",
    "experimental_system_details",
    "experimental_time_point",
    "causality_type",
    "causality_description",
    "publication_type",
    "mapped_citation_id",
    "url"
]

def ensure_database_exists(database_url):
    """Create the database if it doesn't exist"""
    try:
        # Parse the database URL
        parsed = urlparse(database_url)
        db_name = parsed.path.lstrip('/')
        
        if not db_name:
            print("⚠ Warning: No database name found in DATABASE_URL")
            return database_url
        
        # Create a connection URL to the default 'postgres' database
        default_db_url = urlunparse((
            parsed.scheme,
            parsed.netloc,
            '/postgres',  # Connect to default postgres database
            parsed.params,
            parsed.query,
            parsed.fragment
        ))
        
        # Try to connect to the target database first
        try:
            test_engine = create_engine(database_url)
            with test_engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            print(f"✓ Database '{db_name}' already exists")
            return database_url
        except OperationalError as e:
            # Check if the error is specifically about database not existing
            error_msg = str(e).lower()
            if 'does not exist' in error_msg or 'database' in error_msg and 'not exist' in error_msg:
                # Database doesn't exist, create it
                print(f"Database '{db_name}' does not exist. Creating it...")
            else:
                # Some other connection error - re-raise it
                raise
            
            # Connect to default postgres database to create the new database
            if not PSYCOPG2_AVAILABLE:
                print(f"⚠ Warning: psycopg2 not available. Cannot auto-create database.")
                print(f"  Please create the database manually:")
                print(f"  createdb {db_name}")
                return database_url
            
            # Parse connection details for psycopg2
            parsed_default = urlparse(default_db_url)
            conn_params = {
                'host': parsed_default.hostname,
                'port': parsed_default.port or 5432,
                'user': parsed_default.username,
                'password': parsed_default.password,
                'database': 'postgres'
            }
            
            # Remove None values
            conn_params = {k: v for k, v in conn_params.items() if v is not None}
            
            try:
                conn = psycopg2.connect(**conn_params)
                conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
                cursor = conn.cursor()
                
                # Check if database exists
                cursor.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (db_name,)
                )
                if cursor.fetchone():
                    print(f"✓ Database '{db_name}' already exists")
                else:
                    # Create the database
                    # Escape the database name (psycopg2 will handle quoting)
                    cursor.execute(f'CREATE DATABASE "{db_name}"')
                    print(f"✓ Created database '{db_name}'")
                
                cursor.close()
                conn.close()
            except Exception as e:
                print(f"⚠ Warning: Could not create database: {e}")
                print(f"  You may need to create the database manually:")
                print(f"  createdb {db_name}")
                # Continue anyway - the connection attempt will show the actual error
            return database_url
            
    except Exception as e:
        print(f"⚠ Warning: Could not ensure database exists: {e}")
        print("  Attempting to continue with existing connection...")
        return database_url

def create_tables(engine):
    """Create the interactions table with proper schema"""
    print("Creating database tables...")
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS public.cytokine_effects (
        id BIGSERIAL PRIMARY KEY,
        chunk_id TEXT,
        key_sentences TEXT,
        cell_type TEXT,
        cytokine_name TEXT,
        confidence_score FLOAT,
        cytokine_effect TEXT,
        cytokine_effect_original TEXT,
        regulated_genes TEXT,
        gene_response_type TEXT,
        regulated_pathways TEXT,
        pathway_response_type TEXT,
        regulated_cell_processes TEXT,
        cell_process_category TEXT,
        cell_process_response_type TEXT,
        species TEXT,
        necessary_condition TEXT,
        experimental_concentration TEXT,
        experimental_perturbation TEXT,
        experimental_readout TEXT,
        experimental_readout_category TEXT,
        experimental_system_type TEXT,
        experimental_system_details TEXT,
        experimental_time_point TEXT,
        causality_type TEXT,
        causality_description TEXT,
        publication_type TEXT,
        mapped_citation_id TEXT,
        url TEXT
    );
    """
    
    with engine.connect() as conn:
        conn.execute(text(create_table_sql))
        conn.commit()
    
    print("✓ Tables created successfully")

def create_indexes(engine):
    """Create indexes on frequently queried columns"""
    print("Creating indexes for better query performance...")
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_cytokine_name ON cytokine_effects(cytokine_name);",
        "CREATE INDEX IF NOT EXISTS idx_cell_type ON cytokine_effects(cell_type);",
        "CREATE INDEX IF NOT EXISTS idx_species ON cytokine_effects(species);",
        "CREATE INDEX IF NOT EXISTS idx_experimental_system_type ON cytokine_effects(experimental_system_type);",
        "CREATE INDEX IF NOT EXISTS idx_publication_type ON cytokine_effects(publication_type);",
        "CREATE INDEX IF NOT EXISTS idx_confidence_score ON cytokine_effects(confidence_score);",
        # Full-text search indexes for text columns
        "CREATE INDEX IF NOT EXISTS idx_regulated_genes_fts ON cytokine_effects USING gin(to_tsvector('english', COALESCE(regulated_genes, '')));",
        "CREATE INDEX IF NOT EXISTS idx_regulated_pathways_fts ON cytokine_effects USING gin(to_tsvector('english', COALESCE(regulated_pathways, '')));"
    ]
    
    with engine.connect() as conn:
        for idx_sql in indexes:
            try:
                conn.execute(text(idx_sql))
                conn.commit()
                print(f"✓ Created index")
            except Exception as e:
                print(f"⚠ Index creation warning: {e}")
    
    print("✓ All indexes created")

def import_csv(csv_file, engine):
    """Import CSV file into database in chunks"""
    
    if not os.path.exists(csv_file):
        print(f"❌ Error: CSV file '{csv_file}' not found!")
        sys.exit(1)
    
    print(f"Starting import of {csv_file}...")
    print(f"Chunk size: {CHUNK_SIZE} rows")
    
    # Get total rows for progress bar
    print("Counting total rows...")
    total_rows = sum(1 for _ in open(csv_file)) - 1  # Subtract header
    print(f"Total rows to import: {total_rows:,}")
    
    # Import in chunks
    chunk_iterator = pd.read_csv(csv_file, chunksize=CHUNK_SIZE, low_memory=False)
    
    rows_imported = 0
    with tqdm(total=total_rows, desc="Importing") as pbar:
        for chunk_num, chunk in enumerate(chunk_iterator, 1):
            # Replace NaN with None for proper NULL values in database
            chunk = chunk.where(pd.notnull(chunk), None)
            chunk["cytokine_name"] = chunk["cytokine_name"].apply(lambda x: x.split(';'))
            chunk = chunk.explode("cytokine_name").reset_index(drop=True)
            
            # Write to database
            if len(chunk):
                chunk = chunk[FIELDS]
                chunk.to_sql(
                    'cytokine_effects', engine, if_exists='append', index=False, method='multi', schema='public',
                )
            
            rows_imported += len(chunk)
            pbar.update(len(chunk))
            
            if chunk_num % 10 == 0:
                print(f"  Processed {rows_imported:,} / {total_rows:,} rows...")
    
    print(f"✓ Import complete! Total rows imported: {rows_imported:,}")

def verify_import(engine):
    """Verify the import was successful"""
    print("\nVerifying import...")
    
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM cytokine_effects"))
        count = result.scalar()
        print(f"✓ Total rows in database: {count:,}")
        
        # Sample query
        result = conn.execute(text("SELECT cytokine_name, cell_type, species FROM cytokine_effects LIMIT 5"))
        print("\nSample data:")
        for row in result:
            print(f"  Cytokine: {row[0]}, Cell Type: {row[1]}, Species: {row[2]}")

def main(args):
    print("=" * 60)
    print("Cytokine Knowledgebase - CSV Import Tool")
    print("=" * 60)
    print()
    csv_file = args.file
    assert csv_file.endswith(".csv"), "CSV file is required"
    assert os.path.exists(csv_file), f"CSV file {csv_file} does not exist"

    # Ensure database exists
    if not DATABASE_URL:
        print("❌ Error: DATABASE_URL environment variable is not set!")
        sys.exit(1)
    
    print("Checking database connection...")
    database_url = ensure_database_exists(DATABASE_URL)
    print()

    # Create engine
    try:
        engine = create_engine(database_url)
        # Test connection
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"✓ Connected to database: {database_url.split('@')[1] if '@' in database_url else 'local'}")
    except Exception as e:
        print(f"❌ Error connecting to database: {str(e)[:100]}")
        sys.exit(1)
    print()
    
    # Execute import steps
    try:
        # Step 1: Create tables
        create_tables(engine)
        print()
        
        # Step 2: Import CSV data
        import_csv(csv_file, engine)
        print()
        
        # Step 3: Create indexes
        create_indexes(engine)
        print()
        
        # Step 4: Verify
        verify_import(engine)
        print()
        
        print("=" * 60)
        print("✓ IMPORT COMPLETED SUCCESSFULLY!")
        print("=" * 60)
        print("\nYou can now start the FastAPI server with:")
        print("  uvicorn main:app --reload")
        
    except Exception as e:
        print(f"\n❌ Error during import: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Import CSV file into PostgreSQL database")
    parser.add_argument("--file", "-f", type=str, default="sample_data.csv", help="Path to the CSV file to import")
    args = parser.parse_args()
    main(args)