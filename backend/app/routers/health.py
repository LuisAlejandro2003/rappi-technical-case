from fastapi import APIRouter, Depends

from app.core.database import DuckDBService
from app.dependencies import get_db

router = APIRouter()


@router.get("/health")
async def health(db: DuckDBService = Depends(get_db)):
    return {
        "status": "healthy",
        "tables": db.get_table_names(),
        "row_counts": db.get_row_counts(),
    }
