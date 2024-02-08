from __future__ import annotations

import hashlib
from typing import Literal

import music21

from tilia.timelines.base.component import TimelineComponent
from tilia.timelines.base.validators import validate_time, validate_string
from tilia.timelines.component_kinds import ComponentKind
from tilia.timelines.harmony.validators import (
    validate_step,
    validate_accidental,
    validate_quality,
    validate_inversion,
    validate_applied_to,
    validate_level,
    validate_display_mode,
    validate_custom_text_font_type,
)
from tilia.timelines.marker.timeline import MarkerTimeline
from tilia.ui.timelines.harmony.constants import NOTE_NAME_TO_INT, CHORD_COMMON_NAME_TO_TYPE


class Harmony(TimelineComponent):
    SERIALIZABLE_BY_VALUE = [
        "time",
        "comments",
        "step",
        "accidental",
        "quality",
        "inversion",
        "applied_to",
        "level",
        "display_mode",
        "custom_text",
        "custom_text_font_type",
    ]
    SERIALIZABLE_BY_ID = []
    SERIALIZABLE_BY_ID_LIST = []

    KIND = ComponentKind.HARMONY

    validators = {
        "timeline": lambda _: False,
        "id": lambda _: False,
        "time": validate_time,
        "step": validate_step,
        "accidental": validate_accidental,
        "quality": validate_quality,
        "inversion": validate_inversion,
        "applied_to": validate_applied_to,
        "level": validate_level,
        "display_mode": validate_display_mode,
        "custom_text": validate_string,
        "custom_text_font_type": validate_custom_text_font_type,
        "comments": validate_string,
    }

    def __init__(
        self,
        timeline: MarkerTimeline,
        id: int,
        time: float,
        step: int,
        accidental: int,
        quality: str,
        inversion: int | None = None,
        applied_to: int | None = None,
        level: int = 1,
        display_mode: Literal["chord", "roman", "custom"] = "chord",
        custom_text: str = "",
        custom_text_font_type: Literal["analytic", "normal"] = "analytic",
        comments="",
        **_,
    ):
        super().__init__(timeline, id)

        self.time = time
        self.step = step
        self.accidental = accidental
        self.quality = quality
        self.inversion = inversion
        self.applied_to = applied_to
        self.level = level
        self.display_mode = display_mode
        self.custom_text = custom_text
        self.custom_text_font_type = custom_text_font_type
        self.comments = comments

    def __lt__(self, other):
        return self.time < other.time

    def __str__(self):
        return f"Harmony({self.step, self.accidental, self.quality, self.inversion}) at {self.time}"

    def __repr__(self):
        return str(dict(self.__dict__.items()))

    @classmethod
    def create(cls, *args, **kwargs):
        return Harmony(*args, **kwargs)

    @classmethod
    def from_string(cls, time: float, string: str, key: music21.key.Key = music21.key.Key('C')):
        music21_object, object_type = _get_music21_object_from_text(
            string, key
        )

        if not string:
            return None

        if not object_type:
            raise ValueError("Can't create harmony: can't create music21 object from '{string}'")

        params = _get_params_from_music21_object(music21_object, object_type)
        return Harmony(*params)


def _get_music21_object_from_text(text, key):
    text, prefixed_accidental = _extract_prefixed_accidental(text)
    text = _format_postfix_accidental(text)
    if text.startswith(tuple(NOTE_NAME_TO_INT)) and not prefixed_accidental:
        try:
            return music21.harmony.ChordSymbol(text), "chord"
        except ValueError:
            pass
    elif text.startswith(("I", "i", "V", "v")):
        try:
            roman_numeral = music21.roman.RomanNumeral(
                prefixed_accidental + text, key
            )
            chord_common_name = music21.chord.Chord(
                roman_numeral.pitches
            ).commonName
            roman_numeral.chord_type = CHORD_COMMON_NAME_TO_TYPE[chord_common_name]
            return roman_numeral, "roman"
        except (ValueError, KeyError):
            pass

    return None, None


def _get_params_from_music21_object(obj, kind):
    step = obj.root().step
    accidental = int(obj.root().alter)
    inversion = obj.inversion()
    if kind == "roman":
        quality = obj.chord_type
        applied_to = (
            obj.secondaryRomanNumeral.figure.upper()
            if obj.secondaryRomanNumeral
            else None
        )
    else:
        quality = obj.chordKind
        applied_to = None

    return {
        "step": step,
        "accidental": accidental,
        "inversion": inversion,
        "quality": quality,
        "applied_to": applied_to,
    }


def _format_postfix_accidental(text):
    if len(text) > 1 and text[1] == "b":
        text = text[0] + "-" + text[2:]
        if len(text) > 2 and text[2] == "b":
            text = text[:2] + "-" + text[3:]
    return text


def _extract_prefixed_accidental(text):
    if not text:
        return "", ""

    accidental = ""

    while text and text[0] in ["-", "#", "b"]:
        accidental += text[0]
        text = text[1:]

    return text, accidental