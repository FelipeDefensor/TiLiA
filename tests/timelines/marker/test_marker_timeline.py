import logging

from tilia.timelines.marker.timeline import (
    MarkerTimeline,
)
from tilia.timelines.serialize import serialize_component, _deserialize_component
from tilia.timelines.timeline_kinds import TimelineKind

logger = logging.getLogger(__name__)


class TestMarkerTimeline:
    # TEST CREATE
    def test_create_marker(self, marker_tl):
        marker_tl.create_marker(0)

        assert len(marker_tl) == 1

    # TEST UNDO
    def test_restore_state(self, marker_tl):
        marker_tl.create_marker(0)
        marker_tl.create_marker(1)

        state = marker_tl.get_state()

        marker_tl.clear()

        assert len(marker_tl) == 0

        marker_tl.restore_state(state)

        assert len(marker_tl) == 2

    # TEST RIGHT CLICK OPTIONS


class TestMarkerTimelineComponentManager:
    # TEST CLEAR
    def test_clear(self, marker_tl):
        marker_tl.create_marker(0)
        marker_tl.create_marker(0)
        marker_tl.create_marker(0)

        marker_tl.component_manager.clear()

        assert not marker_tl.component_manager._components

    # TEST SERIALIZE
    # noinspection PyUnresolvedReferences
    def test_serialize_components(self, marker_tl):
        mrk1, _ = marker_tl.create_marker(0)
        mrk2, _ = marker_tl.create_marker(1)
        mrk3, _ = marker_tl.create_marker(2)

        serialized_components = marker_tl.component_manager.serialize_components()

        for unit in [mrk1, mrk2, mrk3]:
            assert serialized_components[unit.id]["time"] == unit.time

    # noinspection PyUnresolvedReferences
    def test_deserialize_components(self, marker_tl):
        mrk1, _ = marker_tl.create_marker(0)
        mrk2, _ = marker_tl.create_marker(1)
        mrk3, _ = marker_tl.create_marker(2)

        serialized_components = marker_tl.component_manager.serialize_components()

        marker_tl.component_manager.clear()

        marker_tl.component_manager.deserialize_components(serialized_components)

        assert len(marker_tl) == 3
        assert {
            dsr_mrk.time for dsr_mrk in marker_tl.component_manager._components
        } == {u.time for u in [mrk1, mrk2, mrk3]}
