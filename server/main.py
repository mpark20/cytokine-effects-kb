from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import (
    create_engine, Column, Integer, String, Text, Float,
    select, func, or_
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv
import os
from contextlib import contextmanager

# Database setup
load_dotenv()

SUPABASE_DB_URL = os.getenv("SUPABASE_URL")
if not SUPABASE_DB_URL:
    raise RuntimeError("SUPABASE_URL is not set")

engine = create_engine(
    SUPABASE_DB_URL,
    pool_size=20,
    max_overflow=40,
    pool_timeout=30,
    pool_recycle=1800,
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


ALL_COLUMNS = [
    "id",
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

# Database Model
class CytokineInteraction(Base):
    __tablename__ = "cytokine_effects"

    id = Column(Integer, primary_key=True, index=True)
    chunk_id = Column(String(200))
    key_sentences = Column(Text)
    cell_type = Column(String(500), index=True)
    cytokine_name = Column(String(200), index=True)
    confidence_score = Column(Float)
    cytokine_effect = Column(String(500))
    cytokine_effect_original = Column(String(500))
    regulated_genes = Column(Text)
    gene_response_type = Column(String(200))
    regulated_pathways = Column(Text)
    pathway_response_type = Column(String(200))
    regulated_cell_processes = Column(Text)
    cell_process_category = Column(String(200))
    cell_process_response_type = Column(String(200))
    species = Column(String(200), index=True)
    necessary_condition = Column(String(500))
    experimental_concentration = Column(String(200))
    experimental_perturbation = Column(String(500))
    experimental_readout = Column(String(500))
    experimental_readout_category = Column(String(200))
    experimental_system_type = Column(String(200))
    experimental_system_details = Column(Text)
    experimental_time_point = Column(String(200))
    causality_type = Column(String(200))
    causality_description = Column(Text)
    publication_type = Column(String(200))
    mapped_citation_id = Column(String(200))
    url = Column(String(200))

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
app = FastAPI(
    title="Cytokine Knowledgebase API",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
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


@app.get("/")
def root():
    return {"message": "Cytokine Knowledgebase API", "version": "1.0.0"}

@app.get("/api/interactions", response_model=PaginatedResponse)
def get_interactions(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=500),
    fields: Optional[str] = None,
    cytokine_name: Optional[str] = None,
    cell_type: Optional[str] = None,
    species: Optional[str] = None,
    regulated_genes: Optional[str] = None,
    causality_type: Optional[str] = None,
    experimental_system_type: Optional[str] = None,
    publication_type: Optional[str] = None,
    search: Optional[str] = None,
):
    with get_db() as db:
        query = db.query(CytokineInteraction)
        filters = {}

        if cytokine_name:
            query = query.filter(CytokineInteraction.cytokine_name.ilike(f"%{cytokine_name}%"))
            filters["cytokine_name"] = cytokine_name
        if cell_type:
            query = query.filter(CytokineInteraction.cell_type.ilike(f"%{cell_type}%"))
            filters["cell_type"] = cell_type
        if species:
            query = query.filter(CytokineInteraction.species.ilike(f"%{species}%"))
            filters["species"] = species
        if causality_type:
            query = query.filter(CytokineInteraction.causality_type.ilike(f"%{causality_type}%"))
            filters["causality_type"] = causality_type
        if experimental_system_type:
            query = query.filter(CytokineInteraction.experimental_system_type.ilike(f"%{experimental_system_type}%"))
            filters['experimental_system_type'] = experimental_system_type
        if publication_type:
            query = query.filter(CytokineInteraction.publication_type.ilike(f"%{publication_type}%"))
            filters['publication_type'] = publication_type
        if regulated_genes:
            query = query.filter(CytokineInteraction.regulated_genes.ilike(f"%{regulated_genes}%"))
            filters["regulated_genes"] = regulated_genes

        if search:
            query = query.filter(
                or_(
                    CytokineInteraction.cytokine_name.ilike(f"%{search}%"),
                    CytokineInteraction.cell_type.ilike(f"%{search}%"),
                    CytokineInteraction.cytokine_effect.ilike(f"%{search}%"),
                    CytokineInteraction.species.ilike(f"%{search}%"),
                    CytokineInteraction.regulated_genes.ilike(f"%{search}%"),
                )
            )
            filters["search"] = search

        total = query.count()

        # pagination
        offset = (page - 1) * limit
        results = query.offset(offset).limit(limit).all()

        requested_fields = (
            [f.strip() for f in fields.split(",") if f.strip() in ALL_COLUMNS]
            if fields else ALL_COLUMNS
        )

        data = [
            {field: getattr(row, field) for field in requested_fields}
            for row in results
        ]

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



if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)