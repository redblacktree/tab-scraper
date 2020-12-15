import requests
from logzero import logger
import operator
from copy import deepcopy

COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:80.0) Gecko/20100101 Firefox/80.0",
    "Accept": "application/json",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip",
    "Content-Type": "application/json",
    "X-Accept-Language": "en-NZ",
    "X-OB-Channel": "I",
    "Origin": "https://www.tab.co.nz",
    "Connection": "keep-alive"
}

RACE_TYPES = {
    "HORSE_RACING": "Thoroughbred",
    "HARNESS_RACING": "Harness",
    "GREYHOUNDS": "Greyhound"
}


def get_cloudfare_cookie():
    """ Cloudfare uses cookies to identify users. Get a new cookie for each run of the script
    to emulate human behavior. """
    resp = requests.get("https://www.tab.co.nz/")
    return resp.cookies["__cfduid"]


def map_data(source_data, mapping):
    def find(element, json):
        keys = element.split('.')
        value = json
        for key in keys:
            if isinstance(value, dict):
                if value is not None and key in value:
                    value = value[key]
                else:
                    return None
            elif isinstance(value, list):
                try:
                    index = int(key)
                except ValueError:
                    logger.warning(f"Attempted to retrieve non-integer key {key} from list")
                    logger.debug(f"value: {value}")
                    return None
                if len(value) >= index:
                    value = value[index]
                else:
                    logger.warning("Attempted to retrieve non-existent index")
                    logger.debug(f"value: {value}")
                    return None
        return value
    dest_data = deepcopy(mapping)
    for key in dest_data:
        dest_data[key] = find(mapping[key], source_data)
    return dest_data


def format_data(data, format_rules):
    for key, rule in format_rules.items():
        if key in data:
            data[key] = rule(data[key])
    return data