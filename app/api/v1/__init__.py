"""API v1 routes."""

from fastapi import APIRouter

from app.api.v1 import artists, tours, concerts, twitter, dashboard

api_router = APIRouter(prefix="/api/v1")

api_router.include_router(artists.router, prefix="/artists", tags=["artists"])
api_router.include_router(tours.router, prefix="/tours", tags=["tours"])
api_router.include_router(concerts.router, prefix="/concerts", tags=["concerts"])
api_router.include_router(twitter.router, prefix="/twitter", tags=["twitter"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
