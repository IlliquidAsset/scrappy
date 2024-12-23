def normalize_text(text):
    text = text.lower()
    mapping = {'ln': 'lane', 'dr': 'drive', 'st': 'street'}
    return ' '.join(mapping.get(word, word) for word in text.split())

def validate_input(input_names):
    return [name.strip() for name in input_names if name.strip()]
