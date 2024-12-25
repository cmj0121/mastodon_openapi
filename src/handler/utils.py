from loguru import logger


def canonicalize(text: str) -> str:
    text = text.strip()
    text = text.replace(":", "").replace(" ", "_").replace(".", "")

    if text in ("GroupedNotificationsResults", "PartialAccountWithAvatar", "NotificationGroup"):
        logger.warning(f"{text=} not support now")
        text = "JSON"

    return text
