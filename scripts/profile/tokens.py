"""Colour and motion tokens; no remote styling or font dependencies."""

THEMES = {
    "dark": {
        "bg": "#0D111C", "surface": "#151C2E", "surface-2": "#172043",
        "border": "#2B3650", "text": "#F1F5FF", "text-muted": "#A5B2CC",
        "violet": "#B2A0FF", "cyan": "#68E1F4", "warm": "#FFC780",
        "github": "#0D1117",
    },
    "light": {
        "bg": "#F6F8FF", "surface": "#FFFFFF", "surface-2": "#EEF0FA",
        "border": "#D6DDEF", "text": "#18233E", "text-muted": "#53637E",
        "violet": "#7051C1", "cyan": "#08788E", "warm": "#966016",
        "github": "#FFFFFF",
    },
}

MOTION = {"reveal_ms": 900, "stagger_ms": 30, "max_stagger_ms": 800,
          "ambient_s": 24, "easing": "cubic-bezier(0.22, 1, 0.36, 1)"}
HEAT_BINS = ((0, "0"), (2, "1–2"), (5, "3–5"), (10, "6–10"),
             (50, "11–50"), (float("inf"), "51+"))
HEAT_COLORS = {
    "dark": ("#172043", "#454169", "#635388", "#8370B8", "#B2A0FF", "#DED6FF"),
    "light": ("#EEF0FA", "#DED6F3", "#BDA9E5", "#987CCC", "#7051C1", "#46288D"),
}
# Every token used for text is tested on every surface where it appears.
TEXT_TOKENS = ("text", "text-muted", "violet", "cyan", "warm")
TEXT_BACKGROUNDS = ("bg", "surface", "surface-2")
GRAPHIC_TOKENS = ("violet", "cyan", "warm", "text-muted")


def luminance(hex_color):
    values = [int(hex_color[i:i+2], 16) / 255 for i in (1, 3, 5)]
    linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in values]
    return sum(v * weight for v, weight in zip(linear, (.2126, .7152, .0722)))


def contrast(a, b):
    hi, lo = sorted((luminance(a), luminance(b)), reverse=True)
    return (hi + .05) / (lo + .05)

