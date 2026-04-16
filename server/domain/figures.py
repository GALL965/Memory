from __future__ import annotations


def default_emoji_pool() -> list[str]:
    """Emoji pool used to build pairs for the board.

    The maximum board is 8x8 => 64 cards => 32 pairs.
    This pool provides >= 32 unique emojis.
    """

    return [
        "🍓",
        "🐶",
        "🍇",
        "🍒",
        "🍍",
        "🍉",
        "🍋",
        "🍑",
        "🥝",
        "🥥",
        "🍎",
        "🍊",
        "🍌",
        "🍐",
        "🫐",
        "🥭",
        "🐱",
        "🦊",
        "🐻",
        "🐼",
        "🐨",
        "🐯",
        "🦁",
        "🐮",
        "🐷",
        "🐸",
        "🐵",
        "🐔",
        "🐧",
        "🐙",
        "🦋",
        "🐝",
        "🐢",
        "🐳",
        "🦄",
        "🐞",
    ]
