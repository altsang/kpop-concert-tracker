"""Tour API endpoints."""

from datetime import date
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.artist import Artist
from app.models.tour import Tour, TourStatus
from app.models.tour_date import TourDate, DateStatus
from app.schemas.tour import (
    TourCreate,
    TourDateCreate,
    TourDateResponse,
    TourDateUpdate,
    TourListResponse,
    TourResponse,
    TourUpdate,
)

router = APIRouter()


def _tour_date_to_response(tour_date: TourDate) -> TourDateResponse:
    """Convert TourDate model to response schema."""
    return TourDateResponse(
        id=tour_date.id,
        tour_id=tour_date.tour_id,
        city=tour_date.city,
        venue=tour_date.venue,
        country=tour_date.country,
        region=tour_date.region,
        date=tour_date.date,
        end_date=tour_date.end_date,
        show_time=tour_date.show_time.strftime("%H:%M") if tour_date.show_time else None,
        timezone=tour_date.timezone,
        is_seoul_kickoff=tour_date.is_seoul_kickoff,
        is_encore=tour_date.is_encore,
        is_finale=tour_date.is_finale,
        status=DateStatus(tour_date.status),
        is_added_date=tour_date.is_added_date,
        is_past=tour_date.is_past,
        is_today=tour_date.is_today,
        is_tbd=tour_date.is_tbd,
        days_until=tour_date.days_until,
        ticket_url=tour_date.ticket_url,
        ticket_status=tour_date.ticket_status,
        on_sale_date=tour_date.on_sale_date,
        notes=tour_date.notes,
        original_date=tour_date.original_date,
        created_at=tour_date.created_at,
        updated_at=tour_date.updated_at,
    )


def _tour_to_response(tour: Tour) -> TourResponse:
    """Convert Tour model to response schema."""
    today = date.today()
    upcoming = sum(1 for d in tour.dates if d.date and d.date >= today)
    past = sum(1 for d in tour.dates if d.date and d.date < today)

    # Sort dates: upcoming first (by date), then TBD, then past
    sorted_dates = sorted(
        tour.dates,
        key=lambda d: (
            d.date is None,  # TBD dates go after dated ones
            d.is_past,  # Past dates go last
            d.date or date.max,  # Sort by date
        ),
    )

    return TourResponse(
        id=tour.id,
        artist_id=tour.artist_id,
        artist_name=tour.artist.name if tour.artist else "",
        tour_name=tour.tour_name,
        year=tour.year,
        status=TourStatus(tour.status),
        has_tbd_dates=tour.has_tbd_dates,
        has_tbd_venues=tour.has_tbd_venues,
        total_shows_announced=tour.total_shows_announced,
        total_shows_estimated=tour.total_shows_estimated,
        description=tour.description,
        announcement_date=tour.announcement_date,
        tour_start_date=tour.tour_start_date,
        tour_end_date=tour.tour_end_date,
        regions=tour.get_regions_list(),
        dates=[_tour_date_to_response(d) for d in sorted_dates],
        upcoming_count=upcoming,
        past_count=past,
        created_at=tour.created_at,
        updated_at=tour.updated_at,
    )


def _auto_detect_seoul_kickoff(dates: List[TourDate]) -> None:
    """Auto-detect Seoul kickoff (earliest Seoul date in tour)."""
    seoul_dates = [d for d in dates if d.is_seoul and d.date]
    if seoul_dates:
        # Sort by date and mark the earliest as kickoff
        seoul_dates.sort(key=lambda d: d.date)
        # Reset all Seoul dates first
        for d in dates:
            if d.is_seoul and not d.is_encore:  # Don't change manually set encore
                d.is_seoul_kickoff = False
        # Mark earliest as kickoff
        seoul_dates[0].is_seoul_kickoff = True


@router.post("", response_model=TourResponse, status_code=201)
async def create_tour(
    tour_data: TourCreate,
    db: AsyncSession = Depends(get_db),
) -> TourResponse:
    """Create a new tour with optional initial dates."""
    # Verify artist exists
    result = await db.execute(select(Artist).where(Artist.id == tour_data.artist_id))
    artist = result.scalar_one_or_none()
    if not artist:
        raise HTTPException(status_code=404, detail="Artist not found")

    tour = Tour(
        artist_id=tour_data.artist_id,
        tour_name=tour_data.tour_name,
        year=tour_data.year,
        has_tbd_dates=tour_data.has_tbd_dates,
        has_tbd_venues=tour_data.has_tbd_venues,
        description=tour_data.description,
        announcement_date=tour_data.announcement_date or date.today(),
        tour_start_date=tour_data.tour_start_date,
        tour_end_date=tour_data.tour_end_date,
    )
    tour.set_regions_list(tour_data.regions or [])

    # Add initial dates if provided
    if tour_data.dates:
        for date_data in tour_data.dates:
            tour_date = TourDate(
                city=date_data.city,
                venue=date_data.venue,
                country=date_data.country,
                region=date_data.region,
                date=date_data.date,
                end_date=date_data.end_date,
                show_time=date_data.show_time,
                timezone=date_data.timezone,
                is_seoul_kickoff=date_data.is_seoul_kickoff,
                is_encore=date_data.is_encore,
                is_finale=date_data.is_finale,
                ticket_url=date_data.ticket_url,
                ticket_status=date_data.ticket_status,
                on_sale_date=date_data.on_sale_date,
                notes=date_data.notes,
            )
            tour.dates.append(tour_date)

        # Auto-detect Seoul kickoff if not manually set
        if not any(d.is_seoul_kickoff for d in tour.dates):
            _auto_detect_seoul_kickoff(tour.dates)

        tour.total_shows_announced = len(tour.dates)

    db.add(tour)
    await db.commit()

    # Reload with relationships
    result = await db.execute(
        select(Tour)
        .options(selectinload(Tour.artist), selectinload(Tour.dates))
        .where(Tour.id == tour.id)
    )
    tour = result.scalar_one()

    return _tour_to_response(tour)


@router.get("", response_model=TourListResponse)
async def list_tours(
    artist_id: Optional[int] = Query(None, description="Filter by artist"),
    status: Optional[TourStatus] = Query(None, description="Filter by status"),
    year: Optional[int] = Query(None, description="Filter by year"),
    db: AsyncSession = Depends(get_db),
) -> TourListResponse:
    """List all tours."""
    query = select(Tour).options(selectinload(Tour.artist), selectinload(Tour.dates))

    if artist_id:
        query = query.where(Tour.artist_id == artist_id)
    if status:
        query = query.where(Tour.status == status.value)
    if year:
        query = query.where(Tour.year == year)

    query = query.order_by(Tour.announcement_date.desc())

    result = await db.execute(query)
    tours = result.scalars().all()

    return TourListResponse(
        tours=[_tour_to_response(t) for t in tours],
        total_count=len(tours),
    )


@router.get("/{tour_id}", response_model=TourResponse)
async def get_tour(
    tour_id: int,
    db: AsyncSession = Depends(get_db),
) -> TourResponse:
    """Get a single tour by ID."""
    result = await db.execute(
        select(Tour)
        .options(selectinload(Tour.artist), selectinload(Tour.dates))
        .where(Tour.id == tour_id)
    )
    tour = result.scalar_one_or_none()

    if not tour:
        raise HTTPException(status_code=404, detail="Tour not found")

    return _tour_to_response(tour)


@router.put("/{tour_id}", response_model=TourResponse)
async def update_tour(
    tour_id: int,
    tour_data: TourUpdate,
    db: AsyncSession = Depends(get_db),
) -> TourResponse:
    """Update a tour."""
    result = await db.execute(
        select(Tour)
        .options(selectinload(Tour.artist), selectinload(Tour.dates))
        .where(Tour.id == tour_id)
    )
    tour = result.scalar_one_or_none()

    if not tour:
        raise HTTPException(status_code=404, detail="Tour not found")

    update_data = tour_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "regions":
            tour.set_regions_list(value)
        elif field == "status":
            tour.status = value.value
        else:
            setattr(tour, field, value)

    await db.commit()
    await db.refresh(tour)

    return _tour_to_response(tour)


@router.delete("/{tour_id}", status_code=204)
async def delete_tour(
    tour_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a tour."""
    result = await db.execute(select(Tour).where(Tour.id == tour_id))
    tour = result.scalar_one_or_none()

    if not tour:
        raise HTTPException(status_code=404, detail="Tour not found")

    await db.delete(tour)
    await db.commit()


# Tour Dates endpoints


@router.post("/{tour_id}/dates", response_model=TourDateResponse, status_code=201)
async def add_tour_date(
    tour_id: int,
    date_data: TourDateCreate,
    db: AsyncSession = Depends(get_db),
) -> TourDateResponse:
    """Add a date to a tour."""
    result = await db.execute(
        select(Tour).options(selectinload(Tour.dates)).where(Tour.id == tour_id)
    )
    tour = result.scalar_one_or_none()

    if not tour:
        raise HTTPException(status_code=404, detail="Tour not found")

    tour_date = TourDate(
        tour_id=tour_id,
        city=date_data.city,
        venue=date_data.venue,
        country=date_data.country,
        region=date_data.region,
        date=date_data.date,
        end_date=date_data.end_date,
        show_time=date_data.show_time,
        timezone=date_data.timezone,
        is_seoul_kickoff=date_data.is_seoul_kickoff,
        is_encore=date_data.is_encore,
        is_finale=date_data.is_finale,
        is_added_date=True,  # Mark as added after initial announcement
        ticket_url=date_data.ticket_url,
        ticket_status=date_data.ticket_status,
        on_sale_date=date_data.on_sale_date,
        notes=date_data.notes,
    )

    db.add(tour_date)
    tour.total_shows_announced += 1

    await db.commit()
    await db.refresh(tour_date)

    # Auto-detect Seoul kickoff if this is a Seoul date and none set
    if tour_date.is_seoul and not any(d.is_seoul_kickoff for d in tour.dates):
        result = await db.execute(
            select(Tour).options(selectinload(Tour.dates)).where(Tour.id == tour_id)
        )
        tour = result.scalar_one()
        _auto_detect_seoul_kickoff(tour.dates)
        await db.commit()
        await db.refresh(tour_date)

    return _tour_date_to_response(tour_date)


@router.put("/{tour_id}/dates/{date_id}", response_model=TourDateResponse)
async def update_tour_date(
    tour_id: int,
    date_id: int,
    date_data: TourDateUpdate,
    db: AsyncSession = Depends(get_db),
) -> TourDateResponse:
    """Update a tour date."""
    result = await db.execute(
        select(TourDate).where(TourDate.id == date_id, TourDate.tour_id == tour_id)
    )
    tour_date = result.scalar_one_or_none()

    if not tour_date:
        raise HTTPException(status_code=404, detail="Tour date not found")

    update_data = date_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "status":
            tour_date.status = value.value
        else:
            setattr(tour_date, field, value)

    await db.commit()
    await db.refresh(tour_date)

    return _tour_date_to_response(tour_date)


@router.delete("/{tour_id}/dates/{date_id}", status_code=204)
async def delete_tour_date(
    tour_id: int,
    date_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    """Delete a tour date."""
    result = await db.execute(
        select(TourDate).where(TourDate.id == date_id, TourDate.tour_id == tour_id)
    )
    tour_date = result.scalar_one_or_none()

    if not tour_date:
        raise HTTPException(status_code=404, detail="Tour date not found")

    # Update tour count
    result = await db.execute(select(Tour).where(Tour.id == tour_id))
    tour = result.scalar_one()
    tour.total_shows_announced = max(0, tour.total_shows_announced - 1)

    await db.delete(tour_date)
    await db.commit()
