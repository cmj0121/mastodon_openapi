def canonicalize(text: str) -> str:
    text = text.strip()
    return text.replace(":", "").replace(" ", "_").replace(".", "")
