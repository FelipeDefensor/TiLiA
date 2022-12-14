from typing import Protocol


def to_rgb(hex):
    hex = hex.lstrip("#")
    rgb = tuple(int(hex[i : i + 2], 16) for i in (0, 2, 4))
    return rgb


def rgb_to_hex(rgb):
    return "#%02x%02x%02x" % rgb


def hex_to_rgb(value):
    value = value.lstrip("#")
    lv = len(value)
    return tuple(int(value[i : i + lv // 3], 16) for i in range(0, lv, lv // 3))


def shade_rgb_color(rgb: tuple[int, int, int]) -> tuple[int, int, int]:
    """Returns shaded color as hex, takes an rgb tuple as argument"""

    shade_factor = 0.2
    return tuple(int(color * (1 - shade_factor)) for color in rgb)


def hex_to_shaded_hex(rgb):
    r, g, b = shade_rgb_color(hex_to_rgb(rgb))
    return f"#{r:02x}{g:02x}{b:02x}"


class HasColoredLevels(Protocol):
    color: str
    level: int

    @staticmethod
    def get_default_level_color(lvl) -> bool:
        ...


def has_custom_color(ui_element: HasColoredLevels) -> bool:
    """Return True if unit has custom color, False otherwise"""
    if ui_element.color == ui_element.get_default_level_color(ui_element.level):
        return False
    else:
        return True
