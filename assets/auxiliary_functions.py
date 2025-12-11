# This file contains helper functions for app.py
import re


def remove_emojis(text):
    # Emoji pattern covering most emojis
    emoji_pattern = re.compile(
        "["                     # emoji base ranges
        "\U0001F600-\U0001F64F"
        "\U0001F300-\U0001F5FF"
        "\U0001F680-\U0001F6FF"
        "\U0001F700-\U0001F77F"
        "\U0001F780-\U0001F7FF"
        "\U0001F800-\U0001F8FF"
        "\U0001F900-\U0001F9FF"
        "\U0001FA00-\U0001FA6F"
        "\U0001FA70-\U0001FAFF"
        "\U00002600-\U000026FF"
        "\U00002700-\U000027BF"
        "\U000024C2-\U0001F251"
        "*#]+"
        r"(?:[\u200d\ufe0f\U0001F3FB-\U0001F3FF])*",  # ZWJ, VS16, skin tones, etc.
        flags=re.UNICODE,
    )
    # Substitute matched emojis with an empty string
    return emoji_pattern.sub(r'', text)