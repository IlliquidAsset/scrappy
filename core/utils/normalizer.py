NORMALIZATION_MAP = {
    "ln": "Lane",
    "lane": "Lane",
    "dr": "Drive",
    "drive": "Drive",
    "rd": "Road",
    "road": "Road",
    "st": "Street",
    "street": "Street",
    "blvd": "Boulevard",
    "boulevard": "Boulevard",
    "ave": "Avenue",
    "avenue": "Avenue",
    "ct": "Court",
    "court": "Court",
}

def normalize_text(text):
    if not text:
        return ""
    words = text.lower().split()
    normalized_words = [NORMALIZATION_MAP.get(word, word) for word in words]
    return " ".join(normalized_words).title()
