"""TourDate model for individual concert dates."""

from datetime import date, time
from enum import Enum
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, Date, ForeignKey, Integer, String, Text, Time
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.tour import Tour


class DateStatus(str, Enum):
    """Status of a tour date."""

    UPCOMING = "upcoming"  # Future date
    TODAY = "today"  # Concert is today
    PAST = "past"  # Date has passed
    CANCELLED = "cancelled"  # This specific date cancelled
    POSTPONED = "postponed"  # Date postponed (awaiting new date)
    RESCHEDULED = "rescheduled"  # Date was rescheduled


class TourDate(Base, TimestampMixin):
    """Model representing an individual concert date within a tour."""

    __tablename__ = "tour_dates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tour_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("tours.id", ondelete="CASCADE"), nullable=False
    )
    city: Mapped[str] = mapped_column(String(255), nullable=False)
    venue: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    country: Mapped[str] = mapped_column(String(100), nullable=False)
    region: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True
    )  # e.g., "Asia", "North America"
    date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )  # NULL if TBD
    end_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )  # For multi-day shows
    show_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    timezone: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # e.g., "Asia/Seoul"

    # Special flags
    is_seoul_kickoff: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    is_encore: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_finale: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_added_date: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # True if added after initial announcement

    # Status
    status: Mapped[str] = mapped_column(
        String(50), default=DateStatus.UPCOMING.value, nullable=False
    )

    # Tickets
    ticket_url: Mapped[Optional[str]] = mapped_column(String(1000), nullable=True)
    ticket_status: Mapped[Optional[str]] = mapped_column(
        String(50), nullable=True
    )  # 'on_sale', 'sold_out', 'not_yet'
    on_sale_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Additional info
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_date: Mapped[Optional[date]] = mapped_column(
        Date, nullable=True
    )  # If rescheduled

    # Relationships
    tour: Mapped["Tour"] = relationship("Tour", back_populates="dates")

    @property
    def is_past(self) -> bool:
        """Check if this date has passed."""
        if self.date is None:
            return False
        return self.date < date.today()

    @property
    def is_today(self) -> bool:
        """Check if this concert is today."""
        if self.date is None:
            return False
        return self.date == date.today()

    @property
    def is_tbd(self) -> bool:
        """Check if the date is TBD."""
        return self.date is None

    @property
    def days_until(self) -> Optional[int]:
        """Get days until the concert (None if past or TBD)."""
        if self.date is None:
            return None
        delta = self.date - date.today()
        return delta.days if delta.days >= 0 else None

    @property
    def is_seoul(self) -> bool:
        """Check if this is a Seoul show."""
        return self.city.lower() in ["seoul", "서울"]

    def __repr__(self) -> str:
        return f"<TourDate(id={self.id}, city='{self.city}', date={self.date})>"
