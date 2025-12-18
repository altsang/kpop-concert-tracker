"""Tour model for concert tours."""

import json
from datetime import date
from enum import Enum
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.artist import Artist
    from app.models.tour_date import TourDate
    from app.models.announcement import Announcement


class TourStatus(str, Enum):
    """Status of a tour."""

    ANNOUNCED = "announced"  # Tour announced, dates may be partial
    PARTIAL = "partial"  # Some dates announced, more TBD
    COMPLETE = "complete"  # All dates announced
    ONGOING = "ongoing"  # Tour currently happening
    COMPLETED = "completed"  # Tour finished
    CANCELLED = "cancelled"  # Tour cancelled


class Tour(Base, TimestampMixin):
    """Model representing a concert tour."""

    __tablename__ = "tours"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    artist_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("artists.id", ondelete="CASCADE"), nullable=False
    )
    tour_name: Mapped[str] = mapped_column(String(500), nullable=False)
    year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(
        String(50), default=TourStatus.ANNOUNCED.value, nullable=False
    )
    has_tbd_dates: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_tbd_venues: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    total_shows_announced: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False
    )
    total_shows_estimated: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    announcement_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    tour_start_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    tour_end_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    regions: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array of regions

    # Relationships
    artist: Mapped["Artist"] = relationship("Artist", back_populates="tours")
    dates: Mapped[List["TourDate"]] = relationship(
        "TourDate", back_populates="tour", cascade="all, delete-orphan"
    )
    announcements: Mapped[List["Announcement"]] = relationship(
        "Announcement", back_populates="tour"
    )

    def get_regions_list(self) -> List[str]:
        """Get regions as a Python list."""
        if self.regions:
            return json.loads(self.regions)
        return []

    def set_regions_list(self, regions: List[str]) -> None:
        """Set regions from a Python list."""
        self.regions = json.dumps(regions) if regions else None

    def get_upcoming_dates_count(self) -> int:
        """Get count of upcoming show dates."""
        today = date.today()
        return sum(1 for d in self.dates if d.date and d.date >= today)

    def get_past_dates_count(self) -> int:
        """Get count of past show dates."""
        today = date.today()
        return sum(1 for d in self.dates if d.date and d.date < today)

    def __repr__(self) -> str:
        return f"<Tour(id={self.id}, name='{self.tour_name}', artist_id={self.artist_id})>"
