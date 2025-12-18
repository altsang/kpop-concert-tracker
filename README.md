# K-Pop Concert Tracker

Track K-pop concert announcements from Twitter and view them in an easy-to-understand dashboard with special highlighting for Seoul kickoff and encore shows.

## Features

- **Artist Management**: Track your favorite K-pop groups
- **Twitter Integration**: Automatically fetch concert announcements from Twitter/X
- **Smart Parsing**: Extract dates, venues, and cities from tweets
- **Visual Dashboard**:
  - Seoul kickoff shows highlighted in yellow
  - Encore shows highlighted in blue
  - Past concerts displayed with strikethrough
  - TBD dates clearly marked
- **Filtering**: Filter by artist, city, date range, and more
- **Tour Tracking**: Track partial announcements and update when more dates are released

## Quick Start

### 1. Install Dependencies

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env and add your Twitter API token (optional)
```

### 3. Run the Application

```bash
# Start the server
uvicorn app.main:app --reload

# Or run directly
python -m app.main
```

### 4. Open Dashboard

Visit [http://localhost:8000](http://localhost:8000) in your browser.

API documentation is available at [http://localhost:8000/docs](http://localhost:8000/docs).

## Twitter API Setup (Optional)

The app works without Twitter API for manual data entry. To enable automatic fetching:

1. Go to [Twitter Developer Portal](https://developer.twitter.com/)
2. Create a new App in a Project
3. Generate a Bearer Token
4. Add to your `.env` file:
   ```
   TWITTER_BEARER_TOKEN=your_token_here
   ```

## Usage

### Adding Artists

1. Click the **+** button in the bottom right
2. Enter the artist name (required)
3. Optionally add Korean name and Twitter handle
4. Click "Add Artist"

### Adding Tours Manually

Use the API to add tours:

```bash
# Add a tour
curl -X POST http://localhost:8000/api/v1/tours \
  -H "Content-Type: application/json" \
  -d '{
    "artist_id": 1,
    "tour_name": "BORN PINK WORLD TOUR",
    "year": 2025,
    "has_tbd_dates": true
  }'

# Add a tour date
curl -X POST http://localhost:8000/api/v1/tours/1/dates \
  -H "Content-Type: application/json" \
  -d '{
    "city": "Seoul",
    "country": "South Korea",
    "venue": "KSPO Dome",
    "date": "2025-03-15",
    "is_seoul_kickoff": true
  }'
```

### Filtering Concerts

Use the sidebar filters to:
- Show/hide specific artists
- Set date range
- Show/hide past concerts
- Show/hide TBD dates
- Filter to Seoul-only or Encore-only shows

## API Endpoints

### Artists
- `GET /api/v1/artists` - List all artists
- `POST /api/v1/artists` - Add new artist
- `GET /api/v1/artists/{id}` - Get artist details
- `PUT /api/v1/artists/{id}` - Update artist
- `DELETE /api/v1/artists/{id}` - Remove artist

### Tours
- `GET /api/v1/tours` - List all tours
- `POST /api/v1/tours` - Create new tour
- `GET /api/v1/tours/{id}` - Get tour with dates
- `PUT /api/v1/tours/{id}` - Update tour
- `POST /api/v1/tours/{id}/dates` - Add date to tour

### Concerts (Dashboard)
- `GET /api/v1/concerts` - List concerts with filters
- `GET /api/v1/concerts/upcoming` - Upcoming concerts only
- `GET /api/v1/concerts/highlights` - Seoul/encore highlights

### Twitter
- `GET /api/v1/twitter/status` - API status
- `POST /api/v1/twitter/refresh` - Trigger data refresh
- `GET /api/v1/twitter/announcements` - List raw announcements
- `POST /api/v1/twitter/parse-test` - Test tweet parsing

### Dashboard
- `GET /api/v1/dashboard/summary` - Dashboard statistics

## Visual Styling Guide

| Concert State | Display Style |
|---------------|---------------|
| Seoul Kickoff | Yellow left border, amber background gradient |
| Encore Show | Blue left border, blue background gradient |
| Finale Show | Purple left border, purple background gradient |
| Today's Show | Green left border, green background gradient |
| Past Concert | Gray background, **strikethrough text** |
| TBD Date | "TBD" text with yellow badge |

## Project Structure

```
kpop-concert-tracker/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application
│   ├── config.py            # Settings
│   ├── database.py          # Database connection
│   ├── models/              # SQLAlchemy models
│   │   ├── artist.py
│   │   ├── tour.py
│   │   ├── tour_date.py
│   │   └── announcement.py
│   ├── schemas/             # Pydantic schemas
│   │   ├── artist.py
│   │   ├── tour.py
│   │   └── concert.py
│   ├── api/v1/              # API endpoints
│   │   ├── artists.py
│   │   ├── tours.py
│   │   ├── concerts.py
│   │   ├── twitter.py
│   │   └── dashboard.py
│   └── services/            # Business logic
│       ├── twitter_service.py
│       └── parser_service.py
├── static/
│   ├── css/styles.css
│   └── js/
│       ├── api.js
│       └── app.js
├── templates/
│   ├── base.html
│   └── index.html
├── requirements.txt
├── .env.example
└── README.md
```

## Technology Stack

- **Backend**: Python 3.11+, FastAPI
- **Database**: SQLite (via SQLAlchemy async)
- **Twitter API**: tweepy
- **Frontend**: Vanilla JavaScript, Jinja2 templates

## License

MIT License
