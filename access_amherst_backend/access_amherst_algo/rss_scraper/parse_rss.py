import xml.etree.ElementTree as ET
import json
from datetime import datetime
from access_amherst_algo.models import Event  # Import the Event model
from bs4 import BeautifulSoup
import random
import re
import os
from dotenv import load_dotenv
from django.utils import timezone
from django.db.models import Q
import difflib

load_dotenv()

# Define location buckets with keywords as keys and dictionaries containing full names, latitude, and longitude as values
location_buckets = {
    "Keefe": {
        "name": "Keefe Campus Center",
        "latitude": 42.37141504481807,
        "longitude": -72.51479991450528,
    },
    "Queer": {
        "name": "Keefe Campus Center",
        "latitude": 42.37141504481807,
        "longitude": -72.51479991450528,
    },
    "Multicultural": {
        "name": "Keefe Campus Center",
        "latitude": 42.37141504481807,
        "longitude": -72.51479991450528,
    },
    "Friedmann": {
        "name": "Keefe Campus Center",
        "latitude": 42.37141504481807,
        "longitude": -72.51479991450528,
    },
    "Ford": {
        "name": "Ford Hall",
        "latitude": 42.36923506234738,
        "longitude": -72.51529130962976,
    },
    "SCCE": {
        "name": "Science Center",
        "latitude": 42.37105378715133,
        "longitude": -72.51334790776447,
    },
    "Science Center": {
        "name": "Science Center",
        "latitude": 42.37105378715133,
        "longitude": -72.51334790776447,
    },
    "Chapin": {
        "name": "Chapin Hall",
        "latitude": 42.371771820543486,
        "longitude": -72.51572746604714,
    },
    "Gym": {
        "name": "Alumni Gymnasium",
        "latitude": 42.368819594097864,
        "longitude": -72.5188658145099,
    },
    "Cage": {
        "name": "Alumni Gymnasium",
        "latitude": 42.368819594097864,
        "longitude": -72.5188658145099,
    },
    "Lefrak": {
        "name": "Alumni Gymnasium",
        "latitude": 42.368819594097864,
        "longitude": -72.5188658145099,
    },
    "Middleton Gym": {
        "name": "Alumni Gym",
        "latitude": 42.368819594097864,
        "longitude": -72.5188658145099,
    },
    "Frost": {
        "name": "Frost Library",
        "latitude": 42.37183195277655,
        "longitude": -72.51699336789369,
    },
    "Paino": {
        "name": "Beneski Museum of Natural History",
        "latitude": 42.37209277500926,
        "longitude": -72.51422459549485,
    },
    "Powerhouse": {
        "name": "Powerhouse",
        "latitude": 42.372109655195466,
        "longitude": -72.51309270030836,
    },
    "Converse": {
        "name": "Converse Hall",
        "latitude": 42.37243680844771,
        "longitude": -72.518433147017,
    },
    "Assembly Room": {
        "name": "Converse Hall",
        "latitude": 42.37243680844771,
        "longitude": -72.518433147017,
    },
    "Red Room": {
        "name": "Converse Hall",
        "latitude": 42.37243680844771,
        "longitude": -72.518433147017,
    },
}


# Update categorize_location to use new dictionary structure
def categorize_location(location):
    """
    Categorize a location based on keywords in the `location_buckets` dictionary.

    This function searches the `location` string for any keyword defined in the
    `location_buckets` dictionary. If a keyword is found, it returns the associated 
    category name from the dictionary. If no keyword is matched, it returns "Other" 
    as the default category.

    Args:
        location (str): The location description to categorize.

    Returns:
        str: The category name if a keyword is matched, otherwise "Other".

    Example:
        >>> categorize_location("Friedmann Room")
        'Keefe Campus Center'
    """
    for keyword, info in location_buckets.items():
        if re.search(rf"\b{keyword}\b", location, re.IGNORECASE):
            return info["name"]
    return "Other"  # Default category if no match is found


# Function to extract the details of an event from an XML item
def extract_event_details(item):
    """
    Extract relevant event details from an XML item element.

    This function takes an XML item element and parses various fields such as
    title, link, description, categories, and other event metadata.
    It also handles optional fields like images and author.

    Args:
        item (xml.etree.ElementTree.Element): The XML item element containing event details.

    Returns:
        dict: A dictionary containing event details with the following keys:
            - `title` (str): The event title.
            - `author` (str or None): The event author, if available.
            - `pub_date` (str): Publication date of the event.
            - `host` (list of str): A list of host names associated with the event.
            - `link` (str): URL link to the event.
            - `picture_link` (str or None): URL to the event image, if available.
            - `event_description` (str): Parsed HTML content of the event description.
            - `starttime` (str): Event start time.
            - `endtime` (str): Event end time.
            - `location` (str): The event location as specified in the XML.
            - `categories` (list of str): Categories or tags associated with the event.
            - `map_location` (str): Categorized location name for mapping purposes.
    
    Example:
        >>> event_data = extract_event_details(xml_item)
        >>> print(event_data['title'])
        'Literature Speaker Event'
    """
    ns = "{events}"

    # Extract primary fields from XML
    title = item.find("title").text
    link = item.find("link").text

    # Get image link if available
    enclosure = item.find("enclosure")
    picture_link = enclosure.attrib["url"] if enclosure is not None else None

    # Parse event description HTML if available
    description = item.find("description").text
    event_description = ""
    if description:
        soup = BeautifulSoup(description, "html.parser")
        description_div = soup.find("div", class_="p-description description")
        event_description = "".join(
            str(content) for content in description_div.contents
        )

    # Gather categories and other event metadata
    categories = [category.text for category in item.findall('category')]
    pub_date = item.find('pubDate').text
    start_time = item.find(ns + 'start').text
    end_time = item.find(ns + 'end').text
    location = item.find(ns + 'location').text
    author = item.find('author').text if item.find('author') is not None else None
    host = [host.text for host in item.findall(ns + 'host')]

    # Categorize the location for mapping purposes
    map_location = categorize_location(location)

    return {
        "title": title,
        "author": author,
        "pub_date": pub_date,
        "host": host,
        "link": link,
        "picture_link": picture_link,
        "event_description": event_description,
        "starttime": start_time,
        "endtime": end_time,
        "location": location,
        "categories": categories,
        "map_location": map_location,
    }


# Use hardcoded lat/lng for each location bucket
def get_lat_lng(location):
    """
    Retrieve the latitude and longitude for a given location.

    This function searches the `location` string for any keyword defined in the
    `location_buckets` dictionary. If a keyword is found, it returns the associated 
    category name from the dictionary. If no keyword is matched, it returns "Other" 
    as the default category. If a keyword is found, it returns the corresponding
    latitude and longitude. If no keyword is matched, it returns `(None, None)`.

    Args:
        location (str): The location description to search for latitude and longitude.

    Returns:
        tuple: A tuple containing:
            - `latitude` (float or None): The latitude of the location if a match is found, otherwise None.
            - `longitude` (float or None): The longitude of the location if a match is found, otherwise None.

    Example:
        >>> get_lat_lng("Friedmann Room")
        (42.37141504481807, -72.51479991450528)
    """
    for keyword, info in location_buckets.items():
        if re.search(rf"\b{keyword}\b", location, re.IGNORECASE):
            return info["latitude"], info["longitude"]
    return None, None


# Function to add a slight random offset to latitude and longitude
def add_random_offset(lat, lng):
    """
    Add a small random offset to latitude and longitude coordinates.

    This function applies a random offset within a small range to both the latitude
    and longitude values provided. The offset range can be adjusted as needed based
    on the map scale to create minor variations in coordinates, which is useful for
    visual distinction on maps.

    Args:
        lat (float): The original latitude coordinate.
        lng (float): The original longitude coordinate.

    Returns:
        tuple: A tuple containing:
            - `lat` (float): The latitude with a random offset applied.
            - `lng` (float): The longitude with a random offset applied.

    Example:
        >>> add_random_offset(42.37141504481807, -72.51479991450528)
        (42.37149564586236, -72.51478632450079)  # Results may vary due to randomness
    """
    # Define a small range for random offsets (in degrees)
    offset_range = 0.00015  # Adjust this value as needed for your map scale
    lat += random.uniform(-offset_range, offset_range)
    lng += random.uniform(-offset_range, offset_range)
    return lat, lng


# Function to save the event to the Django model
def save_event_to_db(event_data):
    """
    Save event data to the Django model.

    This function processes event data for database storage by parsing publication,
    start, and end dates into timezone-aware datetime objects, extracting and
    adjusting location data, and generating a unique event ID. Finally, the function
    updates or creates an entry in the database's `Event` table.

    Args:
        event_data (dict): A dictionary containing event details, expected to include:
            - `title` (str): Title of the event.
            - `author` (str or None): The event author if available.
            - `pub_date` (str): The publication date in RFC 2822 format.
            - `host` (list of str): Hosts associated with the event.
            - `link` (str): Unique URL link to the event.
            - `picture_link` (str or None): URL to the event’s image, if available.
            - `event_description` (str): Description or details about the event.
            - `starttime` (str): Event start time in either ISO or RFC 2822 format.
            - `endtime` (str): Event end time in either ISO or RFC 2822 format.
            - `location` (str): Raw location string of the event.
            - `categories` (list of str): Categories or tags associated with the event.
    
    Returns:
        None

    Example:
        >>> event_data = {
        ...     "title": "Literature Speaker Event",
        ...     "link": "https://thehub.amherst.edu/event/10000000",
        ...     "event_description": "Join us to hear our speaker's talk on American Literature! Food from a local restaurant will be provided.",
        ...     "categories": ["Lecture", "Workshop"],
        ...     "pub_date": "Sun, 03 Nov 2024 05:30:25 GMT",
        ...     "starttime": "Tue, 05 Nov 2024 18:00:00 GMT",
        ...     "endtime": "Tue, 05 Nov 2024 19:00:00 GMT",
        ...     "location": "Friedmann Room",
        ...     "author": "literature@amherst.edu",
        ...     "host": "Literature Club",
        ... }
        >>> save_event_to_db(event_data)
    """
    pub_date_format = "%a, %d %b %Y %H:%M:%S %Z"
    pub_date = timezone.make_aware(
        datetime.strptime(event_data["pub_date"], pub_date_format)
    )

    # Parse start and end times with multiple format handling
    try:
        iso_format = "%Y-%m-%dT%H:%M:%S"
        start_time = datetime.strptime(event_data["starttime"], iso_format)
        end_time = datetime.strptime(event_data["endtime"], iso_format)
    except ValueError:
        rfc_format = "%a, %d %b %Y %H:%M:%S %Z"
        start_time = datetime.strptime(event_data["starttime"], rfc_format)
        end_time = datetime.strptime(event_data["endtime"], rfc_format)

    start_time, end_time = timezone.make_aware(
        start_time
    ), timezone.make_aware(end_time)

    # get map location
    event_data["map_location"] = categorize_location(event_data["location"])

    # Geocode to get latitude and longitude using hardcoded values
    lat, lng = get_lat_lng(event_data["map_location"])

    # Add random offset to coordinates if lat/lng are available
    if lat is not None and lng is not None:
        lat, lng = add_random_offset(lat, lng)

    # Save or update event in the database
    Event.objects.update_or_create(
        id=str(event_data['id']),
        defaults={
            "id": event_data['id'],
            "title": event_data['title'],
            "author_name": event_data['author_name'],
            "author_email": event_data['author_email'],
            "pub_date": pub_date,
            "host": json.dumps(event_data["host"]),
            "link": event_data["link"],
            "picture_link": event_data["picture_link"],
            "event_description": event_data["event_description"],
            "start_time": start_time,
            "end_time": end_time,
            "location": event_data["location"],
            "categories": json.dumps(event_data["categories"]),
            "latitude": lat if lat is not None else None,
            "longitude": lng if lng is not None else None,
            "map_location": event_data["map_location"],
        },
    )


# Function to create a list of events from an RSS XML file
def create_events_list():
    """
    Create a list of event details from an RSS XML file.

    This function loads an RSS XML file with a timestamped filename format,
    parses its content, and extracts event details from each `<item>` element.
    The event details are returned as a list of dictionaries, with each dictionary
    containing relevant information for a single event.

    Returns:
        list of dict: A list where each dictionary represents an event and contains
        extracted details retrieved by `extract_event_details`.

    Example:
        >>> events = create_events_list()
        >>> print(events[0]["title"])
        'Literature Speaker Event'
    """
    rss_file_name = (
        "access_amherst_algo/rss_scraper/rss_files/hub_"
        + datetime.now().strftime("%Y_%m_%d_%H")
        + ".xml"
    )
    root = ET.parse(rss_file_name).getroot()

    events_list = [
        extract_event_details(item) for item in root.findall(".//item")
    ]
    return events_list


# Function to save extracted events to a JSON file
def save_json():
    """
    Save the list of extracted events to a JSON file.

    This function generates a timestamped JSON file containing event details.
    It first creates a list of events by calling `create_events_list()`, and 
    then writes this list to a JSON file with a filename format based on the 
    current date and time.

    The resulting JSON file is saved in the `json_outputs` directory under the
    `rss_scraper` folder. If the directory doesn't exist, it is created.

    Returns:
        None

    Example:
        >>> save_json()
        # This will create a JSON file with the event details in the specified directory.
    """
    # Generate the events list
    events_list = create_events_list()

    # Define the directory and output file name
    directory = "access_amherst_algo/rss_scraper/json_outputs"
    os.makedirs(directory, exist_ok=True)  # Create the directory if it doesn't exist
    output_file_name = os.path.join(
        directory, "hub_" + datetime.now().strftime("%Y_%m_%d_%H") + ".json"
    )

    # Save the events list to a JSON file
    with open(output_file_name, "w") as f:
        json.dump(events_list, f, indent=4)

# detect if an event already exists in database
def is_similar_event(event_data):
    try:
        # Attempt to parse start and end times in ISO format first
        iso_format = '%Y-%m-%dT%H:%M:%S'
        start_time = timezone.make_aware(datetime.strptime(event_data['starttime'], iso_format))
        end_time = timezone.make_aware(datetime.strptime(event_data['endtime'], iso_format))
    except ValueError:
        # If ISO format fails, fall back to RFC format
        rfc_format = '%a, %d %b %Y %H:%M:%S %Z'
        start_time = timezone.make_aware(datetime.strptime(event_data['starttime'], rfc_format))
        end_time = timezone.make_aware(datetime.strptime(event_data['endtime'], rfc_format))

    # Filter for events with matching start and end times
    similar_events = Event.objects.filter(
        Q(start_time=start_time) & Q(end_time=end_time)
    )
    
    # Check title similarity with filtered events
    for event in similar_events:
        title_similarity = difflib.SequenceMatcher(None, event_data['title'], event.title).ratio()
        if title_similarity > 0.8:  # Adjust threshold for desired strictness
            return True
    
    return False

# Function to clean and save events to the database
def save_to_db():
    """
    Clean and save event data to the database.

    This function first retrieves a cleaned list of events by calling the 
    `clean_hub_data()` function. It then iterates through each event in the 
    list and saves the event data to the database using the `save_event_to_db()` 
    function.

    This process ensures that only cleaned event data is stored in the database.

    Returns:
        None

    Example:
        >>> save_to_db()
        # This will save the cleaned event data to the database.
    """
    from access_amherst_algo.rss_scraper.clean_hub_data import clean_hub_data
    
    events_list = clean_hub_data()  # Get the cleaned list of events to be saved

    for event in events_list:
        # Check if a similar event already exists. Cases:
        # (if hub event, collision detection handled by update_or_create so always call save_event_to_db)
        # (if not hub event, and not similar to something in DB, then only call save_event_to_db)
        if int(event['id']) > 500_000_000 or not is_similar_event(event):
            # If no similar event is found, save the event
            save_event_to_db(event)



if __name__ == "__main__":
    save_json()
    save_to_db()
