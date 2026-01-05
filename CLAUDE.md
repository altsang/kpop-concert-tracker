# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Development
```bash
# Activate virtual environment (required first)
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Run the development server with auto-reload
uvicorn app.main:app --reload

# Alternative: run directly via Python
python -m app.main

# Install dependencies
pip install -r requirements.txt

# Install new package and update requirements
pip install package_name && pip freeze > requirements.txt
```

### Database
```bash
# Database is auto-created on first run via app lifespan
# Location: ./concerts.db (SQLite)
# To reset database: delete concerts.db and restart the app
```

### API Testing
```bash
# Interactive API docs (Swagger UI)
open http://localhost:8000/docs

# Test endpoints with curl
curl http://localhost:8000/api/v1/artists
curl http://localhost:8000/api/v1/concerts
```

## Architecture

### FastAPI Application Structure

**Entry Point**: `app/main.py`
- Uses async lifespan context manager for database initialization
- Mounts static files and Jinja2 templates for the dashboard UI
- All API routes are prefixed with `/api/v1`

**Database Layer**: Async SQLAlchemy 2.0
- `app/database.py`: Async engine and session management
- `app/models/`: SQLAlchemy ORM models with async support
- Uses `async_sessionmaker` for session creation
- IMPORTANT: All database operations must be async (use `await`)
- Get database session via `get_db()` dependency injection

**API Layer**: `app/api/v1/`
- Modular routers for different resources (artists, tours, concerts, twitter, dashboard)
- All routers use async route handlers
- Database dependency: `db: AsyncSession = Depends(get_db)`

**Services**: `app/services/`
- `twitter_service.py`: Twitter API integration with rate limiting
- `parser_service.py`: Tweet parsing logic for extracting concert info

### Data Model Relationships

```
Artist (1) ──────< (N) Tour (1) ──────< (N) TourDate
   │                   │
   │                   │
   └──────< (N) Announcement
```

**Key Models**:
- `Artist`: K-pop artists/groups with twitter handles and aliases
- `Tour`: Concert tours with metadata (year, status, regions)
- `TourDate`: Individual concert dates with special flags (is_seoul_kickoff, is_encore, is_finale)
- `Announcement`: Raw tweets about concerts, linked to Artist and optionally Tour

**Important Model Features**:
- All models inherit from `Base` (DeclarativeBase)
- `TimestampMixin` provides created_at/updated_at timestamps
- Relationships use cascade delete (`cascade="all, delete-orphan"`)
- TourDate has computed properties: `is_past`, `is_today`, `is_tbd`, `days_until`

### Async Pattern Critical Notes

**NEVER access relationships outside async context**. This app uses async SQLAlchemy which requires:

1. **Always use `await` for relationship access**:
   ```python
   # WRONG - will cause MissingGreenlet error
   tours_count = len(artist.tours)

   # CORRECT - use selectinload or joinedload
   from sqlalchemy.orm import selectinload
   stmt = select(Artist).options(selectinload(Artist.tours))
   result = await db.execute(stmt)
   artist = result.scalar_one()
   tours_count = len(artist.tours)
   ```

2. **Load relationships eagerly with options()**:
   - Use `selectinload()` for collections (one-to-many)
   - Use `joinedload()` for single items (many-to-one)

3. **All database queries must use `await`**:
   ```python
   # CORRECT pattern
   result = await db.execute(select(Artist))
   artists = result.scalars().all()
   ```

### Frontend Architecture

**Dashboard**: `templates/index.html`
- Vanilla JavaScript (no framework)
- API client in `static/js/api.js`
- UI logic in `static/js/app.js`
- Styling in `static/css/styles.css`

**Visual Highlighting**:
- Seoul kickoff shows: Yellow border + amber gradient
- Encore shows: Blue border + blue gradient
- Finale shows: Purple border + purple gradient
- Today's shows: Green border + green gradient
- Past concerts: Gray background + strikethrough
- TBD dates: "TBD" badge with yellow styling

### Twitter Integration Flow

1. `TwitterService.fetch_for_artist()` searches Twitter API
2. Results stored as `Announcement` records (unprocessed)
3. `TweetParser.parse_tweet()` extracts dates, venues, cities
4. Parsed data creates/updates `Tour` and `TourDate` records
5. Rate limiting enforced via `RateLimiter` class

### Configuration

`app/config.py` uses pydantic-settings:
- Loads from `.env` file (copy from `.env.example`)
- `TWITTER_BEARER_TOKEN`: Optional, for Twitter API access
- `DATABASE_URL`: Defaults to `sqlite+aiosqlite:///./concerts.db`
- `DEBUG`: Enable SQLAlchemy query logging

## Development Patterns

### Adding New API Endpoints

1. Create route handler in appropriate file under `app/api/v1/`
2. Use async def with `db: AsyncSession = Depends(get_db)`
3. Use Pydantic schemas from `app/schemas/` for request/response
4. Remember to eagerly load relationships with `.options()`

### Adding Database Fields

1. Update model in `app/models/`
2. Delete `concerts.db` to recreate schema (no migrations setup yet)
3. Update corresponding Pydantic schemas in `app/schemas/`

### Tweet Parser Customization

Edit patterns in `TweetParser` class:
- `DATE_PATTERNS`: Regex patterns for date extraction
- `CITY_COUNTRY_MAP`: Known cities with country/region mappings
- `VENUE_INDICATORS`: Keywords identifying venue names
- `TOUR_PATTERNS`: Regex for tour name extraction

## Testing Notes

No formal test suite exists yet. Manual testing via:
- API docs at `/docs`
- Dashboard UI at `/`
- Direct API calls with curl/httpx
