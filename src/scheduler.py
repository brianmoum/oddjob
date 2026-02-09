"""
EventBridge Scheduler wrapper for OddJob cloud-scheduled bookings.

Creates one-time schedules that invoke the Lambda function at exact times
(e.g., 9:00 AM when reservations are released). Schedules auto-delete after firing.
"""

import json

import boto3
from botocore.exceptions import ClientError

# AWS resource constants
LAMBDA_ARN = "arn:aws:lambda:us-east-1:145713876007:function:oddjob-resy-booker"
SCHEDULER_ROLE_ARN = "arn:aws:iam::145713876007:role/oddjob-scheduler-role"
SCHEDULE_GROUP = "oddjob"
REGION = "us-east-1"


def _get_client():
    """Get an EventBridge Scheduler client."""
    return boto3.client("scheduler", region_name=REGION)


def _ensure_schedule_group(client):
    """Create the oddjob schedule group if it doesn't exist."""
    try:
        client.get_schedule_group(Name=SCHEDULE_GROUP)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            client.create_schedule_group(Name=SCHEDULE_GROUP)
            print(f"Created schedule group: {SCHEDULE_GROUP}")
        else:
            raise


def _make_schedule_name(venue_id: str, date: str, run_at_utc: str, platform: str = "resy") -> str:
    """
    Generate a deterministic, readable schedule name.

    Format: oddjob-{platform}-{venue_id}-{date}-at-{run_at_utc}
    E.g.: oddjob-resy-25973-2026-02-28-at-2026-02-27T14-00-00
    """
    # Replace colons with dashes for EventBridge name compatibility
    safe_run_at = run_at_utc.replace(":", "-")
    return f"oddjob-{platform}-{venue_id}-{date}-at-{safe_run_at}"


def schedule_booking(
    venue_id: str,
    date: str,
    party_size: int,
    best: str,
    earliest: str,
    latest: str,
    run_at_utc: str,
    table_types: list[str] | None = None,
    retries: int = 3,
    platform: str = "resy",
) -> str:
    """
    Create a one-time EventBridge schedule that invokes the Lambda at run_at_utc.

    Args:
        venue_id: Platform-specific venue ID
        date: Reservation date (YYYY-MM-DD)
        party_size: Number of guests
        best: Ideal time (e.g., "19:00")
        earliest: Earliest acceptable time
        latest: Latest acceptable time
        run_at_utc: UTC execution time (YYYY-MM-DDTHH:MM:SS)
        table_types: Optional preferred table types
        retries: Number of booking retry attempts
        platform: Booking platform (default: "resy")

    Returns:
        The schedule name.
    """
    client = _get_client()
    _ensure_schedule_group(client)

    schedule_name = _make_schedule_name(venue_id, date, run_at_utc, platform)

    # Build the Lambda payload (matches lambda_handler.py event format)
    payload = {
        "platform": platform,
        "venue_id": venue_id,
        "date": date,
        "party_size": party_size,
        "best": best,
        "earliest": earliest,
        "latest": latest,
        "retries": retries,
    }
    if table_types:
        payload["table_types"] = table_types

    client.create_schedule(
        Name=schedule_name,
        GroupName=SCHEDULE_GROUP,
        ScheduleExpression=f"at({run_at_utc})",
        ScheduleExpressionTimezone="UTC",
        FlexibleTimeWindow={"Mode": "OFF"},
        Target={
            "Arn": LAMBDA_ARN,
            "RoleArn": SCHEDULER_ROLE_ARN,
            "Input": json.dumps(payload),
        },
        ActionAfterCompletion="DELETE",
    )

    return schedule_name


def list_schedules() -> list[dict]:
    """
    List all schedules in the oddjob group.

    Returns:
        List of schedule dicts with name, state, and schedule expression.
    """
    client = _get_client()

    try:
        response = client.list_schedules(GroupName=SCHEDULE_GROUP)
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceNotFoundException":
            return []
        raise

    schedules = []
    for s in response.get("Schedules", []):
        # Fetch full details to get the schedule expression and payload
        try:
            detail = client.get_schedule(
                Name=s["Name"], GroupName=SCHEDULE_GROUP
            )
            payload = json.loads(detail["Target"].get("Input", "{}"))
            expression = detail.get("ScheduleExpression", "")
        except (ClientError, json.JSONDecodeError):
            payload = {}
            expression = ""

        schedules.append({
            "name": s["Name"],
            "state": s.get("State", "UNKNOWN"),
            "schedule": expression,
            "payload": payload,
        })

    return schedules


def cancel_schedule(name: str) -> None:
    """
    Delete a schedule by name.

    Args:
        name: The schedule name to delete.
    """
    client = _get_client()
    client.delete_schedule(Name=name, GroupName=SCHEDULE_GROUP)
