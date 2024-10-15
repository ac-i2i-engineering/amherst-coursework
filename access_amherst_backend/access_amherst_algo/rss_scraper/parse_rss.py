import xml.etree.ElementTree as ET
import json
from datetime import datetime
from access_amherst_algo.models import Event  # Import the Event model

# Function to extract the details of an event from an XML item
def extract_event_details(item):
    ns = '{events}'

    title = item.find('title').text
    link = item.find('link').text

    enclosure = item.find('enclosure')
    picture_link = enclosure.attrib['url'] if enclosure is not None else None
    
    description = item.find('description').text
    if description:
        description_start = description.find('<div class="p-description description">') + len('<div class="p-description description">')
        description_end = description.find('</div>', description_start)
        event_description = description[description_start:description_end]
    
    categories = [category.text for category in item.findall('category')]

    pub_date = item.find('pubDate').text
    start_time = item.find(ns + 'start').text
    end_time = item.find(ns + 'end').text
    location = item.find(ns + 'location').text
    
    author = item.find('author')
    author = author.text if author is not None else None

    host = [host.text for host in item.findall(ns + 'host')]
    
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
    }

from datetime import datetime

# Function to save the event to the Django model
def save_event_to_db(event_data):
    # Handle the `pub_date` parsing (example format: Tue, 15 Oct 2024 19:30:00 GMT)
    format = '%a, %d %b %Y %H:%M:%S %Z'
    pub_date = datetime.strptime(event_data['pub_date'], format)

    # Handle the `start_time` and `end_time` parsing (ISO 8601 format: 2024-10-15T19:30:00)
    start_time = datetime.strptime(event_data['starttime'], format)
    end_time = datetime.strptime(event_data['endtime'], format)

    # Save the event to the database
    Event.objects.create(
        title=event_data['title'],
        author=event_data['author'],
        pub_date=pub_date,
        host=json.dumps(event_data['host']),
        link=event_data['link'],
        picture_link=event_data['picture_link'],
        event_description=event_data['event_description'],
        start_time=start_time,
        end_time=end_time,
        location=event_data['location'],
        categories=json.dumps(event_data['categories']),
    )


def parse_rss():
    rss_file_name = 'access_amherst_algo/rss_scraper/rss_files/hub_' + datetime.now().strftime('%Y_%m_%d_%H') + '.xml'
    root = ET.parse(rss_file_name).getroot()

    events_list = []

    # Loop through each event item and extract details
    for item in root.findall('.//item'):
        event_details = extract_event_details(item)
        events_list.append(event_details)
        save_event_to_db(event_details)  # Save event to the database

    # Save the extracted data to a JSON file as well
    output_file_name = 'access_amherst_algo/rss_scraper/json_outputs/hub_' + datetime.now().strftime('%Y_%m_%d_%H') + '.json'
    with open(output_file_name, 'w') as f:
        json.dump(events_list, f, indent=4)

if __name__ == '__main__':
    parse_rss()