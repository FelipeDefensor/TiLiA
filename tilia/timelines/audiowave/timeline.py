from __future__ import annotations

import pydub
import pydub.exceptions
import pydub.utils

from tilia.settings import settings
from tilia.timelines.base.timeline import Timeline
from tilia.timelines.timeline_kinds import TimelineKind
from tilia.timelines.component_kinds import ComponentKind
from tilia.requests import get, Get, post, Post
from tilia.timelines.base.timeline import TimelineComponentManager
import tilia.errors


class AudioWaveTimeline(Timeline):
    KIND = TimelineKind.AUDIOWAVE_TIMELINE    
    component_manager: AudioWaveTLComponentManager

    @property
    def default_height(self):
        return settings.get("audiowave_timeline", "default_height")

    def _create_timeline(self):
        dt, normalised_amplitudes = self._get_normalised_amplitudes()
        self._create_components(dt, normalised_amplitudes)

    def _get_audio(self):
        path = get(Get.MEDIA_PATH)
        try:
            return pydub.AudioSegment.from_file(path)        
        except:
            tilia.errors.display(tilia.errors.AUDIOWAVE_INVALID_FILE)
            return None
    
    def _get_normalised_amplitudes(self):    
        divisions = min([get(Get.PLAYBACK_AREA_WIDTH), settings.get("audiowave_timeline", "max_divisions"), self.audio.frame_count()])
        dt = self.audio.duration_seconds / divisions
        chunks = pydub.utils.make_chunks(self.audio, dt * 1000)
        amplitude = [chunk.rms for chunk in chunks]
        return dt, [amp / max(amplitude) for amp in amplitude]
    
    def _create_components(self, duration: float, amplitudes: float):
        for i in range(len(amplitudes)):
            self.create_timeline_component(
                kind = ComponentKind.AUDIOWAVE,
                start = i * duration,
                end = (i + 1) * duration,
                amplitude = amplitudes[i]
            )

    def refresh(self):       
        self.clear()
        self.audio = self._get_audio()
        if not self.audio:
            self._update_visibility(False)
            return
        self._update_visibility(True)
        self._create_timeline()

    def _update_visibility(self, is_visible: bool):
        if self.get_data("is_visible") != is_visible:
            self.set_data("is_visible", is_visible)
            post(Post.TIMELINE_SET_DATA_DONE, self.id, "is_visible", is_visible)

    def get_dB(self, start_time, end_time):
        return self.audio[start_time * 1000: end_time * 1000].dBFS

class AudioWaveTLComponentManager(TimelineComponentManager):
    COMPONENT_TYPES = [ComponentKind.AUDIOWAVE]

    def __init__(self):
        super().__init__(self.COMPONENT_TYPES)
