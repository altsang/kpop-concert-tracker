"""Artist API endpoints."""

import json
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.artist import Artist
from app.models.tour import Tour
from app.models.tour_date import TourDate
from app.schemas.artist import (
    ArtistCreate,
    ArtistListResponse,
    ArtistResponse,
    ArtistUpdate,
)

router = APIRouter()


def _artist_to_response(artist: Artist, upcoming_count: int = 0, tours_count: int = 0) -> ArtistResponse:
    """Convert Artist model to response schema.

    Note: tours_count and upcoming_count must be calculated before calling this function
    to avoid async relationship loading issues.
    """
    return ArtistResponse(
        id=artist.id,
        name=artist.name,
        korean_name=artist.korean_name,
        twitter_handle=artist.twitter_handle,
        official_twitter=artist.official_twitter,
        agency_twitter=artist.agency_twitter,
        is_favorite=artist.is_favorite,
        aliases=artist.get_aliases_list(),
        group_type=artist.group_type,
        members_count=artist.members_count,
        debut_year=artist.debut_year,
        tours_count=tours_count,
        upcoming_shows_count=upcoming_count,
        created_at=artist.created_at,
        updated_at=artist.updated_at,
    )


@router.post("", response_model=ArtistResponse, status_code=201)
async def create_artist(
    artist_data: ArtistCreate,
    db: AsyncSession = Depends(get_db),
) -> ArtistResponse:
    """Create a new artist."""
    # Check if artist with same name exists
    existing = await db.execute(select(Artist).where(Artist.name == artist_data.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Artist with this name already exists")

    # Check if twitter handle exists
    if artist_data.twitter_handle:
        existing = await db.execute(
            select(Artist).where(Artist.twitter_handle == artist_data.twitter_handle)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(
                status_code=400, detail="Artist with this Twitter handle already exists"
            )

    artist = Artist(
        name=artist_data.name,
        korean_name=artist_data.korean_name,
        twitter_handle=artist_data.twitter_handle,
        official_twitter=artist_data.official_twitter,
        agency_twitter=artist_data.agency_twitter,
        group_type=artist_data.group_type,
        members_count=artist_data.members_count,
        debut_year=artist_data.debut_year,
    )
    artist.set_aliases_list(artist_data.aliases or [])

    db.add(artist)
    await db.commit()
    await db.refresh(artist)

    return _artist_to_response(artist, upcoming_count=0)


@router.get("", response_model=ArtistListResponse)
async def list_artists(
    favorites_only: bool = Query(False, description="Only show favorites"),
    search: Optional[str] = Query(None, description="Search by name"),
    db: AsyncSession = Depends(get_db),
) -> ArtistListResponse:
    """List all artists."""
    query = select(Artist).options(selectinload(Artist.tours).selectinload(Tour.dates))

    if favorites_only:
        query = query.where(Artist.is_favorite == True)

    if search:
        search_pattern = f"%{search}%"
        query = query.where(
            (Artist.name.ilike(search_pattern))
            | (Artist.korean_name.ilike(search_pattern))
        )

    query = query.order_by(Artist.name)

    result = await db.execute(query)
    artists = result.scalars().all()

    # Calculate upcoming shows for each artist
    from datetime import date

    today = date.today()
    artist_responses = []
    for artist in artists:
        upcoming_count = 0
        tours_count = len(artist.tours)
        for tour in artist.tours:
            for tour_date in tour.dates:
                if tour_date.date and tour_date.date >= today:
                    upcoming_count += 1
        artist_responses.append(_artist_to_response(artist, upcoming_count, tours_count))

    return ArtistListResponse(artists=artist_responses, total_count=len(artist_responses))


@router.get("/{artist_id}", response_model=ArtistResponse)
async def get_artist(
    artist_id: int,
    db: AsyncSession = Depends(get_db),
) -> ArtistResponse:
    """Get a single artist by ID."""
    result = await db.execute(
        select(Artist)
        .options(selectinload(Artist.tours).selectinload(Tour.dates))
        .where(Artist.id == artist_id)
    )
    artist = result.scalar_one_or_none()

    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    from datetime import date

    today = date.today()
    upcoming_count = 0
    tours_count = len(artist.tours)
    for tour in artist.tours:
        for tour_date in tour.dates:
            if tour_date.date and tour_date.date >= today:
                upcoming_count += 1

    return _artist_to_response(artist, upcoming_count, tours_count)


@router.put("/{artist_id}", response_model=ArtistResponse)
async def update_artist(
    artist_id: int,
    artist_data: ArtistUpdate,
    db: AsyncSession = Depends(get_db),
) -> ArtistResponse:
    """Update an artist."""
    result = await db.execute(
        select(Artist)
        .options(selectinload(Artist.tours).selectinload(Tour.dates))
        .where(Artist.id == artist_id)
    )
    artist = result.scalar_one_or_none()

    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    # Update fields if provided
    update_data = artist_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "aliases":
            artist.set_aliases_list(value)
        else:
            setattr(artist, field, value)

    await db.commit()
    await db.refresh(artist)

    # Calculate upcoming shows
    from datetime import date

    today = date.today()
    upcoming_count = 0
    tours_count = len(artist.tours)
    for tour in artist.tours:
        for tour_date in tour.dates:
            if tour_date.date and tour_date.date >= today:
                upcoming_count += 1

    return _artist_to_response(artist, upcoming_count, tours_count)


@router.delete("/{artist_id}", status_code=204)
async def delete_artist(
    artist_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete an artist."""
    result = await db.execute(select(Artist).where(Artist.id == artist_id))
    artist = result.scalar_one_or_none()

    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    await db.delete(artist)
    await db.commit()
