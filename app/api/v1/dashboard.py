"""Dashboard API endpoints."""

import datetime
from typing import Optional

from fastapi import APIRouter, Depends
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.artist import Artist
from app.models.tour import Tour
from app.models.tour_date import TourDate
from app.schemas.concert import ConcertDisplayItem, DashboardSummary

router = APIRouter()


def _format_date_display(d: Optional[datetime.date]) -> str:
    """Format date for display."""
    if d is None:
        return "TBD"
    return d.strftime("%b %d, %Y")


@router.get("/summary", response_model=DashboardSummary)
async def get_dashboard_summary(
    db: AsyncSession = Depends(get_db),
) -> DashboardSummary:
    """Get dashboard summary statistics."""
    today = datetime.date.today()
    current_month_start = today.replace(day=1)
    if today.month == 12:
        next_month_start = today.replace(year=today.year + 1, month=1, day=1)
    else:
        next_month_start = today.replace(month=today.month + 1, day=1)

    # Total artists tracked
    artists_count = await db.execute(
        select(func.count(Artist.id)).where(Artist.is_favorite == True)
    )
    total_artists = artists_count.scalar() or 0

    # Get all tour dates for favorites
    base_query = (
        select(TourDate, Tour, Artist)
        .join(Tour, TourDate.tour_id == Tour.id)
        .join(Artist, Tour.artist_id == Artist.id)
        .where(Artist.is_favorite == True)
    )

    # Upcoming concerts
    upcoming_result = await db.execute(
        base_query.where(TourDate.date >= today)
    )
    upcoming_dates = upcoming_result.all()
    total_upcoming = len(upcoming_dates)

    # Past concerts
    past_result = await db.execute(
        base_query.where(TourDate.date < today)
    )
    total_past = len(past_result.all())

    # Concerts this month
    this_month_result = await db.execute(
        base_query.where(
            and_(
                TourDate.date >= current_month_start,
                TourDate.date < next_month_start,
            )
        )
    )
    concerts_this_month = len(this_month_result.all())

    # Concerts with TBD
    tbd_result = await db.execute(
        base_query.where(TourDate.date.is_(None))
    )
    concerts_with_tbd = len(tbd_result.all())

    # Next concert
    next_concert = None
    if upcoming_dates:
        # Sort by date and get the first
        sorted_upcoming = sorted(upcoming_dates, key=lambda x: x[0].date)
        tour_date, tour, artist = sorted_upcoming[0]
        next_concert = ConcertDisplayItem(
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
            status=tour_date.status,
            ticket_url=tour_date.ticket_url,
            ticket_status=tour_date.ticket_status,
        )

    # Seoul shows upcoming
    seoul_result = await db.execute(
        base_query.where(
            and_(
                TourDate.date >= today,
                or_(
                    TourDate.city.ilike("%seoul%"),
                    TourDate.city.ilike("%서울%"),
                ),
            )
        )
    )
    seoul_shows_upcoming = len(seoul_result.all())

    # Encore shows upcoming
    encore_result = await db.execute(
        base_query.where(
            and_(
                TourDate.date >= today,
                TourDate.is_encore == True,
            )
        )
    )
    encore_shows_upcoming = len(encore_result.all())

    return DashboardSummary(
        total_artists_tracked=total_artists,
        total_upcoming_concerts=total_upcoming,
        total_past_concerts=total_past,
        concerts_this_month=concerts_this_month,
        concerts_with_tbd=concerts_with_tbd,
        next_concert=next_concert,
        seoul_shows_upcoming=seoul_shows_upcoming,
        encore_shows_upcoming=encore_shows_upcoming,
        last_twitter_update=None,  # Will be populated when Twitter integration is added
    )
