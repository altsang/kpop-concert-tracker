"""Twitter API integration service."""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional

import tweepy
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.models.announcement import Announcement
from app.models.artist import Artist

logger = logging.getLogger(__name__)
settings = get_settings()


class RateLimiter:
    """Track and enforce Twitter API rate limits."""

    def __init__(
        self,
        max_requests: int = 450,
        window_seconds: int = 900,
    ):
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self.request_timestamps: List[datetime] = []
        self.reset_time: Optional[datetime] = None

    def _clean_old_timestamps(self) -> None:
        """Remove timestamps older than the window."""
        now = datetime.now()
        cutoff = now - timedelta(seconds=self.window_seconds)
        self.request_timestamps = [ts for ts in self.request_timestamps if ts > cutoff]

    @property
    def remaining(self) -> int:
        """Get remaining requests in current window."""
        self._clean_old_timestamps()
        return max(0, self.max_requests - len(self.request_timestamps))

    @property
    def can_request(self) -> bool:
        """Check if a request can be made."""
        return self.remaining > 0

    async def wait_if_needed(self) -> None:
        """Wait if rate limit would be exceeded."""
        self._clean_old_timestamps()

        if len(self.request_timestamps) >= self.max_requests:
            # Calculate wait time until oldest request expires
            oldest = min(self.request_timestamps)
            wait_until = oldest + timedelta(seconds=self.window_seconds)
            wait_seconds = (wait_until - datetime.now()).total_seconds()

            if wait_seconds > 0:
                logger.info(f"Rate limit reached. Waiting {wait_seconds:.1f}s")
                await asyncio.sleep(wait_seconds)
                self._clean_old_timestamps()

    def record_request(self) -> None:
        """Record a new request timestamp."""
        self.request_timestamps.append(datetime.now())


class SearchQueryBuilder:
    """Build optimized Twitter search queries for concert announcements."""

    CONCERT_KEYWORDS = [
        "tour",
        "concert",
        "world tour",
        "dates announced",
        "tickets",
        "live in",
    ]

    EXCLUSION_KEYWORDS = [
        "fan meeting",
        "fanmeeting",
        "meet and greet",
        "reality show",
        "album",
        "MV",
        "music video",
    ]

    def build_query(self, artist: Artist) -> str:
        """Build search query for an artist.

        Example output:
        (BLACKPINK OR @BLACKPINK OR 블랙핑크) (tour OR concert) -is:retweet -"fan meeting"
        """
        # Artist name variations
        names = [f'"{artist.name}"']
        if artist.korean_name:
            names.append(f'"{artist.korean_name}"')
        if artist.twitter_handle:
            names.append(artist.twitter_handle)
        aliases = artist.get_aliases_list()
        for alias in aliases[:2]:  # Limit to avoid query length issues
            names.append(f'"{alias}"')

        name_clause = " OR ".join(names)

        # Concert keywords (limit to avoid query length)
        keyword_clause = " OR ".join(self.CONCERT_KEYWORDS[:3])

        # Exclusions
        exclusions = " ".join(f'-"{kw}"' for kw in self.EXCLUSION_KEYWORDS[:3])

        # Build final query
        query = f"({name_clause}) ({keyword_clause}) -is:retweet {exclusions}"

        # Twitter max query length is 512 for recent search
        return query[:512]

    def build_official_query(self, artist: Artist) -> Optional[str]:
        """Build query for official accounts only."""
        handles = artist.get_all_twitter_handles()
        if not handles:
            return None

        # Search from specific accounts
        from_clause = " OR ".join(f"from:{h.lstrip('@')}" for h in handles)
        keywords = " OR ".join(self.CONCERT_KEYWORDS[:3])

        query = f"({from_clause}) ({keywords})"
        return query[:512]


class TwitterService:
    """Service for interacting with Twitter API."""

    def __init__(self):
        self.client: Optional[tweepy.Client] = None
        self.rate_limiter = RateLimiter(
            max_requests=settings.twitter_search_limit,
            window_seconds=settings.twitter_window_seconds,
        )
        self.query_builder = SearchQueryBuilder()
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Twitter API client."""
        if settings.twitter_bearer_token:
            self.client = tweepy.Client(
                bearer_token=settings.twitter_bearer_token,
                wait_on_rate_limit=False,  # We handle rate limiting ourselves
            )
            logger.info("Twitter client initialized")
        else:
            logger.warning("Twitter API token not configured")

    @property
    def is_configured(self) -> bool:
        """Check if Twitter API is configured."""
        return self.client is not None

    def get_status(self) -> dict:
        """Get Twitter API status information."""
        return {
            "connected": self.is_configured,
            "rate_limit_remaining": self.rate_limiter.remaining,
            "rate_limit_max": self.rate_limiter.max_requests,
            "can_request": self.rate_limiter.can_request,
        }

    async def search_tweets(
        self,
        query: str,
        max_results: int = 100,
        since_id: Optional[str] = None,
    ) -> List[dict]:
        """Search for tweets matching the query.

        Returns list of tweet data dictionaries.
        """
        if not self.is_configured:
            logger.warning("Twitter API not configured")
            return []

        await self.rate_limiter.wait_if_needed()

        try:
            response = self.client.search_recent_tweets(
                query=query,
                max_results=min(max_results, 100),
                since_id=since_id,
                tweet_fields=[
                    "created_at",
                    "author_id",
                    "public_metrics",
                    "entities",
                ],
                user_fields=["username", "name"],
                expansions=["author_id"],
            )

            self.rate_limiter.record_request()

            if not response.data:
                return []

            # Build user lookup
            users = {u.id: u for u in (response.includes.get("users", []) or [])}

            tweets = []
            for tweet in response.data:
                author = users.get(tweet.author_id)
                tweets.append({
                    "tweet_id": str(tweet.id),
                    "text": tweet.text,
                    "created_at": tweet.created_at,
                    "author_id": str(tweet.author_id),
                    "author_handle": f"@{author.username}" if author else None,
                    "author_name": author.name if author else None,
                    "retweet_count": tweet.public_metrics.get("retweet_count", 0)
                    if tweet.public_metrics
                    else 0,
                    "like_count": tweet.public_metrics.get("like_count", 0)
                    if tweet.public_metrics
                    else 0,
                })

            return tweets

        except tweepy.TooManyRequests:
            logger.warning("Twitter rate limit exceeded")
            self.rate_limiter.reset_time = datetime.now() + timedelta(
                seconds=self.rate_limiter.window_seconds
            )
            return []
        except tweepy.TweepyException as e:
            logger.error(f"Twitter API error: {e}")
            return []

    async def fetch_for_artist(
        self,
        artist: Artist,
        db: AsyncSession,
        max_results: int = 100,
    ) -> List[Announcement]:
        """Fetch and store announcements for an artist.

        Returns list of new announcements created.
        """
        if not self.is_configured:
            return []

        # Get last processed tweet ID for this artist
        last_tweet = await db.execute(
            select(Announcement)
            .where(Announcement.artist_id == artist.id)
            .order_by(Announcement.tweeted_at.desc())
            .limit(1)
        )
        last = last_tweet.scalar_one_or_none()
        since_id = last.tweet_id if last else None

        # Build search query
        query = self.query_builder.build_query(artist)
        logger.info(f"Searching for {artist.name}: {query}")

        # Search tweets
        tweets = await self.search_tweets(query, max_results, since_id)

        # Also search official accounts if configured
        official_query = self.query_builder.build_official_query(artist)
        if official_query:
            official_tweets = await self.search_tweets(official_query, 50, since_id)
            # Merge and deduplicate
            seen_ids = {t["tweet_id"] for t in tweets}
            for t in official_tweets:
                if t["tweet_id"] not in seen_ids:
                    t["is_official"] = True
                    tweets.append(t)

        # Store announcements
        new_announcements = []
        official_handles = set(h.lower() for h in artist.get_all_twitter_handles())

        for tweet_data in tweets:
            # Check if already exists
            existing = await db.execute(
                select(Announcement).where(
                    Announcement.tweet_id == tweet_data["tweet_id"]
                )
            )
            if existing.scalar_one_or_none():
                continue

            # Determine if from official account
            is_official = tweet_data.get("is_official", False)
            if tweet_data.get("author_handle"):
                is_official = (
                    is_official
                    or tweet_data["author_handle"].lower() in official_handles
                )

            announcement = Announcement(
                artist_id=artist.id,
                tweet_id=tweet_data["tweet_id"],
                tweet_text=tweet_data["text"],
                tweet_url=f"https://twitter.com/i/status/{tweet_data['tweet_id']}",
                author_handle=tweet_data.get("author_handle", "unknown"),
                author_name=tweet_data.get("author_name"),
                tweeted_at=tweet_data["created_at"],
                is_official=is_official,
                is_processed=False,
                retweet_count=tweet_data.get("retweet_count", 0),
                like_count=tweet_data.get("like_count", 0),
            )

            db.add(announcement)
            new_announcements.append(announcement)

        if new_announcements:
            await db.commit()
            logger.info(
                f"Found {len(new_announcements)} new announcements for {artist.name}"
            )

        return new_announcements

    async def fetch_all_artists(
        self,
        db: AsyncSession,
        force: bool = False,
    ) -> dict:
        """Fetch announcements for all favorite artists.

        Returns summary of results.
        """
        # Get all favorite artists
        result = await db.execute(select(Artist).where(Artist.is_favorite == True))
        artists = result.scalars().all()

        summary = {
            "artists_processed": 0,
            "total_new_announcements": 0,
            "errors": [],
        }

        for artist in artists:
            try:
                if not force and not self.rate_limiter.can_request:
                    summary["errors"].append(
                        f"Rate limit reached, skipped {artist.name}"
                    )
                    continue

                announcements = await self.fetch_for_artist(artist, db)
                summary["artists_processed"] += 1
                summary["total_new_announcements"] += len(announcements)

            except Exception as e:
                logger.error(f"Error fetching for {artist.name}: {e}")
                summary["errors"].append(f"{artist.name}: {str(e)}")

        return summary
