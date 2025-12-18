"""Pydantic schemas for Artist API."""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class ArtistBase(BaseModel):
    """Base schema for Artist."""

    name: str = Field(..., min_length=1, max_length=255, description="Artist name")
    korean_name: Optional[str] = Field(None, max_length=255, description="Korean name")
    twitter_handle: Optional[str] = Field(
        None, max_length=100, description="Primary Twitter handle"
    )
    official_twitter: Optional[str] = Field(
        None, max_length=100, description="Official account handle"
    )
    agency_twitter: Optional[str] = Field(
        None, max_length=100, description="Agency account handle"
    )
    aliases: Optional[List[str]] = Field(
        default_factory=list, description="Alternative names"
    )
    group_type: str = Field(
        default="group", description="Type: 'group', 'solo', or 'subunit'"
    )
    members_count: Optional[int] = Field(None, ge=1, description="Number of members")
    debut_year: Optional[int] = Field(
        None, ge=1990, le=2030, description="Debut year"
    )


class ArtistCreate(ArtistBase):
    """Schema for creating an Artist."""

    pass


class ArtistUpdate(BaseModel):
    """Schema for updating an Artist."""

    name: Optional[str] = Field(None, min_length=1, max_length=255)
    korean_name: Optional[str] = Field(None, max_length=255)
    twitter_handle: Optional[str] = Field(None, max_length=100)
    official_twitter: Optional[str] = Field(None, max_length=100)
    agency_twitter: Optional[str] = Field(None, max_length=100)
    is_favorite: Optional[bool] = None
    aliases: Optional[List[str]] = None
    group_type: Optional[str] = None
    members_count: Optional[int] = Field(None, ge=1)
    debut_year: Optional[int] = Field(None, ge=1990, le=2030)


class ArtistResponse(ArtistBase):
    """Schema for Artist response."""

    id: int
    is_favorite: bool
    tours_count: int = 0
    upcoming_shows_count: int = 0
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ArtistListResponse(BaseModel):
    """Schema for list of Artists response."""

    artists: List[ArtistResponse]
    total_count: int
