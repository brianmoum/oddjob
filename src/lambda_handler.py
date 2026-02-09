"""
AWS Lambda handler for OddJob reservation booking.

This function is triggered by EventBridge Scheduler at the exact time
reservations are released. Supports multiple platforms via the 'platform' field.

Expected event format:
{
    "platform": "resy",  // optional, default "resy"
    "venue_id": "25973",
    "date": "2026-02-19",
    "party_size": 2,
    "best": "19:00",
    "earliest": "18:00",
    "latest": "21:00",
    "table_types": ["Indoor Dining"],  // optional
    "retries": 5  // optional, default 3
}
"""

import json
import boto3
from botocore.exceptions import ClientError

from api.base import BookingClientError
from api.client_factory import create_client
from api.slot_selection import select_best_slot
from cli import generate_preferred_times, validate_times


def get_secrets(platform: str = "resy"):
    """Retrieve booking credentials from AWS Secrets Manager."""
    secret_name = f"oddjob/{platform}-credentials"
    region_name = "us-east-1"

    client = boto3.client("secretsmanager", region_name=region_name)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        return json.loads(response["SecretString"])
    except ClientError as e:
        raise Exception(f"Failed to retrieve secrets for {platform}: {e}")


def lambda_handler(event, context):
    """
    Main Lambda entry point.

    Returns:
        dict with statusCode and body
    """
    print(f"Received event: {json.dumps(event)}")

    # Parse event
    platform = event.get("platform", "resy")
    venue_id = str(event["venue_id"])
    date = event["date"]
    party_size = event["party_size"]
    best = event["best"]
    earliest = event["earliest"]
    latest = event["latest"]
    table_types = event.get("table_types")
    retries = event.get("retries", 3)

    # Validate times
    try:
        validate_times(best, earliest, latest)
    except SystemExit:
        return {
            "statusCode": 400,
            "body": json.dumps({"error": "Invalid time parameters"})
        }

    # Get credentials from Secrets Manager
    try:
        credentials = get_secrets(platform)
    except Exception as e:
        print(f"Failed to get secrets: {e}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)})
        }

    # Generate preferred times
    preferred_times = generate_preferred_times(best, earliest, latest)
    print(f"Preferred times: {preferred_times}")

    # Create client and attempt booking
    try:
        client = create_client(platform, credentials)
    except BookingClientError as e:
        print(f"Failed to create client: {e}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)})
        }

    for attempt in range(1, retries + 1):
        try:
            print(f"Attempt {attempt}/{retries}")

            # Find available slots
            slots = client.find_slots(venue_id, date, party_size)

            if not slots:
                print("No slots available")
                continue

            print(f"Found {len(slots)} slots")

            selected_slot = select_best_slot(slots, preferred_times, table_types)

            if not selected_slot:
                print("No slots match preferred times")
                continue

            print(f"Selected: {selected_slot.time} - {selected_slot.table_type}")

            result = client.book_slot(selected_slot, date, party_size)

            print(f"SUCCESS! Confirmation: {result.confirmation_id}")

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "success": True,
                    "platform": platform,
                    "confirmation_id": result.confirmation_id,
                    "reservation_id": result.reservation_id,
                    "time": selected_slot.time,
                    "table_type": selected_slot.table_type,
                })
            }

        except BookingClientError as e:
            print(f"API Error: {e}")

    # All retries failed
    return {
        "statusCode": 500,
        "body": json.dumps({
            "success": False,
            "error": "Failed to book after all retries"
        })
    }
