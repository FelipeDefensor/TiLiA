from __future__ import annotations

from typing import TYPE_CHECKING

from tilia.timelines.base.validators import validate_time, validate_bool
from tilia.timelines.component_kinds import ComponentKind

if TYPE_CHECKING:
    from tilia.timelines.beat.timeline import BeatTimeline

from tilia.timelines.base.component import TimelineComponent


class Beat(TimelineComponent):
    # serializer attributes
    SERIALIZABLE_BY_VALUE = ["time"]

    SERIALIZABLE_BY_ID = []
    SERIALIZABLE_BY_ID_LIST = []
    ORDERING_ATTRS = ("time",)

    KIND = ComponentKind.BEAT

    validators = {"time": validate_time, "is_first_in_measure": validate_bool}

    def __init__(
        self,
        timeline: BeatTimeline,
        id: int,
        time: float,
        comments="",
        **_,
    ):
        super().__init__(timeline, id)

        self.time = time
        self.comments = comments
        self.is_first_in_measure = False

    def __str__(self):
        return f"Beat({self.time})"

    def __repr__(self):
        return f"Beat({self.time})"

    @property
    def metric_position(self):
        self.timeline: BeatTimeline
        beat_index = self.timeline.get_beat_index(self)
        measure_index, index_in_measure = self.timeline.get_measure_index(beat_index)

        return self.timeline.measure_numbers[measure_index], index_in_measure + 1

    @property
    def measure_number(self):
        return self.metric_position[0]

    @property
    def beat_number(self):
        return self.metric_position[1]
