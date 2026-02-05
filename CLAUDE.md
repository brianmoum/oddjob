# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OddJob is a Python-based automated restaurant reservation system. The core use case is making reservations at high-demand restaurants that release availability at a fixed time in advance (e.g., 9 AM, 30 days out) and sell out within seconds. OddJob creates timed "jobs" that execute at the exact release moment to secure reservations faster than manual booking.

## Project Direction

**Current state**: API-based approach using Resy endpoints (`src/api/resy_client.py` + `src/cli.py`). Fast, reliable, serverless-compatible.

**Legacy**: Selenium-based browser automation in `src/web/` (deprecated).

**Planned features**:
- Serverless cloud deployment (jobs run without local machine)
- Bulk job creation
- Resy account rotation (create/manage multiple accounts to avoid bot detection)
- SMS/mobile interface for creating jobs on the go
- Multi-platform support (OpenTable, Sevenrooms, etc.)

## Running the Application

From the `src/` directory:

```bash
# Book a reservation (API-based)
python cli.py \
  --venue-id 25973 \
  --date 2026-02-19 \
  --guests 2 \
  --best 19:00 \
  --earliest 18:00 \
  --latest 21:00

# Schedule a booking for release time
python cli.py \
  --venue-id 25973 \
  --date 2026-02-19 \
  --guests 2 \
  --best 19:00 \
  --earliest 18:00 \
  --latest 21:00 \
  --run-at "2026-02-05 09:00:00"

# Test without actually booking
python cli.py --venue-id 25973 --date 2026-02-19 --guests 2 \
  --best 19:00 --earliest 18:00 --latest 21:00 --dry-run

# Prefer specific table types
python cli.py --venue-id 25973 --date 2026-02-19 --guests 2 \
  --best 19:00 --earliest 18:00 --latest 21:00 \
  --table-type "Indoor Dining" --table-type "Patio"
```

## Configuration

Requires `config.json` in the working directory:
```json
{
  "api_key": "YOUR_RESY_API_KEY",
  "auth_token": "YOUR_RESY_AUTH_TOKEN"
}
```

**How to get credentials** (from browser dev tools while logged into Resy):
- `api_key`: Found in `Authorization` header as `ResyAPI api_key="..."`
- `auth_token`: Found in `x-resy-auth-token` header

You also need `venue_id` for each restaurant (visible in `/find` API calls or URL params when viewing a restaurant on Resy).

## Resy API Reference

Base URL: `https://api.resy.com`

### Headers (all requests)
```
Authorization: ResyAPI api_key="YOUR_API_KEY"
x-resy-auth-token: YOUR_AUTH_TOKEN
```

### Booking Flow (3 calls)

**1. Find available slots**
```
GET /4/find?lat=0&long=0&day=YYYY-MM-DD&party_size=N&venue_id=ID
```
Response contains `results.venues[0].slots[]` with `config.token` (the config_id) for each time slot.

**2. Get reservation details**
```
GET /3/details?config_id=TOKEN&day=YYYY-MM-DD&party_size=N
```
Response contains `book_token.value` and `user.payment_methods[0].id`.

**3. Book reservation**
```
POST /3/book
Content-Type: application/x-www-form-urlencoded

book_token=TOKEN&struct_payment_method={"id":PAYMENT_ID}
```
Response contains `resy_token` on success.

## Architecture

### API Client (New)
`src/api/resy_client.py` - Direct API implementation:
- `ResyClient` class with methods: `find_reservations()`, `get_reservation_details()`, `book_reservation()`
- `book()` high-level method that combines all three steps with time preference matching
- `load_client_from_config()` helper to load credentials from config.json

### Legacy (Selenium)

The old implementation uses Selenium browser automation. Being phased out.

### Core Flow (Legacy)
1. **ResyInterface.py** - CLI entry point, parses arguments, handles scheduled execution via `--run-at`
2. **booking.py** - Validates inputs and orchestrates the booking process
3. **ResyDaemon.py** - Selenium automation: navigates Resy, selects time slots, handles login, completes booking

### Key Modules
- `src/web/` - Browser automation (ResyDaemon handles page navigation and booking flow)
- `src/infra/` - Restaurant lookup utilities (ResyRestaurantLookup searches Resy by name)
- `src/util/` - Time parsing/conversion (ResyTimeFunctions converts between time formats)
- `src/domains/models/` - Data models (User, ReservationRequest) - scaffolding for future features
- `src/interfaces/` - CLI interfaces

### Time Preference Algorithm
The booking system uses a "preferred times" algorithm in `ResyDaemon.getPreferredTimes()` that creates a priority-ordered list starting from the ideal time and alternating outward (e.g., 7:00 -> 7:15 -> 6:45 -> 7:30 -> 6:30...) until reaching the earliest/latest boundaries.

## Dependencies

- requests (API client)
- selenium, webdriver-manager (legacy browser automation)
- beautifulsoup4, pandas (legacy web scraping utilities)

## Known Limitations (Legacy Selenium Approach)

- Currently hardcoded to grab "Dinner" service window (ShiftInventory__shift--last element)
- City defaults to new-york-ny
- Bot detection may require manual CAPTCHA intervention
- Selenium is slow and requires a browser/display - not suitable for serverless

These limitations are why we're moving to an API-based approach.
