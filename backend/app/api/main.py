from fastapi import APIRouter

from app.api.routes import categories, ledgers, login, users, utils

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(ledgers.router)
api_router.include_router(categories.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
