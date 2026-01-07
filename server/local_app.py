from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Text, Float, select, func, or_, and_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import os
from contextlib import contextmanager

# Database setup
load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Database Model
# Database Model (pruned)
class CytokineInteraction(Base):
    __tablename__ = "cytokine_effects"

    id = Column(Integer, primary_key=True, index=True)
    cytokine_name = Column(String(200), index=True)
    cell_type = Column(String(500), index=True)
    cytokine_effect = Column(String(500))
    causality_type = Column(String(200))
    species = Column(String(200), index=True)
    chunk_id = Column(String(200))
    key_sentences = Column(Text)
    citation_id = Column(String(200))

# Pydantic models
class InteractionResponse(BaseModel):
    id: int
    data: Dict[str, Any]
    
    class Config:
        from_attributes = True

class PaginatedResponse(BaseModel):
    data: List[Dict[str, Any]]
    pagination: Dict[str, Any]
    filters: Dict[str, Any]

class FilterOptions(BaseModel):
    column: str
    values: List[str]

# FastAPI app
app = FastAPI(title="Cytokine Knowledgebase API", version="1.0.0")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@contextmanager
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# All available columns
ALL_COLUMNS = [
    "cytokine_name",
    "cell_type",
    "cytokine_effect",
    "causality_type",
    "species",
    "chunk_id",
    "key_sentences",
    "citation_id"
]

@app.get("/")
def root():
    return {"message": "Cytokine Knowledgebase API", "version": "1.0.0"}

@app.get("/api/interactions", response_model=PaginatedResponse)
def get_interactions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    fields: Optional[str] = Query(None, description="Comma-separated list of fields to return"),
    # Filter parameters
    cytokine_name: Optional[str] = None,
    cell_type: Optional[str] = None,
    species: Optional[str] = None,
    causality_type: Optional[str] = None,
    experimental_system_type: Optional[str] = None,
    publication_type: Optional[str] = None,
    # Search parameter
    search: Optional[str] = Query(None, description="Search across key fields")
):
    with get_db() as db:
        # Build query
        query = db.query(CytokineInteraction)
        
        # Apply filters
        filters = {}
        if cytokine_name:
            query = query.filter(CytokineInteraction.cytokine_name.ilike(f"%{cytokine_name}%"))
            filters['cytokine_name'] = cytokine_name
        if cell_type:
            query = query.filter(CytokineInteraction.cell_type.ilike(f"%{cell_type}%"))
            filters['cell_type'] = cell_type
        if species:
            query = query.filter(CytokineInteraction.species.ilike(f"%{species}%"))
            filters['species'] = species
        if causality_type:
            query = query.filter(CytokineInteraction.causality_type.ilike(f"%{causality_type}%"))
            filters['causality_type'] = causality_type
        if experimental_system_type:
            # This column is no longer in ALL_COLUMNS, so only filter if it exists in DB
            if hasattr(CytokineInteraction, "experimental_system_type"):
                query = query.filter(CytokineInteraction.experimental_system_type.ilike(f"%{experimental_system_type}%"))
            filters['experimental_system_type'] = experimental_system_type
        if publication_type:
            if hasattr(CytokineInteraction, "publication_type"):
                query = query.filter(CytokineInteraction.publication_type.ilike(f"%{publication_type}%"))
            filters['publication_type'] = publication_type
        
        # Global search only on available columns
        if search:
            search_filter = or_(
                CytokineInteraction.cytokine_name.ilike(f"%{search}%"),
                CytokineInteraction.cell_type.ilike(f"%{search}%"),
                CytokineInteraction.cytokine_effect.ilike(f"%{search}%"),
                CytokineInteraction.species.ilike(f"%{search}%")
            )
            query = query.filter(search_filter)
            filters['search'] = search
        
        # Get total count
        total = query.count()
        
        # Apply pagination
        offset = (page - 1) * limit
        results = query.offset(offset).limit(limit).all()
        
        # Determine which fields to return
        if fields:
            requested_fields = [f.strip() for f in fields.split(',')]
            requested_fields = ['id'] + [f for f in requested_fields if f in ALL_COLUMNS and f != 'id']
        else:
            # Default fields to show (only in pruned ALL_COLUMNS)
            requested_fields = ALL_COLUMNS
        
        # Format results
        data = []
        for row in results:
            item = {}
            for field in requested_fields:
                item[field] = getattr(row, field, None)
            data.append(item)
        
        return {
            "data": data,
            "pagination": {
                "page": page,
                "limit": limit,
                "total": total,
                "total_pages": (total + limit - 1) // limit
            },
            "filters": filters
        }


@app.get("/api/filters/{column}")
def get_filter_options(column: str, limit: int = Query(100, ge=1, le=1000)):
    """Get unique values for a specific column for filtering"""
    if column not in ALL_COLUMNS:
        raise HTTPException(status_code=400, detail=f"Invalid column: {column}")
    
    with get_db() as db:
        col = getattr(CytokineInteraction, column, None)
        if col is None:
            raise HTTPException(status_code=400, detail=f"Column not found: {column}")
        
        # Get distinct values
        values = db.query(col).distinct().filter(col.isnot(None)).limit(limit).all()
        values = [v[0] for v in values if v[0]]
        
        return {"column": column, "values": sorted(values)}

@app.get("/api/columns")
def get_columns():
    """Get all available columns"""
    return {"columns": ALL_COLUMNS}

@app.get("/api/stats")
def get_stats():
    """Get database statistics"""
    with get_db() as db:
        total = db.query(func.count(CytokineInteraction.id)).scalar()
        unique_cytokines = db.query(func.count(func.distinct(CytokineInteraction.cytokine_name))).scalar()
        unique_cell_types = db.query(func.count(func.distinct(CytokineInteraction.cell_type))).scalar()
        unique_species = db.query(func.count(func.distinct(CytokineInteraction.species))).scalar()
        
        return {
            "total_interactions": total,
            "unique_cytokines": unique_cytokines,
            "unique_cell_types": unique_cell_types,
            "unique_species": unique_species
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)