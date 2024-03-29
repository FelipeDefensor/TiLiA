from tilia.ui.actions import TiliaAction
from tilia.ui.menus import MenuItemKind
from tilia.ui.timelines.base.context_menus import TimelineUIElementContextMenu


class BeatContextMenu(TimelineUIElementContextMenu):
    name = "Marker"
    items = [
        (MenuItemKind.ACTION, TiliaAction.TIMELINE_ELEMENT_INSPECT),
        (MenuItemKind.SEPARATOR, None),
        (MenuItemKind.ACTION, TiliaAction.BEAT_SET_MEASURE_NUMBER),
        (MenuItemKind.ACTION, TiliaAction.BEAT_RESET_MEASURE_NUMBER),
        (MenuItemKind.ACTION, TiliaAction.BEAT_DISTRIBUTE),
        (MenuItemKind.ACTION, TiliaAction.BEAT_SET_AMOUNT_IN_MEASURE),
        (MenuItemKind.SEPARATOR, None),
        (MenuItemKind.ACTION, TiliaAction.TIMELINE_ELEMENT_COPY),
        (MenuItemKind.ACTION, TiliaAction.TIMELINE_ELEMENT_PASTE),
        (MenuItemKind.SEPARATOR, None),
        (MenuItemKind.ACTION, TiliaAction.TIMELINE_ELEMENT_DELETE),
    ]
