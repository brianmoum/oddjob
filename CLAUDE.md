# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OddJob is a Python-based automated restaurant reservation system, currently focused on Resy. It uses Selenium for browser automation to book reservations at high-demand restaurants when slots become available.

## Running the Application

From the `src/` directory:

```bash
# Book a reservation
python interfaces/ResyInterface.py \
  --restaurant lartusi-ny \
  --date 2025-03-15 \
  --guests 4 \
  --best 7:00 \
  --earliest 6:00 \
  --latest 9:30

# Schedule a booking for a specific time (for release-day reservations)
python interfaces/ResyInterface.py \
  --restaurant lartusi-ny \
  --date 2025-03-15 \
  --guests 4 \
  --best 7:00 \
  --earliest 6:00 \
  --latest 9:30 \
  --run-at "2025-03-01 09:00:00"
```

## Configuration

Requires `config.json` in the working directory with Resy credentials:
```json
{"username": "your@email.com", "password": "your_password"}
```

## Architecture

### Core Flow
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

- selenium, webdriver-manager (browser automation)
- beautifulsoup4, pandas, requests (web scraping utilities)

## Known Limitations

- Currently hardcoded to grab "Dinner" service window (ShiftInventory__shift--last element)
- City defaults to new-york-ny
- Bot detection may require manual CAPTCHA intervention
