from fastapi import APIRouter, HTTPException, status
from app.database import db

router = APIRouter(
    prefix="/health",
    tags=["Health"]
)

@router.get("/")
async def health_check():
    """Basic health check"""
    return {"status": "healthy"}

@router.get("/db")
async def db_health():
    """Test database connectivity"""
    try:
        # Simple query to check if database is responsive
        server_info = await db.command("serverStatus")
        return {
            "status": "connected", 
            "version": server_info.get("version", "unknown"),
            "uptime": server_info.get("uptime", 0)
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Database connection error: {str(e)}"
        )