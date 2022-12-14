import pytest

from unittest.mock import MagicMock, patch
import tkinter as tk

from tilia import globals_, events
from tilia.events import Event, unsubscribe_from_all
from tilia.timelines.timeline_kinds import TimelineKind
from tilia.ui.timelines.collection import TimelineUICollection
from tilia.ui.timelines.hierarchy import HierarchyTimelineUI
from tilia.ui.timelines.marker import MarkerTimelineUI
from tilia.ui.timelines.slider import SliderTimelineUI
from tilia.ui.tkinterui import TkinterUI


@pytest.fixture
def tkui_mock():
    _tkui_mock = MagicMock(TkinterUI)
    _tkui_mock.timeline_padx = globals_.DEFAULT_TIMELINE_PADX
    _tkui_mock.timeline_width = globals_.DEFAULT_TIMELINE_WIDTH
    _tkui_mock.timeline_total_size = (
        globals_.DEFAULT_TIMELINE_PADX + globals_.DEFAULT_TIMELINE_WIDTH
    )

    return _tkui_mock


@pytest.fixture
def tlui_coll(tkui_mock):
    _tlui_coll = TimelineUICollection(tkui_mock, tk.Frame(), tk.Scrollbar(), tk.Frame())
    yield _tlui_coll
    unsubscribe_from_all(_tlui_coll)


@patch("tilia.ui.timelines.collection.TimelineUICollection.create_playback_line")
class TestTkTimelineUICollection:
    def test_constructor(self, tkui_mock):
        tlui_coll = TimelineUICollection(
            tkui_mock, tk.Frame(), tk.Scrollbar(), tk.Frame()
        )

        assert tlui_coll._app_ui == tkui_mock

        unsubscribe_from_all(tlui_coll)

    @patch("tilia.ui.timelines.collection.TimelineUICollection.get_tlcanvas_width")
    def test_create_timeline_ui_hierarchy_timeline(self, get_width_mock, _, tlui_coll):

        get_width_mock.return_value = 1

        tlui_coll.get_toolbar_for_timeline_ui = lambda _: MagicMock()

        tlui = tlui_coll.create_timeline_ui(TimelineKind.HIERARCHY_TIMELINE, "test")

        assert tlui.__class__ == HierarchyTimelineUI
        assert tlui in tlui_coll._timeline_uis
        assert tlui_coll._select_order[0] == tlui

    @patch("tilia.ui.timelines.collection.TimelineUICollection.get_tlcanvas_width")
    def test_create_timeline_ui_slider_timeline(self, get_width_mock, _, tlui_coll):
        get_width_mock.return_value = 1

        tlui = tlui_coll.create_timeline_ui(TimelineKind.SLIDER_TIMELINE, "test")

        assert tlui.__class__ == SliderTimelineUI
        assert tlui in tlui_coll._timeline_uis
        assert tlui_coll._select_order[0] == tlui

    @patch("tilia.ui.timelines.collection.TimelineUICollection.get_tlcanvas_width")
    def test_create_two_timeline_uis(self, get_width_mock, _, tlui_coll):
        get_width_mock.return_value = 1

        tlui_coll.get_toolbar_for_timeline_ui = lambda _: MagicMock()

        tlui1 = tlui_coll.create_timeline_ui(TimelineKind.HIERARCHY_TIMELINE, "test")
        tlui2 = tlui_coll.create_timeline_ui(TimelineKind.HIERARCHY_TIMELINE, "test")

        assert tlui1 in tlui_coll._timeline_uis
        assert tlui2 in tlui_coll._timeline_uis
        assert tlui_coll._select_order[0] == tlui2

    @patch("tilia.ui.timelines.collection.TimelineUICollection.get_tlcanvas_width")
    def test_delete_timeline_ui(self, get_width_mock, _, tlui_coll):
        get_width_mock.return_value = 1

        tlui_coll.get_toolbar_for_timeline_ui = lambda _: MagicMock()
        tlui_coll._delete_timeline_ui_toolbar_if_necessary = lambda _: None

        tlui = tlui_coll.create_timeline_ui(TimelineKind.HIERARCHY_TIMELINE, "test")

        tlui_coll.delete_timeline_ui(tlui)

        assert not tlui_coll._timeline_uis
        assert not tlui_coll._select_order
        assert not tlui_coll._display_order

    @patch("tilia.ui.timelines.collection.TimelineUICollection.get_tlcanvas_width")
    def test_update_select_order(self, get_width_mock, _, tlui_coll):
        get_width_mock.return_value = 1

        tlui_coll.get_toolbar_for_timeline_ui = lambda _: MagicMock()

        tlui1 = tlui_coll.create_timeline_ui(TimelineKind.HIERARCHY_TIMELINE, "test")
        tlui2 = tlui_coll.create_timeline_ui(TimelineKind.HIERARCHY_TIMELINE, "test")

        assert tlui_coll._select_order[0] == tlui2

        events.post(Event.CANVAS_LEFT_CLICK, tlui1.canvas, 0, 0, 0, None, double=False)

        assert tlui_coll._select_order[0] == tlui1

        events.post(Event.CANVAS_LEFT_CLICK, tlui2.canvas, 0, 0, 0, None, double=False)

        assert tlui_coll._select_order[0] == tlui2
