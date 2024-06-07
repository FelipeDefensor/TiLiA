from __future__ import annotations

import functools
import sys
from abc import ABC, abstractmethod
from enum import Enum, auto
from pathlib import Path

from PyQt6.QtCore import QTimer

import tilia.errors
from tilia.media import exporter
from tilia.utils import get_tilia_class_string
from tilia.requests import (
    listen,
    Post,
    serve,
    Get,
    post,
    stop_listening_to_all,
    get,
    stop_serving_all,
)
from tilia.ui.strings import NO_MEDIA_LOADED_ERROR_TITLE, NO_MEDIA_LOADED_ERROR_MESSAGE
from tilia.timelines.timeline_kinds import TimelineKind

from tilia.ui.player import PlayerToolbarElement


class MediaTimeChangeReason(Enum):
    PLAYBACK = auto()
    SEEK = auto()
    LOAD = auto()


class Player(ABC):
    UPDATE_INTERVAL = 100
    E = UPDATE_INTERVAL / 500
    MEDIA_TYPE = None

    def __init__(self):
        super().__init__()

        self._setup_requests()
        self.is_media_loaded = False
        self.duration = 0.0
        self.playback_start = 0.0
        self.playback_end = 0.0
        self.current_time = 0.0
        self.media_path = ""
        self.is_playing = False
        self.is_looping = False
        self.loop_start = 0
        self.loop_end = 0
        self.loop_elements = set()
        self.qtimer = QTimer()
        self.qtimer.timeout.connect(self._play_loop)

    def __str__(self):
        return get_tilia_class_string(self)

    def _setup_requests(self):        
        LISTENS = {
            (Post.PLAYER_TOGGLE_PLAY_PAUSE, self.toggle_play),
            (Post.PLAYER_STOP, self.stop),
            (Post.PLAYER_TOGGLE_LOOP, self.toggle_loop),
            (Post.PLAYER_VOLUME_CHANGE, self.on_volume_change),
            (Post.PLAYER_VOLUME_MUTE, self.on_volume_mute),
            (Post.PLAYER_PLAYBACK_RATE_TRY, self.on_playback_rate_try),
            (Post.PLAYER_SEEK, self.on_seek),
            (Post.PLAYER_SEEK_IF_NOT_PLAYING, functools.partial(self.on_seek, if_paused=True)),
            (Post.PLAYER_REQUEST_TO_UNLOAD_MEDIA, self.unload_media),
            (Post.PLAYER_REQUEST_TO_LOAD_MEDIA, self.load_media),
            (Post.PLAYER_EXPORT_AUDIO, self.on_export_audio),
            (Post.HIERARCHY_MERGE_SPLIT_DONE, self.on_hierarchy_merge_split),
            (Post.TIMELINE_COMPONENT_DELETED, self.on_component_delete),
            (Post.TIMELINE_COMPONENT_SET_DATA_DONE, self.on_component_set_data),
            (Post.EDIT_UNDO, self.cancel_loop),
            (Post.EDIT_REDO, self.cancel_loop)
        }

        SERVES = {
            (Get.MEDIA_CURRENT_TIME, lambda: self.current_time),
            (Get.MEDIA_PATH, lambda: self.media_path),
            (Get.MEDIA_TYPE, lambda: self.MEDIA_TYPE)
        }

        for post, callback in LISTENS:
            listen(self, post, callback)

        for request, callback in SERVES:
            serve(self, request, callback)

    @property
    def playback_length(self):
        return self.playback_end - self.playback_start

    def load_media(
        self, path: str | Path, start: float = 0.0, end: float = 0.0
    ) -> bool:
        if self.is_playing:
            self.stop()

        success = self._engine_load_media(path)
        if not success:
            tilia.errors.display(tilia.errors.MEDIA_LOAD_FAILED, path)
            return False
        self.on_media_load_done(path, start, end)
        return True

    def on_media_load_done(self, path, start, end):
        self.media_path = str(path)
        self.playback_start = start

        post(
            Post.PLAYER_URL_CHANGED,
            self.media_path,
        )

        post(Post.PLAYER_CURRENT_TIME_CHANGED, 0.0, MediaTimeChangeReason.LOAD)

        self.is_media_loaded = True

    def on_media_duration_available(self, duration):
        self.playback_end = self.duration = duration
        post(Post.PLAYER_DURATION_AVAILABLE, duration)

    def setup_playback_start_and_end(self, start, end):
        self.playback_start = start
        self.playback_end = end or self.duration

        start or self._engine_seek(start)

    def unload_media(self):
        self._engine_unload_media()
        self.is_media_loaded = False
        self.duration = 0.0
        self.current_time = 0.0
        self.media_path = ""
        self.is_playing = False
        self.is_looping = False
        self._remove_loop_elements_UI()
        post(Post.PLAYER_UI_UPDATE, PlayerToolbarElement.TOGGLE_LOOP, False)
        post(Post.PLAYER_CURRENT_LOOP_CHANGED, 0, 0)
        post(Post.PLAYER_MEDIA_UNLOADED)

    def toggle_play(self, toggle_is_playing: bool):
        if not self.media_path:
            post(
                Post.DISPLAY_ERROR,
                title=NO_MEDIA_LOADED_ERROR_TITLE,
                message=NO_MEDIA_LOADED_ERROR_MESSAGE,
            )
            return

        if toggle_is_playing:
            if self.is_looping:
                self.on_seek(self.loop_start)
            self._engine_play()
            self.is_playing = True
            self.start_play_loop()
            post(Post.PLAYER_UNPAUSED)

        else:
            self._engine_pause()
            self.stop_play_loop()
            self.is_playing = False
            post(Post.PLAYER_PAUSED)

    def stop(self):
        """Stops music playback and resets slider position"""
        post(Post.PLAYER_STOPPING)
        if not self.is_playing and self.current_time == 0.0:
            return

        self._engine_stop()
        self.stop_play_loop()
        self.is_playing = False
        
        if self.is_looping:
            self.is_looping = False
            self._remove_loop_elements_UI()
            post(Post.PLAYER_UI_UPDATE, PlayerToolbarElement.TOGGLE_LOOP, False)
            post(Post.PLAYER_CURRENT_LOOP_CHANGED, 0, 0)

        self._engine_seek(self.playback_start)
        self.current_time = self.playback_start

        post(Post.PLAYER_STOPPED)
        post(
            Post.PLAYER_CURRENT_TIME_CHANGED,
            self.current_time,
            MediaTimeChangeReason.PLAYBACK,
        )

    def toggle_loop(self, is_looping):
        if is_looping:                     
            hierarchies_with_selected = [tl for tl in get(Get.TIMELINE_ELEMENTS_SELECTED) if tl.TIMELINE_KIND is TimelineKind.HIERARCHY_TIMELINE]
            self.loop_elements = {
                (element.timeline_ui.id, element.id)
                for elements_by_tl in hierarchies_with_selected
                for element in elements_by_tl.element_manager.get_selected_elements()
            }
                
            self._update_loop_elements()            

        else:
            self.is_looping = False
            self._engine_loop(False)
            self._remove_loop_elements_UI()
            post(Post.PLAYER_CURRENT_LOOP_CHANGED, 0, 0)
            
    def on_hierarchy_merge_split(self, new_units, old_units):
        if set(old_units).issubset(self.loop_elements) and self.is_looping:
            for new_unit in new_units:
                self.loop_elements.add(new_unit)

            for old_unit in old_units:
                self.loop_elements.remove(old_unit)
            
            self._update_loop_elements()

    def on_component_delete(self, _, timeline_id, component_id, loop_remove):
        if loop_remove:
            deleted = (timeline_id, component_id)
            if deleted in self.loop_elements and self.is_looping:
                self.loop_elements.remove(deleted)

                if len(self.loop_elements) == 0:
                    self.is_looping = False
                    post(Post.PLAYER_UI_UPDATE, PlayerToolbarElement.TOGGLE_LOOP, False)
                    post(Post.PLAYER_CURRENT_LOOP_CHANGED, 0, 0)
                    return   
                
                self._update_loop_elements()

    def on_component_set_data(self, timeline_id, component_id, *_):
        updated = (timeline_id, component_id)
        if updated in self.loop_elements and self.is_looping:
            self._update_loop_elements()

    def cancel_loop(self):
        if self.is_looping:
            self.is_looping = False
            self._remove_loop_elements_UI()

    def _remove_loop_elements_UI(self):
        for element in [get(Get.TIMELINE_UI_ELEMENT, element_id[0], element_id[1]) for element_id in self.loop_elements]:
            element.on_loop_set(False)
            
        self.loop_elements.clear()

    def _update_loop_elements(self):
        if self.loop_elements: 
            connected, [start_time, end_time] = self._check_loop_continuity()
            if not connected:
                post(
                    Post.DISPLAY_ERROR,
                    "Looping Error",
                    "Selected Hierarchies are disjunct."
                )
                self.is_looping = False
                self._remove_loop_elements_UI()
                post(Post.PLAYER_UI_UPDATE, PlayerToolbarElement.TOGGLE_LOOP, False)
                post(Post.PLAYER_CURRENT_LOOP_CHANGED, 0, 0)
                return
            
            if abs(end_time - get(Get.MEDIA_DURATION)) < 1.0:
                end_time = get(Get.MEDIA_DURATION) - self.E

            for element in [get(Get.TIMELINE_UI_ELEMENT, element_id[0], element_id[1]) for element_id in self.loop_elements]:
                element.on_loop_set(True)

        else:
            start_time = 0
            end_time = get(Get.MEDIA_DURATION)
            self._engine_loop(True)            
            self._remove_loop_elements_UI()

        self.is_looping = True
        self.loop_start = start_time
        self.loop_end = end_time
        post(Post.PLAYER_UI_UPDATE, PlayerToolbarElement.TOGGLE_LOOP, True)
        post(Post.PLAYER_CURRENT_LOOP_CHANGED, start_time, end_time)
        

    def _check_loop_continuity(self) -> tuple[bool, list]:
        def dfs(index, cur_min, cur_max):
            if graph[index]['is_visited']:
                return cur_min, cur_max
            
            graph[index]['is_visited'] = True
            for node in graph[index]['node']:
                new_min, new_max = dfs(node, min(node, cur_min), max(node, cur_max))
                cur_min = min(new_min, cur_min)
                cur_max = max(new_max, cur_max)

            return cur_min, cur_max
        
        graph = {}
        elements = [get(Get.TIMELINE_UI_ELEMENT, element_id[0], element_id[1]) for element_id in self.loop_elements]
        for element in elements:
            if element.get_data('start') in graph:
                graph[element.get_data('start')]['node'].add(element.get_data('end'))
            else:
                graph[element.get_data('start')] = {
                    'is_visited': False,
                    'node': {element.get_data('end')}
                }

            if element.get_data('end') in graph:
                graph[element.get_data('end')]['node'].add(element.get_data('start'))
            else:
                graph[element.get_data('end')] = {
                    'is_visited': False,
                    'node': {element.get_data('start')}
                }

        connections = {}
        for i in graph:
            if not graph[i]['is_visited']:
                min_time, max_time = dfs(i, i, i)
                connections[i] = [min_time, max_time]

        connector = next(iter(connections.values()))

        for i in connections:
            if (connector[0] < connections[i][0] and connector[1] > connections[i][0] and connector[1] < connections[i][1]):
                connector[1] = connections[i][1]
            elif (connector[0] > connections[i][0] and connector[0] < connections[i][1] and connector[1] > connections[i][1]):
                connector[0] = connections[i][0]
            elif (connector[0] <= connections[i][0] and connector[1] >= connections[i][1]):
                pass
            elif (connector[0] > connections[i][0] and connector[1] < connections[i][1]):
                connector[0] = connections[i][0]
                connector[1] = connections[i][1]
            else:
                return False, [0, 0]
            
        return True, connector

    def on_volume_change(self, volume: int) -> None:
        self._engine_set_volume(volume)

    def on_volume_mute(self, is_muted: bool) -> None:
        self._engine_set_mute(is_muted)

    def on_playback_rate_try(self, playback_rate: float) -> None:
        self._engine_try_playback_rate(playback_rate)

    def on_seek(self, time: float, if_paused: bool = False) -> None:
        if if_paused and self.is_playing:
            return

        if self.is_media_loaded:
            self.check_seek_outside_loop(time)

            self._engine_seek(time)

        self.current_time = time
        
        post(
            Post.PLAYER_CURRENT_TIME_CHANGED,
            self.current_time,
            MediaTimeChangeReason.SEEK,
        )

    def on_export_audio(self, segment_name: str, start_time: float, end_time: float):
        if self.MEDIA_TYPE != "audio":            
            tilia.errors.display(tilia.errors.EXPORT_AUDIO_FAILED, "Can only export from audio files.")
            return

        if sys.platform == "darwin":    
            tilia.errors.display(tilia.errors.EXPORT_AUDIO_FAILED, "Exporting audio is not available on macOS.")
            return

        path, _ = get(
            Get.FROM_USER_SAVE_PATH_OGG,
            "Export audio",
            f"{get(Get.MEDIA_TITLE)}_{segment_name}",
        )

        if not path:
            return

        exporter.export_audio(
            source_path=get(Get.MEDIA_PATH),
            destination_path=path,
            start_time=start_time,
            end_time=end_time,
        )

    def start_play_loop(self):
        self.qtimer.start(self.UPDATE_INTERVAL)

    def stop_play_loop(self):
        self.qtimer.stop()

    def _play_loop(self) -> None:
        self.current_time = self._engine_get_current_time() - self.playback_start
        if self.check_not_loop_back(self.current_time):            
            post(
                Post.PLAYER_CURRENT_TIME_CHANGED,
                self.current_time,
                MediaTimeChangeReason.PLAYBACK,
            )

            if self.current_time >= self.playback_length:
                self.stop()

    def check_seek_outside_loop(self, time):
        if self.is_looping and any([time > self.loop_end + self.E, time < self.loop_start - self.E]):
            self.is_looping = False
            self._remove_loop_elements_UI()
            post(Post.PLAYER_UI_UPDATE, PlayerToolbarElement.TOGGLE_LOOP, False)
            post(Post.PLAYER_CURRENT_LOOP_CHANGED, 0, 0)

    def check_not_loop_back(self, time) -> bool:
        if self.is_looping and time >= self.loop_end:
            self.on_seek(self.loop_start)
            return False
        
        return True

    def clear(self):
        self.unload_media()

    def destroy(self):
        self.stop()
        self.unload_media()
        stop_listening_to_all(self)
        stop_serving_all(self)
        self._engine_exit()

    def restore_state(self, media_path: str):
        if self.media_path == media_path:
            return
        else:
            self.unload_media()
            self.load_media(media_path)

    @abstractmethod
    def _engine_pause(self) -> None: ...

    @abstractmethod
    def _engine_unpause(self) -> None: ...

    @abstractmethod
    def _engine_get_current_time(self) -> float: ...

    @abstractmethod
    def _engine_stop(self): ...

    @abstractmethod
    def _engine_seek(self, time: float) -> None: ...

    @abstractmethod
    def _engine_unload_media(self) -> None: ...

    @abstractmethod
    def _engine_load_media(self, media_path: str) -> None: ...

    @abstractmethod
    def _engine_play(self) -> None: ...

    @abstractmethod
    def _engine_get_media_duration(self) -> float: ...

    @abstractmethod
    def _engine_exit(self) -> float: ...

    @abstractmethod
    def _engine_set_volume(self, volume: int) -> None: ...

    @abstractmethod
    def _engine_set_mute(self, is_muted: bool) -> None: ...

    @abstractmethod
    def _engine_try_playback_rate(self, playback_rate: float) -> None: ...

    @abstractmethod
    def _engine_set_playback_rate(self, playback_rate: float) -> None: ...

    @abstractmethod
    def _engine_loop(self, is_looping: bool) -> None: ...

    def __repr__(self):
        return f"{type(self)}-{id(self)}"