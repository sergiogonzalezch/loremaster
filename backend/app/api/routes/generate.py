from fastapi import APIRouter
from app.services.generate_service import generate_response
from app.models.models import GenerateTextRequest

router = APIRouter(prefix="/generate", tags=["generate"])


@router.post("/text")
async def generate(request: GenerateTextRequest):
    return {
        "message": generate_response(request.query),
        "status": "success",
    }
