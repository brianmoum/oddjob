"""
AWS Lambda handler for OddJob Resy booking.

This function is triggered by EventBridge Scheduler at the exact time
reservations are released.

Expected event format:
{
    "venue_id": 25973,
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

from api.resy_client import ResyClient, ResyApiError
from cli import generate_preferred_times, validate_times


def get_secrets():
    """Retrieve Resy credentials from AWS Secrets Manager."""
    secret_name = "oddjob/resy-credentials"
    region_name = "us-east-1"

    client = boto3.client("secretsmanager", region_name=region_name)

    try:
        response = client.get_secret_value(SecretId=secret_name)
        secret = json.loads(response["SecretString"])
        return secret["api_key"], secret["auth_token"]
    except ClientError as e:
        raise Exception(f"Failed to retrieve secrets: {e}")


def lambda_handler(event, context):
    """
    Main Lambda entry point.

    Returns:
        dict with statusCode and body
    """
    print(f"Received event: {json.dumps(event)}")

    # Parse event
    venue_id = event["venue_id"]
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
        api_key, auth_token = get_secrets()
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
    client = ResyClient(api_key=api_key, auth_token=auth_token)

    for attempt in range(1, retries + 1):
        try:
            print(f"Attempt {attempt}/{retries}")

            # Find available slots
            slots = client.find_reservations(venue_id, date, party_size)

            if not slots:
                print("No slots available")
                continue

            print(f"Found {len(slots)} slots")

            # Build lookup by time
            slots_by_time = {}
            for slot in slots:
                if slot.time not in slots_by_time:
                    slots_by_time[slot.time] = []
                slots_by_time[slot.time].append(slot)

            # Find best matching slot
            selected_slot = None
            for pref_time in preferred_times:
                if pref_time in slots_by_time:
                    available = slots_by_time[pref_time]

                    if table_types:
                        for table_type in table_types:
                            for slot in available:
                                if table_type.lower() in slot.table_type.lower():
                                    selected_slot = slot
                                    break
                            if selected_slot:
                                break

                    if not selected_slot:
                        selected_slot = available[0]

                    break

            if not selected_slot:
                print("No slots match preferred times")
                continue

            print(f"Selected: {selected_slot.time} - {selected_slot.table_type}")

            # Get booking details and book
            details = client.get_reservation_details(
                selected_slot.config_token, date, party_size
            )

            result = client.book_reservation(
                details.book_token, details.payment_method_id
            )

            print(f"SUCCESS! Reservation ID: {result.reservation_id}")

            return {
                "statusCode": 200,
                "body": json.dumps({
                    "success": True,
                    "reservation_id": result.reservation_id,
                    "resy_token": result.resy_token,
                    "time": selected_slot.time,
                    "table_type": selected_slot.table_type,
                })
            }

        except ResyApiError as e:
            print(f"API Error: {e}")

    # All retries failed
    return {
        "statusCode": 500,
        "body": json.dumps({
            "success": False,
            "error": "Failed to book after all retries"
        })
    }
