import pytest

from tilia.timelines.beat.components import Beat
from tilia.timelines.beat.timeline import BeatTimeline
from tilia.timelines.component_kinds import ComponentKind
from tilia.timelines.timeline_kinds import TimelineKind as TlKind
from tilia.ui.timelines.beat import BeatTimelineUI, BeatUI


class TestBeatTimelineUI(BeatTimelineUI):
    def create_component(self, _: ComponentKind, *args, **kwargs): ...

    def create_beat(self, *args, **kwargs) -> tuple[Beat, BeatUI]: ...


@pytest.fixture
def beat_tlui(tls, tluis) -> TestBeatTimelineUI:
    tl: BeatTimeline = tls.create_timeline(TlKind.BEAT_TIMELINE, [], beat_pattern=[4])
    ui = tluis.get_timeline_ui(tl.id)

    def create_component(_: ComponentKind, *args, **kwargs):
        return create_beat(*args, **kwargs)

    def create_beat(*args, **kwargs):
        beat, error = tl.create_timeline_component(ComponentKind.BEAT, *args, **kwargs)
        if error:
            raise ValueError(f'Unable to create beat: {error}')
        tl.recalculate_measures()
        return beat, ui.get_element(beat.id)

    tl.create_beat = create_beat
    ui.create_beat = create_beat
    tl.create_component = create_component
    ui.create_component = create_component

    yield ui  # will be deleted by tls


@pytest.fixture
def beat_tl(beat_tlui):
    yield beat_tlui.timeline
