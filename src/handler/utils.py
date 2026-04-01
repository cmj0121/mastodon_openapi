import requests
from bs4 import BeautifulSoup
from loguru import logger

from src.openapi_spec import MediaTypeObject


def canonicalize(text: str) -> str:
    text = text.strip()
    text = text.replace(":", "").replace(" ", "_").replace(".", "")

    if text in ("GroupedNotificationsResults", "PartialAccountWithAvatar", "NotificationGroup"):
        logger.warning(f"{text=} not support now")
        text = "JSON"

    return text


def fetch_soup(link: str) -> BeautifulSoup:
    response = requests.get(link)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser")


def make_media_type(schema) -> MediaTypeObject:
    return MediaTypeObject.model_validate({"schema": schema})


def handle_type_str(text: str, item: str | None = None) -> tuple[str, str | None]:
    if text == "Array of":
        return "array", item
    if text == "Array of Strings":
        return "array", "String"
    elif text.startswith("String"):
        return "String", None
    elif text.startswith("Integer"):
        return "Integer", None
    elif text.startswith("Number"):
        return "Number", None
    elif text.startswith("Array of"):
        items = text.split()[2]
        return "array", handle_type_str(items)[0]

    return text, item
