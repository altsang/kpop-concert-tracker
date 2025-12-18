"""Artist model for K-pop groups and solo artists."""

import json
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import Boolean, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.tour import Tour
    from app.models.announcement import Announcement


class Artist(Base, TimestampMixin):
    """Model representing a K-pop artist or group."""

    __tablename__ = "artists"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    korean_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    twitter_handle: Mapped[Optional[str]] = mapped_column(
        String(100), nullable=True, unique=True
    )
    official_twitter: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    agency_twitter: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_favorite: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    aliases: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True
    )  # JSON array of alternative names
    group_type: Mapped[str] = mapped_column(
        String(50), default="group", nullable=False
    )  # 'group', 'solo', 'subunit'
    members_count: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    debut_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Relationships
    tours: Mapped[List["Tour"]] = relationship(
        "Tour", back_populates="artist", cascade="all, delete-orphan"
    )
    announcements: Mapped[List["Announcement"]] = relationship(
        "Announcement", back_populates="artist"
    )

    def get_aliases_list(self) -> List[str]:
        """Get aliases as a Python list."""
        if self.aliases:
            return json.loads(self.aliases)
        return []

    def set_aliases_list(self, aliases: List[str]) -> None:
        """Set aliases from a Python list."""
        self.aliases = json.dumps(aliases) if aliases else None

    def get_all_twitter_handles(self) -> List[str]:
        """Get all Twitter handles associated with this artist."""
        handles = []
        if self.twitter_handle:
            handles.append(self.twitter_handle)
        if self.official_twitter:
            handles.append(self.official_twitter)
        if self.agency_twitter:
            handles.append(self.agency_twitter)
        return handles

    def __repr__(self) -> str:
        return f"<Artist(id={self.id}, name='{self.name}')>"
