# generate_map.py
import folium
from folium.plugins import HeatMap
from django.db.models.functions import ExtractHour
import urllib.parse


def create_map(center_coords, zoom_start=17):
    """Initialize a Folium map centered around the specified coordinates."""
    return folium.Map(location=center_coords, zoom_start=zoom_start)


def add_event_markers(folium_map, events):
    """Add event markers to the map with popups and Google Calendar links."""
    for event in events:
        start_time = event.start_time.strftime("%Y-%m-%d %H:%M")
        end_time = event.end_time.strftime("%Y-%m-%d %H:%M")

        google_calendar_link = (
            "https://www.google.com/calendar/render?action=TEMPLATE"
            f"&text={urllib.parse.quote(event.title)}"
            f"&dates={event.start_time.strftime('%Y%m%dT%H%M%SZ')}/{event.end_time.strftime('%Y%m%dT%H%M%SZ')}"
            f"&details={urllib.parse.quote(event.event_description)}"
            f"&location={urllib.parse.quote(event.location)}"
        )

        popup_html = (
            f"<strong>{event.title}</strong><br>"
            f"{event.location} ({event.map_location})<br>"
            f"Start: {start_time}<br>"
            f"End: {end_time}<br>"
            f"<a href='{google_calendar_link}' target='_blank'>Add to Google Calendar</a>"
        )

        folium.Marker(
            location=[float(event.latitude), float(event.longitude)],
            popup=folium.Popup(popup_html, max_width=300),
            icon=folium.Icon(color="blue", icon="info-sign"),
        ).add_to(folium_map)

    return folium_map


def generate_heatmap(events, timezone, min_hour=None, max_hour=None):
    """Generate a heatmap map object based on filtered events within a time range."""
    if min_hour is not None and max_hour is not None:
        events = events.annotate(event_hour=ExtractHour("start_time")).filter(
            event_hour__gte=min_hour, event_hour__lte=max_hour
        )

    heatmap_data = [
        [float(event.latitude), float(event.longitude)]
        for event in events
        if event.latitude and event.longitude
    ]

    folium_map = folium.Map(
        location=[42.37284302722828, -72.51584816807264], zoom_start=17
    )
    if heatmap_data:
        HeatMap(heatmap_data).add_to(folium_map)

    return folium_map
