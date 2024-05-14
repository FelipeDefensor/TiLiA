from enum import auto, Enum


class ComponentKind(Enum):
    MODE = auto()
    HARMONY = auto()
    BEAT = auto()
    MARKER = auto()
    HIERARCHY = auto()
    AUDIOWAVE = auto()


def get_component_class_by_kind(kind: ComponentKind):
    from tilia.timelines.hierarchy.components import Hierarchy
    from tilia.timelines.marker.components import Marker
    from tilia.timelines.beat.components import Beat
    from tilia.timelines.harmony.components import Harmony, Mode
    from tilia.timelines.audiowave.components import AudioWave

    kind_to_class_dict = {
        ComponentKind.HIERARCHY: Hierarchy,
        ComponentKind.MARKER: Marker,
        ComponentKind.BEAT: Beat,
        ComponentKind.HARMONY: Harmony,
        ComponentKind.MODE: Mode,
        ComponentKind.AUDIOWAVE: AudioWave
    }

    return kind_to_class_dict[kind]
