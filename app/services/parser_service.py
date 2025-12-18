"""Tweet parsing service for extracting concert information."""

import re
from dataclasses import dataclass, field
from datetime import date
from typing import List, Optional, Tuple

from dateutil import parser as date_parser


@dataclass
class ParsedLocation:
    """Parsed location from tweet."""

    city: str
    venue: Optional[str] = None
    country: Optional[str] = None
    region: Optional[str] = None


@dataclass
class ParsedDate:
    """Parsed date from tweet."""

    date: Optional[date] = None
    end_date: Optional[date] = None
    raw_text: str = ""
    is_tbd: bool = False


@dataclass
class ParsedConcertInfo:
    """Result of parsing a tweet for concert information."""

    dates: List[ParsedDate] = field(default_factory=list)
    locations: List[ParsedLocation] = field(default_factory=list)
    tour_name: Optional[str] = None
    is_seoul_related: bool = False
    is_encore: bool = False
    has_tbd: bool = False
    confidence: float = 0.0
    raw_text: str = ""


class TweetParser:
    """Parse concert information from tweets."""

    # Date patterns
    DATE_PATTERNS = [
        # "March 15, 2025" or "March 15th, 2025"
        r"(\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:st|nd|rd|th)?,?\s*\d{4})",
        # "March 15-16, 2025"
        r"(\b(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{1,2}(?:\s*[-&]\s*\d{1,2})?,?\s*\d{4})",
        # "15/03/2025" or "03/15/2025"
        r"(\b\d{1,2}/\d{1,2}/\d{2,4})",
        # "2025-03-15"
        r"(\b\d{4}-\d{2}-\d{2})",
        # "15 March 2025"
        r"(\b\d{1,2}\s+(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)\s+\d{4})",
    ]

    # Venue indicators
    VENUE_INDICATORS = [
        "stadium",
        "arena",
        "dome",
        "center",
        "centre",
        "hall",
        "park",
        "garden",
        "coliseum",
        "amphitheatre",
        "amphitheater",
        "forum",
        "pavilion",
    ]

    # Seoul keywords
    SEOUL_KEYWORDS = ["seoul", "서울", "kspo", "gocheok", "jamsil", "olympic park"]

    # Encore keywords
    ENCORE_KEYWORDS = [
        "encore",
        "additional",
        "added dates",
        "added shows",
        "extra dates",
        "final",
        "last show",
        "grand finale",
    ]

    # TBD indicators
    TBD_PATTERNS = [
        r"more\s+(?:dates|cities|shows).*(?:coming|soon|tba|tbd)",
        r"additional.*(?:dates|shows).*(?:announced|coming)",
        r"dates?\s+to\s+be\s+(?:announced|determined)",
        r"\+\s*more",
        r"and\s+more",
        r"tba",
        r"tbd",
    ]

    # Tour name patterns
    TOUR_PATTERNS = [
        r"([A-Z][A-Z\s\d]+(?:TOUR|WORLD TOUR|CONCERT))",  # "BORN PINK WORLD TOUR"
        r"['\"]([^'\"]+(?:tour|concert))['\"]",  # Quoted tour names
        r"(\w+\s+(?:TOUR|Tour)\s*\d*)",  # "Name Tour 2025"
    ]

    # City-Country mappings for common K-pop tour cities
    CITY_COUNTRY_MAP = {
        "seoul": ("Seoul", "South Korea", "Asia"),
        "busan": ("Busan", "South Korea", "Asia"),
        "tokyo": ("Tokyo", "Japan", "Asia"),
        "osaka": ("Osaka", "Japan", "Asia"),
        "bangkok": ("Bangkok", "Thailand", "Asia"),
        "singapore": ("Singapore", "Singapore", "Asia"),
        "jakarta": ("Jakarta", "Indonesia", "Asia"),
        "manila": ("Manila", "Philippines", "Asia"),
        "taipei": ("Taipei", "Taiwan", "Asia"),
        "hong kong": ("Hong Kong", "Hong Kong", "Asia"),
        "los angeles": ("Los Angeles", "USA", "North America"),
        "new york": ("New York", "USA", "North America"),
        "chicago": ("Chicago", "USA", "North America"),
        "dallas": ("Dallas", "USA", "North America"),
        "atlanta": ("Atlanta", "USA", "North America"),
        "san francisco": ("San Francisco", "USA", "North America"),
        "seattle": ("Seattle", "USA", "North America"),
        "toronto": ("Toronto", "Canada", "North America"),
        "vancouver": ("Vancouver", "Canada", "North America"),
        "london": ("London", "UK", "Europe"),
        "paris": ("Paris", "France", "Europe"),
        "berlin": ("Berlin", "Germany", "Europe"),
        "amsterdam": ("Amsterdam", "Netherlands", "Europe"),
        "sydney": ("Sydney", "Australia", "Oceania"),
        "melbourne": ("Melbourne", "Australia", "Oceania"),
    }

    def parse_tweet(self, tweet_text: str) -> ParsedConcertInfo:
        """Extract concert information from tweet text."""
        result = ParsedConcertInfo(raw_text=tweet_text)
        text_lower = tweet_text.lower()

        # Extract dates
        result.dates = self._extract_dates(tweet_text)

        # Extract locations
        result.locations = self._extract_locations(tweet_text)

        # Extract tour name
        result.tour_name = self._extract_tour_name(tweet_text)

        # Check for Seoul
        result.is_seoul_related = self._check_seoul(text_lower)

        # Check for encore
        result.is_encore = self._check_encore(text_lower)

        # Check for TBD
        result.has_tbd = self._check_tbd(text_lower)

        # Calculate confidence
        result.confidence = self._calculate_confidence(result)

        return result

    def _extract_dates(self, text: str) -> List[ParsedDate]:
        """Extract dates from text."""
        dates = []
        seen_raw = set()

        for pattern in self.DATE_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                if match in seen_raw:
                    continue
                seen_raw.add(match)

                parsed = self._parse_date_string(match)
                if parsed:
                    dates.append(parsed)

        return dates

    def _parse_date_string(self, date_str: str) -> Optional[ParsedDate]:
        """Parse a date string into a ParsedDate object."""
        try:
            # Check for date range (e.g., "March 15-16, 2025")
            range_match = re.search(r"(\d{1,2})\s*[-&]\s*(\d{1,2})", date_str)
            if range_match:
                # Parse the first date
                first_date_str = re.sub(
                    r"(\d{1,2})\s*[-&]\s*\d{1,2}", r"\1", date_str
                )
                start_date = date_parser.parse(first_date_str, fuzzy=True).date()

                # Calculate end date
                end_day = int(range_match.group(2))
                end_date = start_date.replace(day=end_day)

                return ParsedDate(
                    date=start_date,
                    end_date=end_date,
                    raw_text=date_str,
                )

            # Single date
            parsed = date_parser.parse(date_str, fuzzy=True)
            return ParsedDate(
                date=parsed.date(),
                raw_text=date_str,
            )
        except (ValueError, TypeError):
            return None

    def _extract_locations(self, text: str) -> List[ParsedLocation]:
        """Extract city/venue locations from text."""
        locations = []
        text_lower = text.lower()

        # Check for known cities
        for city_key, (city, country, region) in self.CITY_COUNTRY_MAP.items():
            if city_key in text_lower:
                # Try to find venue near this city mention
                venue = self._find_venue_near_city(text, city_key)
                locations.append(
                    ParsedLocation(
                        city=city,
                        venue=venue,
                        country=country,
                        region=region,
                    )
                )

        # Look for venue patterns even without city match
        for indicator in self.VENUE_INDICATORS:
            pattern = rf"([A-Z][A-Za-z\s]+{indicator})"
            matches = re.findall(pattern, text, re.IGNORECASE)
            for match in matches:
                # Check if this venue is already associated with a location
                venue_lower = match.lower()
                already_found = any(
                    loc.venue and venue_lower in loc.venue.lower()
                    for loc in locations
                )
                if not already_found:
                    locations.append(
                        ParsedLocation(
                            city="Unknown",
                            venue=match.strip(),
                        )
                    )

        return locations

    def _find_venue_near_city(self, text: str, city: str) -> Optional[str]:
        """Find venue name mentioned near a city."""
        # Look for venue indicators in the text
        for indicator in self.VENUE_INDICATORS:
            # Pattern: venue name ending with indicator
            pattern = rf"([A-Z][A-Za-z\s]+{indicator})"
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                return matches[0].strip()
        return None

    def _extract_tour_name(self, text: str) -> Optional[str]:
        """Extract tour name from text."""
        for pattern in self.TOUR_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    def _check_seoul(self, text_lower: str) -> bool:
        """Check if text mentions Seoul."""
        return any(kw in text_lower for kw in self.SEOUL_KEYWORDS)

    def _check_encore(self, text_lower: str) -> bool:
        """Check if this is an encore/additional show announcement."""
        return any(kw in text_lower for kw in self.ENCORE_KEYWORDS)

    def _check_tbd(self, text_lower: str) -> bool:
        """Check if more dates are TBD."""
        return any(re.search(p, text_lower) for p in self.TBD_PATTERNS)

    def _calculate_confidence(self, result: ParsedConcertInfo) -> float:
        """Calculate confidence score for parsed result."""
        score = 0.0

        # Has dates
        if result.dates:
            score += 0.3

        # Has locations
        if result.locations:
            score += 0.3

        # Has tour name
        if result.tour_name:
            score += 0.2

        # Has venue info
        if any(loc.venue for loc in result.locations):
            score += 0.1

        # Has country info
        if any(loc.country for loc in result.locations):
            score += 0.1

        return min(1.0, score)

    def is_concert_related(self, tweet_text: str) -> bool:
        """Quick check if tweet is concert-related."""
        text_lower = tweet_text.lower()
        concert_keywords = [
            "tour",
            "concert",
            "tickets",
            "live",
            "show",
            "stadium",
            "arena",
            "dates",
        ]
        return any(kw in text_lower for kw in concert_keywords)
