import pandas as pd
import os
import sys
from sqlalchemy import create_engine, text
from tqdm import tqdm
from dotenv import load_dotenv

# Configuration
load_dotenv()
CSV_FILE = "sample_data.csv"  # Update with your CSV file path
DATABASE_URL = os.getenv("DATABASE_URL")
CHUNK_SIZE = 10000  # Process 10k rows at a time
FIELDS = [
    "cytokine_name",
    "cell_type",
    "cytokine_effect",
    "causality_type",
    "species",
    "chunk_id",
    "key_sentences",
    "citation_id"
]

def create_tables(engine):
    """Create the interactions table with proper schema"""
    print("Creating database tables...")
    
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS public.cytokine_effects (
        id BIGSERIAL PRIMARY KEY,
        cytokine_name VARCHAR(500),
        cell_type VARCHAR(500),
        cytokine_effect TEXT,
        causality_type VARCHAR(500),
        species VARCHAR(500),
        chunk_id VARCHAR(500),
        key_sentences TEXT,
        citation_id VARCHAR(500)
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
        "CREATE INDEX IF NOT EXISTS idx_causality_type ON cytokine_effects(causality_type);",
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

def main():
    print("=" * 60)
    print("Cytokine Knowledgebase - CSV Import Tool")
    print("=" * 60)
    print()
    
    # Create engine
    try:
        engine = create_engine(DATABASE_URL)
        print(f"✓ Connected to database: {DATABASE_URL.split('@')[1] if '@' in DATABASE_URL else 'local'}")
    except Exception as e:
        print(f"❌ Error connecting to database: {str(e)[:100]}")
        sys.exit(1)
    
    # Check if CSV file exists
    if not os.path.exists(CSV_FILE):
        print(f"❌ Error: CSV file '{CSV_FILE}' not found!")
        print(f"Please update CSV_FILE path in the script or set it as an environment variable.")
        sys.exit(1)
    
    print()
    
    # # Confirm before proceeding
    # response = input(f"This will import data from '{CSV_FILE}' into the database.\nProceed? (yes/no): ")
    # if response.lower() not in ['yes', 'y']:
    #     print("Import cancelled.")
    #     sys.exit(0)
    
    print()
    
    # Execute import steps
    try:
        # Step 1: Create tables
        create_tables(engine)
        print()
        
        # Step 2: Import CSV data
        import_csv(CSV_FILE, engine)
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
    main()