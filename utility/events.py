import json
import re
from functools import lru_cache

from logging_utility import logger

@lru_cache(maxsize=30720)
def get_events() -> list | None:
    with open("data/events.json", "r", encoding="utf-8") as file:
        events: list = json.load(file)
    return events


def query_events(query: str = None, day: int = None, month: int = None, year: int = None) -> list | None:
    events: list[dict] | None = get_events()
    
    if query is not None:
        if query.strip == "":
            query = ".*"
        pattern = re.compile(query, re.IGNORECASE)
        events = [
            event for event in events 
            if (pattern.search(event.get("name", "")) or pattern.search(event.get("description", "")))
        ]

    if day is not None:
        events = [
            event for event in events if (day == event.get("day"))
        ]
    
    if month is not None:
        events = [
            event for event in events if (month == event.get("month"))
        ]

    if year is not None:
        events = [
            event for event in events if (year == event.get("year"))
        ]


    return events if events else []

@lru_cache(maxsize=30720)
def get_event_by_id(_id: str) -> dict | None:
    events: list[dict] | None = get_events()
    result = [event for event in events if (str(_id) == (event.get("id")))]
    event = result[0] if result else None
    return event


def delete_event_json(event_id: str):
    events: list[dict] = get_events()
    
    events_new = [event for event in events if event.get("id") != str(event_id)]

    with open("data/events.json", "w", encoding="utf-8") as f:
        json.dump(events_new, f, indent=4, ensure_ascii=False)    
    
    get_event_by_id.cache_clear()
    get_events.cache_clear()

def add_event(event_data: dict):
    try:
        events: list[dict] = get_events()
        events.append(event_data)

        with open("data/events.json", "w", encoding="utf-8") as f:
            json.dump(events, f, indent=4, ensure_ascii=False)
        
        logger.info(f"Event added successfully | Event ID: {event_data.get('id')}")
        
        # Clear cached data for events
        get_event_by_id.cache_clear()
        get_events.cache_clear()
    except FileNotFoundError:
        logger.critical("events.json file not found.")
    except json.JSONDecodeError:
        logger.critical("Invalid JSON in events.json.")
    except Exception as e:
        logger.error(f"Error adding event: {e}")