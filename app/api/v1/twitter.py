"""Twitter API endpoints."""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.announcement import Announcement
from app.models.artist import Artist
from app.services.twitter_service import TwitterService
from app.services.parser_service import TweetParser

router = APIRouter()

# Global service instances
twitter_service = TwitterService()
tweet_parser = TweetParser()


class TwitterStatusResponse(BaseModel):
    """Response for Twitter API status."""

    connected: bool
    rate_limit_remaining: int
    rate_limit_max: int
    can_request: bool


class RefreshRequest(BaseModel):
    """Request to refresh Twitter data."""

    artist_ids: Optional[List[int]] = None
    force: bool = False


class RefreshResponse(BaseModel):
    """Response from refresh operation."""

    artists_processed: int
    total_new_announcements: int
    errors: List[str]


class AnnouncementResponse(BaseModel):
    """Response for a single announcement."""

    id: int
    artist_id: Optional[int]
    artist_name: Optional[str] = None
    tour_id: Optional[int]
    tweet_id: str
    tweet_text: str
    tweet_url: Optional[str]
    author_handle: str
    author_name: Optional[str]
    tweeted_at: str
    is_official: bool
    is_processed: bool
    is_relevant: bool
    parsing_confidence: Optional[float]

    class Config:
        from_attributes = True


class AnnouncementListResponse(BaseModel):
    """Response for list of announcements."""

    announcements: List[AnnouncementResponse]
    total_count: int


class ParseTestRequest(BaseModel):
    """Request to test tweet parsing."""

    tweet_text: str


class ParseTestResponse(BaseModel):
    """Response from parsing test."""

    dates: List[dict]
    locations: List[dict]
    tour_name: Optional[str]
    is_seoul_related: bool
    is_encore: bool
    has_tbd: bool
    confidence: float


@router.get("/status", response_model=TwitterStatusResponse)
async def get_twitter_status() -> TwitterStatusResponse:
    """Get Twitter API connection status and rate limits."""
    status = twitter_service.get_status()
    return TwitterStatusResponse(**status)


@router.post("/refresh", response_model=RefreshResponse)
async def refresh_twitter_data(
    request: RefreshRequest = None,
    db: AsyncSession = Depends(get_db),
) -> RefreshResponse:
    """Trigger Twitter data refresh for artists."""
    if not twitter_service.is_configured:
        raise HTTPException(
            status_code=503,
            detail="Twitter API not configured. Add TWITTER_BEARER_TOKEN to .env",
        )

    request = request or RefreshRequest()

    if request.artist_ids:
        # Refresh specific artists
        result = await db.execute(
            select(Artist).where(Artist.id.in_(request.artist_ids))
        )
        artists = result.scalars().all()

        summary = {
            "artists_processed": 0,
            "total_new_announcements": 0,
            "errors": [],
        }

        for artist in artists:
            try:
                announcements = await twitter_service.fetch_for_artist(
                    artist, db
                )
                summary["artists_processed"] += 1
                summary["total_new_announcements"] += len(announcements)
            except Exception as e:
                summary["errors"].append(f"{artist.name}: {str(e)}")
    else:
        # Refresh all favorite artists
        summary = await twitter_service.fetch_all_artists(db, force=request.force)

    return RefreshResponse(**summary)


@router.get("/announcements", response_model=AnnouncementListResponse)
async def list_announcements(
    artist_id: Optional[int] = Query(None, description="Filter by artist"),
    processed: Optional[bool] = Query(None, description="Filter by processed status"),
    official_only: bool = Query(False, description="Show only official announcements"),
    limit: int = Query(50, ge=1, le=100, description="Number of results"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    db: AsyncSession = Depends(get_db),
) -> AnnouncementListResponse:
    """List Twitter announcements."""
    query = select(Announcement).order_by(Announcement.tweeted_at.desc())

    if artist_id:
        query = query.where(Announcement.artist_id == artist_id)
    if processed is not None:
        query = query.where(Announcement.is_processed == processed)
    if official_only:
        query = query.where(Announcement.is_official == True)

    # Get total count
    count_result = await db.execute(query)
    total = len(count_result.all())

    # Apply pagination
    query = query.offset(offset).limit(limit)
    result = await db.execute(query)
    announcements = result.scalars().all()

    # Get artist names
    responses = []
    for ann in announcements:
        artist_name = None
        if ann.artist_id:
            artist_result = await db.execute(
                select(Artist).where(Artist.id == ann.artist_id)
            )
            artist = artist_result.scalar_one_or_none()
            if artist:
                artist_name = artist.name

        responses.append(
            AnnouncementResponse(
                id=ann.id,
                artist_id=ann.artist_id,
                artist_name=artist_name,
                tour_id=ann.tour_id,
                tweet_id=ann.tweet_id,
                tweet_text=ann.tweet_text,
                tweet_url=ann.tweet_url,
                author_handle=ann.author_handle,
                author_name=ann.author_name,
                tweeted_at=ann.tweeted_at.isoformat(),
                is_official=ann.is_official,
                is_processed=ann.is_processed,
                is_relevant=ann.is_relevant,
                parsing_confidence=ann.parsing_confidence,
            )
        )

    return AnnouncementListResponse(
        announcements=responses,
        total_count=total,
    )


@router.post("/parse-test", response_model=ParseTestResponse)
async def test_tweet_parsing(request: ParseTestRequest) -> ParseTestResponse:
    """Test tweet parsing without storing results."""
    result = tweet_parser.parse_tweet(request.tweet_text)

    return ParseTestResponse(
        dates=[
            {
                "date": d.date.isoformat() if d.date else None,
                "end_date": d.end_date.isoformat() if d.end_date else None,
                "raw_text": d.raw_text,
                "is_tbd": d.is_tbd,
            }
            for d in result.dates
        ],
        locations=[
            {
                "city": loc.city,
                "venue": loc.venue,
                "country": loc.country,
                "region": loc.region,
            }
            for loc in result.locations
        ],
        tour_name=result.tour_name,
        is_seoul_related=result.is_seoul_related,
        is_encore=result.is_encore,
        has_tbd=result.has_tbd,
        confidence=result.confidence,
    )


@router.post("/process/{announcement_id}")
async def process_announcement(
    announcement_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Process an announcement and extract concert info."""
    result = await db.execute(
        select(Announcement).where(Announcement.id == announcement_id)
    )
    announcement = result.scalar_one_or_none()

    if not announcement:
        raise HTTPException(status_code=404, detail="Announcement not found")

    # Parse the tweet
    parsed = tweet_parser.parse_tweet(announcement.tweet_text)

    # Update announcement
    announcement.is_processed = True
    announcement.parsing_confidence = parsed.confidence
    announcement.set_extracted_data_dict({
        "dates": [
            {
                "date": d.date.isoformat() if d.date else None,
                "end_date": d.end_date.isoformat() if d.end_date else None,
                "raw_text": d.raw_text,
            }
            for d in parsed.dates
        ],
        "locations": [
            {
                "city": loc.city,
                "venue": loc.venue,
                "country": loc.country,
                "region": loc.region,
            }
            for loc in parsed.locations
        ],
        "tour_name": parsed.tour_name,
        "is_seoul_related": parsed.is_seoul_related,
        "is_encore": parsed.is_encore,
        "has_tbd": parsed.has_tbd,
    })

    await db.commit()

    return {
        "announcement_id": announcement_id,
        "confidence": parsed.confidence,
        "dates_found": len(parsed.dates),
        "locations_found": len(parsed.locations),
        "tour_name": parsed.tour_name,
    }
