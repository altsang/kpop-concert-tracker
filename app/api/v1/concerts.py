"""Concert API endpoints for dashboard views."""

import datetime
from datetime import date as date_type
from typing import List, Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.artist import Artist
from app.models.tour import Tour
from app.models.tour_date import TourDate, DateStatus
from app.schemas.concert import (
    ConcertDisplayItem,
    ConcertFilterParams,
    ConcertListResponse,
)

router = APIRouter()


def _format_date_display(d: Optional[date_type]) -> str:
    """Format date for display."""
    if d is None:
        return "TBD"
    return d.strftime("%b %d, %Y")


def _tour_date_to_concert_item(
    tour_date: TourDate, tour: Tour, artist: Artist
) -> ConcertDisplayItem:
    """Convert tour date to concert display item."""
    return ConcertDisplayItem(
        tour_date_id=tour_date.id,
        artist_id=artist.id,
        artist_name=artist.name,
        artist_korean_name=artist.korean_name,
        tour_id=tour.id,
        tour_name=tour.tour_name,
        city=tour_date.city,
        venue=tour_date.venue,
        country=tour_date.country,
        region=tour_date.region,
        concert_date=tour_date.date,
        end_date=tour_date.end_date,
        date_display=_format_date_display(tour_date.date),
        is_past=tour_date.is_past,
        is_today=tour_date.is_today,
        is_seoul_kickoff=tour_date.is_seoul_kickoff,
        is_encore=tour_date.is_encore,
        is_finale=tour_date.is_finale,
        has_tbd_in_tour=tour.has_tbd_dates,
        days_until=tour_date.days_until,
        status=DateStatus(tour_date.status),
        ticket_url=tour_date.ticket_url,
        ticket_status=tour_date.ticket_status,
    )


@router.get("", response_model=ConcertListResponse)
async def list_concerts(
    artist_ids: Optional[str] = Query(None, description="Comma-separated artist IDs"),
    cities: Optional[str] = Query(None, description="Comma-separated cities"),
    countries: Optional[str] = Query(None, description="Comma-separated countries"),
    date_from: Optional[date_type] = Query(None, description="Start date"),
    date_to: Optional[date_type] = Query(None, description="End date"),
    include_past: bool = Query(False, description="Include past shows"),
    include_tbd: bool = Query(True, description="Include TBD dates"),
    seoul_only: bool = Query(False, description="Seoul shows only"),
    encore_only: bool = Query(False, description="Encore shows only"),
    sort_by: str = Query("date", description="Sort by: date, artist, city"),
    sort_order: str = Query("asc", description="Sort order: asc, desc"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=100, description="Page size"),
    db: AsyncSession = Depends(get_db),
) -> ConcertListResponse:
    """List concerts with filtering and pagination."""
    today = date_type.today()

    # Build base query
    query = (
        select(TourDate, Tour, Artist)
        .join(Tour, TourDate.tour_id == Tour.id)
        .join(Artist, Tour.artist_id == Artist.id)
        .where(Artist.is_favorite == True)
    )

    # Apply filters
    conditions = []

    # Artist filter
    if artist_ids:
        ids = [int(x.strip()) for x in artist_ids.split(",") if x.strip()]
        if ids:
            conditions.append(Artist.id.in_(ids))

    # City filter
    if cities:
        city_list = [x.strip().lower() for x in cities.split(",") if x.strip()]
        if city_list:
            city_conditions = [TourDate.city.ilike(f"%{c}%") for c in city_list]
            conditions.append(or_(*city_conditions))

    # Country filter
    if countries:
        country_list = [x.strip().lower() for x in countries.split(",") if x.strip()]
        if country_list:
            country_conditions = [TourDate.country.ilike(f"%{c}%") for c in country_list]
            conditions.append(or_(*country_conditions))

    # Date range filter
    if date_from:
        conditions.append(or_(TourDate.date >= date_from, TourDate.date.is_(None)))
    if date_to:
        conditions.append(or_(TourDate.date <= date_to, TourDate.date.is_(None)))

    # Past filter
    if not include_past:
        conditions.append(or_(TourDate.date >= today, TourDate.date.is_(None)))

    # TBD filter
    if not include_tbd:
        conditions.append(TourDate.date.isnot(None))

    # Seoul only filter
    if seoul_only:
        conditions.append(
            or_(
                TourDate.city.ilike("%seoul%"),
                TourDate.city.ilike("%서울%"),
            )
        )

    # Encore only filter
    if encore_only:
        conditions.append(TourDate.is_encore == True)

    # Apply all conditions
    if conditions:
        query = query.where(and_(*conditions))

    # Sorting
    if sort_by == "artist":
        order_col = Artist.name
    elif sort_by == "city":
        order_col = TourDate.city
    else:  # date
        order_col = TourDate.date

    if sort_order == "desc":
        # For date sorting, put TBD (NULL) at the end
        if sort_by == "date":
            query = query.order_by(
                TourDate.date.is_(None),  # NULL dates last
                order_col.desc(),
            )
        else:
            query = query.order_by(order_col.desc())
    else:
        if sort_by == "date":
            query = query.order_by(
                TourDate.date.is_(None),  # NULL dates last
                order_col.asc(),
            )
        else:
            query = query.order_by(order_col.asc())

    # Get total count
    count_result = await db.execute(query)
    all_results = count_result.all()
    total_count = len(all_results)

    # Apply pagination
    offset = (page - 1) * page_size
    paginated_results = all_results[offset : offset + page_size]

    # Convert to response items
    concerts = [
        _tour_date_to_concert_item(tour_date, tour, artist)
        for tour_date, tour, artist in paginated_results
    ]

    # Check if any tour has TBD dates
    has_any_tbd = any(td.date is None for td, _, _ in all_results)

    return ConcertListResponse(
        concerts=concerts,
        total_count=total_count,
        page=page,
        page_size=page_size,
        has_more_pages=(offset + page_size) < total_count,
        has_any_tbd=has_any_tbd,
        last_updated=datetime.datetime.now(),
    )


@router.get("/upcoming", response_model=ConcertListResponse)
async def list_upcoming_concerts(
    limit: int = Query(20, ge=1, le=100, description="Number of concerts"),
    db: AsyncSession = Depends(get_db),
) -> ConcertListResponse:
    """Get upcoming concerts only."""
    today = date_type.today()

    query = (
        select(TourDate, Tour, Artist)
        .join(Tour, TourDate.tour_id == Tour.id)
        .join(Artist, Tour.artist_id == Artist.id)
        .where(Artist.is_favorite == True)
        .where(TourDate.date >= today)
        .order_by(TourDate.date.asc())
        .limit(limit)
    )

    result = await db.execute(query)
    results = result.all()

    concerts = [
        _tour_date_to_concert_item(tour_date, tour, artist)
        for tour_date, tour, artist in results
    ]

    return ConcertListResponse(
        concerts=concerts,
        total_count=len(concerts),
        page=1,
        page_size=limit,
        has_more_pages=False,
        has_any_tbd=False,
        last_updated=datetime.datetime.now(),
    )


@router.get("/highlights")
async def get_highlights(
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Get highlighted concerts (Seoul kickoffs, encores, finales)."""
    today = date_type.today()

    base_query = (
        select(TourDate, Tour, Artist)
        .join(Tour, TourDate.tour_id == Tour.id)
        .join(Artist, Tour.artist_id == Artist.id)
        .where(Artist.is_favorite == True)
        .where(or_(TourDate.date >= today, TourDate.date.is_(None)))
    )

    # Seoul kickoffs
    seoul_query = base_query.where(TourDate.is_seoul_kickoff == True).limit(10)
    seoul_result = await db.execute(seoul_query)
    seoul_kickoffs = [
        _tour_date_to_concert_item(td, t, a) for td, t, a in seoul_result.all()
    ]

    # Encore shows
    encore_query = base_query.where(TourDate.is_encore == True).limit(10)
    encore_result = await db.execute(encore_query)
    encore_shows = [
        _tour_date_to_concert_item(td, t, a) for td, t, a in encore_result.all()
    ]

    # Finale shows
    finale_query = base_query.where(TourDate.is_finale == True).limit(10)
    finale_result = await db.execute(finale_query)
    finale_shows = [
        _tour_date_to_concert_item(td, t, a) for td, t, a in finale_result.all()
    ]

    return {
        "seoul_kickoffs": seoul_kickoffs,
        "encore_shows": encore_shows,
        "finale_shows": finale_shows,
    }
