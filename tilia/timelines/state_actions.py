"""Enum for action names to be recorded by UndoRedoStack (to be implemented)."""

from enum import Enum, auto


class Action(Enum):
    TIMELINE_NAME_CHANGE = auto()
    TIMELINE_HEIGHT_CHANGE = auto()
    DELETE_TIMELINE_COMPONENT = auto()
    MARKER_DRAG = auto()
    BEAT_DRAG = auto()
    HIERARCHY_LEVEL_CHANGE = auto()
    CLEAR_ALL_TIMELINES = auto()
    TIMELINE_CLEAR = auto()
    CREATE_BEAT = auto()
    TIMELINE_CREATE = auto()
    TIMELINE_DELETE = auto()
    UNDO = auto()
    CREATE_MARKER = auto()
    ATTRIBUTE_EDIT_VIA_INSPECTOR = auto()
    COMPONENT_DELETE = auto()
    FILE_LOAD = auto()
    PASTE = auto()
    MERGE = auto()
    CLEAR_TIMELINE = auto()
    SPLIT = auto()
    GROUP = auto()
    CHANGE_LEVEL = auto()
    CREATE_UNIT_BELOW = auto()
    DELETE = auto()
