# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

OddJob is a Python-based automated restaurant reservation system. The core use case is making reservations at high-demand restaurants that release availability at a fixed time in advance (e.g., 9 AM, 30 days out) and sell out within seconds. OddJob creates timed "jobs" that execute at the exact release moment to secure reservations faster than manual booking.

## Project Direction

**Current state**: Multi-platform API-based approach with a shared `BookingClient` interface (`src/api/base.py`). Resy is fully implemented; OpenTable is stubbed out awaiting API capture. Fast, reliable, serverless-compatible.

**Legacy**: Selenium-based browser automation in `src/web/` (deprecated).

**Planned features**:
- Bulk job creation
- Resy account rotation (create/manage multiple accounts to avoid bot detection)
- SMS/mobile interface for creating jobs on the go
- OpenTable client implementation (stub exists, needs API capture from browser dev tools)
- Additional platform support (Sevenrooms, etc.)

## Running the Application

From the `src/` directory:

```bash
# Book a reservation (Resy — default platform)
python cli.py \
  --venue-id 25973 \
  --date 2026-02-19 \
  --guests 2 \
  --best 19:00 \
  --earliest 18:00 \
  --latest 21:00

# Explicit platform flag (same as above)
python cli.py --platform resy \
  --venue-id 25973 \
  --date 2026-02-19 \
  --guests 2 \
  --best 19:00 \
  --earliest 18:00 \
  --latest 21:00

# OpenTable (stub — not yet implemented, will error)
python cli.py --platform opentable \
  --venue-id some-venue-id \
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

### Cloud Scheduling (EventBridge)

Requires AWS credentials (use `aws-vault exec oddjob --` prefix):

```bash
# Schedule a booking job in the cloud (runs on Lambda at the specified time)
aws-vault exec oddjob -- python cli.py \
  --venue-id 25973 \
  --date 2026-02-28 \
  --guests 2 \
  --best 19:00 \
  --earliest 18:00 \
  --latest 21:00 \
  --schedule "2026-02-27 09:00:00"

# Schedule with explicit platform
aws-vault exec oddjob -- python cli.py --platform resy \
  --venue-id 25973 \
  --date 2026-02-28 \
  --guests 2 \
  --best 19:00 \
  --earliest 18:00 \
  --latest 21:00 \
  --schedule "2026-02-27 09:00:00"

# List all scheduled jobs (shows platform in output)
aws-vault exec oddjob -- python cli.py --list-jobs

# Cancel a scheduled job
aws-vault exec oddjob -- python cli.py --cancel-job oddjob-resy-25973-2026-02-28-at-2026-02-27T14-00-00
```

`--schedule` takes a local time and converts it to UTC for EventBridge. Schedules auto-delete after firing.

## Configuration

Requires `config.json` in the project root. Supports two formats:

**Legacy flat format** (Resy-only, backwards compatible):
```json
{
  "api_key": "YOUR_RESY_API_KEY",
  "auth_token": "YOUR_RESY_AUTH_TOKEN"
}
```

**Multi-platform nested format**:
```json
{
  "resy": {
    "api_key": "YOUR_RESY_API_KEY",
    "auth_token": "YOUR_RESY_AUTH_TOKEN"
  },
  "opentable": {
    "...": "credentials TBD after API capture"
  }
}
```

### Getting Resy Credentials

From browser dev tools while logged into Resy:
- `api_key`: Found in `Authorization` header as `ResyAPI api_key="..."`
- `auth_token`: Found in `x-resy-auth-token` header
- `venue_id`: Visible in `/find` API calls or URL params when viewing a restaurant on Resy

### Getting OpenTable Credentials (TODO)

OpenTable client is stubbed but not yet implemented. To capture the API:
1. Open browser dev tools (Network tab) while logged into OpenTable
2. Search for a restaurant and select a date/time/party size
3. Watch network requests — note endpoints, headers, and payloads
4. Complete a booking and capture the booking request
5. Fill in `src/api/opentable_client.py` with the captured API details

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

### Multi-Platform Interface
`src/api/base.py` - Shared interface:
- `Slot` dataclass: platform-agnostic slot with `platform_data` dict for opaque platform-specific data
- `BookingConfirmation` dataclass: platform-agnostic booking result
- `BookingClientError` exception: base error with `platform` field
- `BookingClient` ABC: `find_slots()` and `book_slot()` methods

`src/api/slot_selection.py` - Shared slot selection:
- `select_best_slot()` picks the best slot from any platform based on time/table type preferences

`src/api/client_factory.py` - Client creation:
- `create_client(platform, credentials)` creates the right client for a platform
- `load_client_from_config(platform, config_path)` loads from config.json (supports legacy flat + nested formats)

### Platform Clients
`src/api/resy_client.py` - Resy API implementation:
- `ResyClient` extends `BookingClient`
- Internal methods: `find_reservations()`, `get_reservation_details()`, `book_reservation()`
- Interface methods: `find_slots()` wraps find_reservations, `book_slot()` runs details+book flow

`src/api/opentable_client.py` - OpenTable stub:
- `OpenTableClient` extends `BookingClient`
- Both methods raise `BookingClientError` until API is captured and implemented

### Cloud Scheduler
`src/scheduler.py` - EventBridge Scheduler wrapper:
- `schedule_booking()` creates a one-time `at()` schedule targeting the Lambda, includes `platform` in payload
- Schedule names include platform: `oddjob-{platform}-{venue_id}-{date}-at-{run_at_utc}`
- `list_schedules()` lists all schedules in the `oddjob` group with payload details
- `cancel_schedule()` deletes a schedule by name
- Schedules auto-delete after firing (`ActionAfterCompletion="DELETE"`)

### Lambda Handler
`src/lambda_handler.py` - AWS Lambda entry point invoked by EventBridge Scheduler. Reads `platform` from event (default: "resy"), fetches credentials from `oddjob/{platform}-credentials` in Secrets Manager, and runs the booking flow via the shared `BookingClient` interface.

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

## AWS Setup

### IAM Roles
Two IAM roles are needed (created manually in the AWS Console due to session token limitations):

1. **`oddjob-lambda-role`** — Lambda execution role. Allows the Lambda to read from Secrets Manager.
2. **`oddjob-scheduler-role`** — EventBridge Scheduler role. Trust policy for `scheduler.amazonaws.com`, with permission to `lambda:InvokeFunction` on the Lambda.

### Resources
- **Lambda**: `oddjob-resy-booker` (us-east-1) — handles all platforms
- **Secrets** (Secrets Manager): `oddjob/resy-credentials`, `oddjob/opentable-credentials` (when implemented)
- **Schedule Group**: `oddjob` (EventBridge Scheduler)

Run `./deploy.sh` to deploy. It will print instructions for any missing roles.

## Dependencies

- requests (API client)
- boto3 (AWS SDK — cloud scheduling, Lambda handler)
- selenium, webdriver-manager (legacy browser automation)
- beautifulsoup4, pandas (legacy web scraping utilities)

## Known Limitations (Legacy Selenium Approach)

- Currently hardcoded to grab "Dinner" service window (ShiftInventory__shift--last element)
- City defaults to new-york-ny
- Bot detection may require manual CAPTCHA intervention
- Selenium is slow and requires a browser/display - not suitable for serverless

These limitations are why we're moving to an API-based approach.
