from enum import Enum


class TimelineKind(Enum):
    HIERARCHY_TIMELINE = "HIERARCHY_TIMELINE"
    MARKER_TIMELINE = "MARKER_TIMELINE"
    BEAT_TIMELINE = "BEAT_TIMELINE"
    RANGE_TIMELINE = "RANGE_TIMELINE"
    SLIDER_TIMELINE = "SLIDER_TIMELINE"


IMPLEMENTED_TIMELINE_KINDS = [
    TimelineKind.HIERARCHY_TIMELINE,
    TimelineKind.SLIDER_TIMELINE,
    TimelineKind.MARKER_TIMELINE,
    TimelineKind.BEAT_TIMELINE,
]

USER_CREATABLE_TIMELINE_KINDS = [
    TimelineKind.HIERARCHY_TIMELINE,
    TimelineKind.MARKER_TIMELINE,
    TimelineKind.BEAT_TIMELINE,
]
