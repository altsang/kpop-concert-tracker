"""Pydantic schemas for Concert dashboard views."""

import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.tour_date import DateStatus


class ConcertDisplayItem(BaseModel):
    """Schema for a single concert display item in the dashboard."""

    tour_date_id: int
    artist_id: int
    artist_name: str
    artist_korean_name: Optional[str] = None
    tour_id: int
    tour_name: str
    city: str
    venue: Optional[str] = None
    country: str
    region: Optional[str] = None
    concert_date: Optional[datetime.date] = Field(None, alias="date")
    end_date: Optional[datetime.date] = None
    date_display: str  # Formatted: "Dec 15, 2025" or "TBD"
    is_past: bool  # For strikethrough styling
    is_today: bool
    is_seoul_kickoff: bool  # For special highlight
    is_encore: bool  # For special highlight
    is_finale: bool
    has_tbd_in_tour: bool  # Show "more dates TBD" indicator
    days_until: Optional[int] = None  # Days until concert (None if past/TBD)
    status: DateStatus
    ticket_url: Optional[str] = None
    ticket_status: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True


class ConcertFilterParams(BaseModel):
    """Schema for concert list filter parameters."""

    artist_ids: Optional[List[int]] = Field(None, description="Filter by artist IDs")
    cities: Optional[List[str]] = Field(None, description="Filter by cities")
    countries: Optional[List[str]] = Field(None, description="Filter by countries")
    date_from: Optional[datetime.date] = Field(None, description="Start date range")
    date_to: Optional[datetime.date] = Field(None, description="End date range")
    include_past: bool = Field(default=False, description="Include past shows")
    include_tbd: bool = Field(default=True, description="Include TBD dates")
    seoul_only: bool = Field(default=False, description="Seoul shows only")
    encore_only: bool = Field(default=False, description="Encore shows only")
    sort_by: str = Field(default="date", description="Sort by: 'date', 'artist', 'city'")
    sort_order: str = Field(default="asc", description="Sort order: 'asc', 'desc'")
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=50, ge=1, le=100, description="Page size")


class ConcertListResponse(BaseModel):
    """Schema for concert list response."""

    concerts: List[ConcertDisplayItem]
    total_count: int
    page: int
    page_size: int
    has_more_pages: bool
    has_any_tbd: bool  # Indicates if any tour has TBD dates
    last_updated: datetime.datetime


class DashboardSummary(BaseModel):
    """Schema for dashboard summary statistics."""

    total_artists_tracked: int
    total_upcoming_concerts: int
    total_past_concerts: int
    concerts_this_month: int
    concerts_with_tbd: int
    next_concert: Optional[ConcertDisplayItem] = None
    seoul_shows_upcoming: int
    encore_shows_upcoming: int
    last_twitter_update: Optional[datetime.datetime] = None


class HighlightsResponse(BaseModel):
    """Schema for highlights section response."""

    seoul_kickoffs: List[ConcertDisplayItem]
    encore_shows: List[ConcertDisplayItem]
    finale_shows: List[ConcertDisplayItem]
    recently_announced: List[ConcertDisplayItem]
