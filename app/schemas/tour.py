"""Pydantic schemas for Tour and TourDate API."""

import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from app.models.tour import TourStatus
from app.models.tour_date import DateStatus


class TourDateBase(BaseModel):
    """Base schema for TourDate."""

    city: str = Field(..., min_length=1, max_length=255, description="City name")
    venue: Optional[str] = Field(None, max_length=500, description="Venue name")
    country: str = Field(..., min_length=1, max_length=100, description="Country")
    region: Optional[str] = Field(
        None, max_length=100, description="Region (e.g., Asia)"
    )
    date: Optional[datetime.date] = Field(None, description="Concert date (null if TBD)")
    end_date: Optional[datetime.date] = Field(None, description="End date for multi-day shows")
    show_time: Optional[str] = Field(None, description="Show start time (HH:MM format)")
    timezone: Optional[str] = Field(None, max_length=50, description="Timezone")
    is_seoul_kickoff: bool = Field(default=False, description="Seoul kickoff show")
    is_encore: bool = Field(default=False, description="Encore show")
    is_finale: bool = Field(default=False, description="Finale show")
    ticket_url: Optional[str] = Field(None, max_length=1000, description="Ticket URL")
    ticket_status: Optional[str] = Field(
        None, description="'on_sale', 'sold_out', 'not_yet'"
    )
    on_sale_date: Optional[datetime.date] = Field(None, description="Ticket on-sale date")
    notes: Optional[str] = Field(None, description="Additional notes")


class TourDateCreate(TourDateBase):
    """Schema for creating a TourDate."""

    pass


class TourDateUpdate(BaseModel):
    """Schema for updating a TourDate."""

    city: Optional[str] = Field(None, min_length=1, max_length=255)
    venue: Optional[str] = Field(None, max_length=500)
    country: Optional[str] = Field(None, min_length=1, max_length=100)
    region: Optional[str] = Field(None, max_length=100)
    date: Optional[datetime.date] = None
    end_date: Optional[datetime.date] = None
    show_time: Optional[str] = None
    timezone: Optional[str] = Field(None, max_length=50)
    is_seoul_kickoff: Optional[bool] = None
    is_encore: Optional[bool] = None
    is_finale: Optional[bool] = None
    status: Optional[DateStatus] = None
    ticket_url: Optional[str] = Field(None, max_length=1000)
    ticket_status: Optional[str] = None
    on_sale_date: Optional[datetime.date] = None
    notes: Optional[str] = None


class TourDateResponse(TourDateBase):
    """Schema for TourDate response."""

    id: int
    tour_id: int
    status: DateStatus
    is_added_date: bool
    is_past: bool  # Computed field
    is_today: bool  # Computed field
    is_tbd: bool  # Computed field
    days_until: Optional[int]  # Computed field
    original_date: Optional[datetime.date]
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


class TourBase(BaseModel):
    """Base schema for Tour."""

    tour_name: str = Field(..., min_length=1, max_length=500, description="Tour name")
    year: Optional[int] = Field(None, ge=2000, le=2030, description="Tour year")
    has_tbd_dates: bool = Field(default=False, description="Has TBD dates")
    has_tbd_venues: bool = Field(default=False, description="Has TBD venues")
    description: Optional[str] = Field(None, description="Tour description")
    announcement_date: Optional[datetime.date] = Field(None, description="Announcement date")
    tour_start_date: Optional[datetime.date] = Field(None, description="Tour start date")
    tour_end_date: Optional[datetime.date] = Field(None, description="Tour end date")
    regions: Optional[List[str]] = Field(
        default_factory=list, description="Tour regions"
    )


class TourCreate(TourBase):
    """Schema for creating a Tour."""

    artist_id: int = Field(..., description="Artist ID")
    dates: Optional[List[TourDateCreate]] = Field(
        default_factory=list, description="Initial tour dates"
    )


class TourUpdate(BaseModel):
    """Schema for updating a Tour."""

    tour_name: Optional[str] = Field(None, min_length=1, max_length=500)
    year: Optional[int] = Field(None, ge=2000, le=2030)
    status: Optional[TourStatus] = None
    has_tbd_dates: Optional[bool] = None
    has_tbd_venues: Optional[bool] = None
    description: Optional[str] = None
    announcement_date: Optional[datetime.date] = None
    tour_start_date: Optional[datetime.date] = None
    tour_end_date: Optional[datetime.date] = None
    regions: Optional[List[str]] = None


class TourResponse(TourBase):
    """Schema for Tour response."""

    id: int
    artist_id: int
    artist_name: str = ""  # Will be populated from relationship
    status: TourStatus
    total_shows_announced: int
    total_shows_estimated: Optional[int]
    dates: List[TourDateResponse] = []
    upcoming_count: int = 0
    past_count: int = 0
    created_at: datetime.datetime
    updated_at: datetime.datetime

    class Config:
        from_attributes = True


class TourListResponse(BaseModel):
    """Schema for list of Tours response."""

    tours: List[TourResponse]
    total_count: int
