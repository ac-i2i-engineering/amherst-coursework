from django import template
from datetime import datetime

register = template.Library()


@register.filter
def trim(value):
    return value.strip()


@register.filter
def multiply(value, arg):
    """Multiply value by argument"""
    return value * arg


@register.filter
def split(value, arg):
    """Split a string by the given argument"""
    return value.split(arg)


@register.filter
def safe_split(value, arg):
    if not value:
        return [""]
    parts = value.split(arg)
    return parts if len(parts) > 1 else [parts[0], ""]


@register.filter
def get_day_start_time(section, prefix):
    """Get the start time for a given day"""
    # Map prefix to actual field names
    day_map = {
        "mon": "monday",
        "tue": "tuesday",
        "wed": "wednesday",
        "thu": "thursday",
        "fri": "friday",
    }
    day = day_map.get(prefix)
    if day:
        return getattr(section, f"{day}_start_time", None)
    return None


@register.filter
def get_day_end_time(section, prefix):
    """Get the end time for a given day"""
    # Map prefix to actual field names
    day_map = {
        "mon": "monday",
        "tue": "tuesday",
        "wed": "wednesday",
        "thu": "thursday",
        "fri": "friday",
    }
    day = day_map.get(prefix)
    if day:
        return getattr(section, f"{day}_end_time", None)
    return None


@register.filter
def calculate_duration(section, prefix):
    """Calculate duration in pixels (1 hour = 60px)"""
    # Map prefix to actual field names
    day_map = {
        "mon": "monday",
        "tue": "tuesday",
        "wed": "wednesday",
        "thu": "thursday",
        "fri": "friday",
    }
    day = day_map.get(prefix)
    if day:
        start_time = getattr(section, f"{day}_start_time", None)
        end_time = getattr(section, f"{day}_end_time", None)

        if start_time and end_time:
            duration = datetime.combine(datetime.today(), end_time) - datetime.combine(
                datetime.today(), start_time
            )
            return duration.seconds / 60  # Convert to minutes for pixels
    return 0


def calculate_duration_minutes(start_time, end_time):
    """Calculate duration in minutes between two times"""
    if not (start_time and end_time):
        return 0
    duration = datetime.combine(datetime.today(), end_time) - datetime.combine(
        datetime.today(), start_time
    )
    return duration.seconds / 60


@register.filter
def get_class_time(section, day_prefix):
    """Get start/end times and calculate position/height for a specific day"""
    start = section.get(f"{day_prefix}_start_time")
    end = section.get(f"{day_prefix}_end_time")

    if start and end:
        # Parse times using datetime
        start_time = datetime.strptime(start, "%I:%M %p")
        end_time = datetime.strptime(end, "%I:%M %p")

        # The hour is already in 24-hour format after strptime
        start_hour = start_time.hour
        end_hour = end_time.hour

        # Calculate duration in minutes
        duration = ((end_hour - start_hour) * 60) + (
            end_time.minute - start_time.minute
        )

        result = {
            "start": start,
            "end": end,
            "start_hour": start_hour,
            "top_offset": start_time.minute,
            "duration": duration,
        }

        return result

    return None
