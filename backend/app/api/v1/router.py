from fastapi import APIRouter
from app.api.v1.endpoints import health, auth, farmers, crops, advisory, resources, groups, machinery_plan

api_router = APIRouter()
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(farmers.router, tags=["farmers"])
api_router.include_router(crops.router, prefix="/crops", tags=["crops"])
api_router.include_router(advisory.router, tags=["advisory"])
api_router.include_router(resources.router, tags=["resources"])
api_router.include_router(groups.router, tags=["groups"])
api_router.include_router(machinery_plan.router, tags=["machinery-plan"])
