from fastapi import APIRouter
from endpoints import interviews, chat, cv, auth

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(interviews.router, prefix="/interviews", tags=["Interviews"])
api_router.include_router(chat.router, prefix="/interviews", tags=["Chat & WebSockets"])
api_router.include_router(cv.router, prefix="/cv", tags=["CV Processing"])
