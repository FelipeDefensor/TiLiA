"""Enum for action names to be recorded by UndoRedoStack (to be implemented)."""

from enum import Enum


class StateAction(Enum):
    ATTRIBUTE_EDIT_VIA_INSPECTOR = 'ATTRIBUTE EDIT VIA INSPECT'
    COMPONENT_DELETE = "COMPONENT DELETE"
    FILE_LOAD = "FILE LOAD"
    DUMMY_ACTION1 = "DUMMY"
    DUMMY_ACTION2 = "DUMMY"
    PASTE = "PASTE"
    MERGE = "MERGE"
    CLEAR_TIMELINE = "CLEAR COMPONENT MANAGER"
    SPLIT = "SPLIT"
    GROUP = "GROUP"
    CHANGE_LEVEL = "CHANGE LEVEL"
    CREATE_UNIT_BELOW = "CREATE UNIT BELOW"
    DELETE = "DELETE"
