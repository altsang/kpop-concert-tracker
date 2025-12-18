"""Announcement model for Twitter announcements."""

import json
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base

if TYPE_CHECKING:
    from app.models.artist import Artist
    from app.models.tour import Tour


class Announcement(Base):
    """Model representing a Twitter announcement about a concert."""

    __tablename__ = "announcements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    artist_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("artists.id", ondelete="SET NULL"), nullable=True
    )
    tour_id: Mapped[Optional[int]] = mapped_column(
        Integer, ForeignKey("tours.id", ondelete="SET NULL"), nullable=True
    )
    tweet_id: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    tweet_text: Mapped[str] = mapped_column(Text, nullable=False)
    tweet_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    author_handle: Mapped[str] = mapped_column(String(100), nullable=False)
    author_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    tweeted_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    is_official: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_processed: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_relevant: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False
    )  # Concert-related
    extracted_data: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON of parsed data
    parsing_confidence: Mapped[Optional[float]] = mapped_column(
        Float, nullable=True
    )  # 0.0-1.0 confidence score
    media_urls: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array of image URLs
    retweet_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    like_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=datetime.utcnow, nullable=False
    )

    # Relationships
    artist: Mapped[Optional["Artist"]] = relationship(
        "Artist", back_populates="announcements"
    )
    tour: Mapped[Optional["Tour"]] = relationship(
        "Tour", back_populates="announcements"
    )

    def get_extracted_data_dict(self) -> dict:
        """Get extracted data as a Python dict."""
        if self.extracted_data:
            return json.loads(self.extracted_data)
        return {}

    def set_extracted_data_dict(self, data: dict) -> None:
        """Set extracted data from a Python dict."""
        self.extracted_data = json.dumps(data) if data else None

    def get_media_urls_list(self) -> list:
        """Get media URLs as a Python list."""
        if self.media_urls:
            return json.loads(self.media_urls)
        return []

    def set_media_urls_list(self, urls: list) -> None:
        """Set media URLs from a Python list."""
        self.media_urls = json.dumps(urls) if urls else None

    def __repr__(self) -> str:
        return f"<Announcement(id={self.id}, tweet_id='{self.tweet_id}')>"
