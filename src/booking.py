import json
import os
import sys
from datetime import date, datetime

import ResyTimeFunctions as rtf
import ResyDaemon as rd


def validate_config():
    if not os.path.exists('config.json'):
        print("Error: config.json not found.")
        print("Create a config.json file with your Resy credentials:")
        print('  {"username": "your@email.com", "password": "your_password"}')
        sys.exit(1)

    with open('config.json') as f:
        try:
            auth = json.load(f)
        except json.JSONDecodeError:
            print("Error: config.json is not valid JSON.")
            sys.exit(1)

    if "username" not in auth or "password" not in auth:
        print("Error: config.json must contain 'username' and 'password' keys.")
        sys.exit(1)


def validate_date(date_str):
    try:
        res_date = datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"Error: Invalid date format '{date_str}'. Use YYYY-MM-DD.")
        sys.exit(1)

    if res_date < date.today():
        print(f"Error: Date '{date_str}' is in the past.")
        sys.exit(1)

    return date_str


def validate_times(best, earliest, latest):
    n_best = rtf.timeToFloat(best)
    n_earliest = rtf.timeToFloat(earliest)
    n_latest = rtf.timeToFloat(latest)

    if n_earliest > n_best:
        print(f"Error: Earliest time ({earliest}) is after best time ({best}).")
        sys.exit(1)

    if n_best > n_latest:
        print(f"Error: Best time ({best}) is after latest time ({latest}).")
        sys.exit(1)

    if n_earliest > n_latest:
        print(f"Error: Earliest time ({earliest}) is after latest time ({latest}).")
        sys.exit(1)


def run_booking(restaurant, res_date, guests, best, earliest, latest, city="new-york-ny"):
    """Execute a Resy reservation booking. This function is the core entry point
    that can be called from the CLI, a cloud function handler, or any other context."""

    validate_config()
    validate_date(res_date)
    validate_times(best, earliest, latest)

    preferred_times = rd.getPreferredTimes(best, earliest, latest)

    url = "https://resy.com/cities/{0}/venues/{1}?seats={2}&date={3}".format(
        city, restaurant, guests, res_date
    )

    print(f"Booking: {restaurant}")
    print(f"  Date:   {res_date}")
    print(f"  Guests: {guests}")
    print(f"  Time:   {earliest} - {latest} (ideal: {best})")
    print(f"  URL:    {url}")
    print()

    rd.getPage(url, preferred_times)
