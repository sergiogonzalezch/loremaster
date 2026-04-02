from fastapi import APIRouter
from app.services.rag_service import generate_response
from app.schemas.models import GenerateTextRequest

router = APIRouter()


@router.post("/generate")
async def generate(request: GenerateTextRequest):
    return {
        "response": generate_response(request.query),
        "status": "success",
    }
