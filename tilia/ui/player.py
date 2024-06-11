from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QStackedWidget,
    QToolBar,
    QLabel,
    QSlider,
    QDoubleSpinBox,
)

from PyQt6.QtGui import QIcon, QAction, QPixmap

from PyQt6.QtCore import Qt

from tilia.ui import actions
from tilia.ui.actions import TiliaAction
from tilia.ui.format import format_media_time
from tilia.requests import Post, post, listen, stop_listening_to_all, get, Get

import tilia.errors

from pathlib import Path

from enum import Enum, auto


class PlayerToolbar(QToolBar):
    def __init__(self):
        super().__init__()

        self.setContextMenuPolicy(Qt.ContextMenuPolicy.PreventContextMenu)
        self._setup_requests()

        self.current_time_string = format_media_time(0)
        self.duration_string = format_media_time(0)
        self.last_playback_rate = 1.0

        self._setup_controls()

    def _setup_requests(self):
        LISTENS = {
            (Post.PLAYER_CURRENT_TIME_CHANGED, self.on_player_current_time_changed), 
            (Post.FILE_MEDIA_DURATION_CHANGED, self.on_media_duration_changed), 
            (Post.PLAYER_MEDIA_UNLOADED, self.on_media_unload), 
            (Post.PLAYER_STOPPED, self.on_stop), 
            (Post.PLAYER_UPDATE_CONTROLS, self.on_update_controls), 
            (Post.PLAYER_UI_UPDATE, self.on_ui_update_silent)
        }

        for post, callback in LISTENS:
            listen(self, post, callback)

    def _setup_controls(self):
        self.toolbar_stack = QStackedWidget()
        self.status_label = QLabel("<i>Player disabled. Load file via '</i>File > Load Media File<i>' to start.</i>")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.player_controls = QToolBar()
        self.toolbar_stack.addWidget(self.status_label)
        self.toolbar_stack.addWidget(self.player_controls)
        self.toolbar_stack.setCurrentWidget(self.status_label)
        self.addWidget(self.toolbar_stack)

        self.add_play_toggle()
        self.stop_action = actions.get_qaction(TiliaAction.MEDIA_STOP)
        self.player_controls.addAction(self.stop_action)
        self.add_loop_toggle()
        self.add_time_label()

        self.player_controls.addSeparator()

        self.add_volume_toggle()
        self.add_volume_slider()

        self.player_controls.addSeparator()

        self.add_playback_rate_spinbox()

    def on_player_current_time_changed(
        self, audio_time: float, *_
    ) -> None:
        self.current_time_string = format_media_time(audio_time)
        self.update_time_string()

    def on_stop(self) -> None:
        self.current_time_string = format_media_time(0)
        self.update_time_string()
        self.on_ui_update_silent(PlayerToolbarElement.TOGGLE_PLAY_PAUSE, False)

    def on_media_duration_changed(self, duration: float):
        self.duration_string = format_media_time(duration)
        self.update_time_string()

    def on_media_unload(self) -> None:
        self.duration_string = format_media_time(0)
        self.current_time_string = format_media_time(0)
        self.update_time_string()

    def update_time_string(self):
        self.time_label.setText(f"{self.current_time_string}/{self.duration_string}")

    def on_update_controls(self, state):
        match state:
            case PlayerStatus.NO_MEDIA:
                self.status_label.setText("<i>Player disabled. Load file via '</i>File > Load Media File<i>' to start.</i>")
                self.toolbar_stack.setCurrentWidget(self.status_label)
            case PlayerStatus.PLAYER_ENABLED:
                self.reset()
                self.toolbar_stack.setCurrentWidget(self.player_controls)
            case PlayerStatus.WAITING_FOR_YOUTUBE:
                self.status_label.setText("<i>Player disabled. Click on YouTube video to enable player.</i>")
                self.toolbar_stack.setCurrentWidget(self.status_label)

    def on_ui_update_silent(self, element_to_set, value):
        match element_to_set:
            case PlayerToolbarElement.TOGGLE_PLAY_PAUSE:
                element = self.play_toggle_action
            case PlayerToolbarElement.TOGGLE_LOOP:
                element = self.loop_toggle_action
            case PlayerToolbarElement.TOGGLE_VOLUME:
                element = self.volume_toggle_action
            case PlayerToolbarElement.SLIDER_VOLUME:
                element = self.volume_slider
            case PlayerToolbarElement.SPINBOX_PLAYBACK:
                self.last_playback_rate = value
                self.pr_spinbox_update_silent()
                return
            case _:
                tilia.errors.display(tilia.errors.PLAYER_TOOLBAR_ERROR, "Unknown element selected.")

        element.blockSignals(True)
        try:
            if element_to_set in [PlayerToolbarElement.TOGGLE_PLAY_PAUSE, PlayerToolbarElement.TOGGLE_LOOP, PlayerToolbarElement.TOGGLE_VOLUME]:
                element.setChecked(value)
            else:
                element.setValue(value)
        except:
            tilia.errors.display(tilia.errors.PLAYER_TOOLBAR_ERROR, f"Unable to set {element_to_set} with value {value} of type {type(value)}.")
        element.blockSignals(False)

    def destroy(self):
        stop_listening_to_all(self)
        super().destroy()

    def add_play_toggle(self):
        def on_play_toggle(checked: bool) -> None:
            post(Post.PLAYER_TOGGLE_PLAY_PAUSE, checked)

        play_toggle_icon = QIcon()
        play_toggle_icon.addPixmap(QPixmap(str(Path("ui", "img", "play15.png"))), QIcon.Mode.Normal, QIcon.State.Off)
        play_toggle_icon.addPixmap(QPixmap(str(Path("ui", "img", "pause15.png"))), QIcon.Mode.Normal, QIcon.State.On)        
        self.play_toggle_action = QAction(self)
        self.play_toggle_action.setText("Play / Pause")
        self.play_toggle_action.triggered.connect(lambda checked: on_play_toggle(checked))
        self.play_toggle_action.setToolTip("Play / Pause (Space)")
        self.play_toggle_action.setCheckable(True)
        self.play_toggle_action.setIcon(play_toggle_icon)
        self.play_toggle_action.setShortcut("Space")
        self.player_controls.addAction(self.play_toggle_action)

    def add_loop_toggle(self):
        def on_loop_changed(checked: bool) -> None:
            post(Post.PLAYER_TOGGLE_LOOP, checked)

        loop_toggle_icon = QIcon()
        loop_toggle_icon.addPixmap(QPixmap(str(Path("ui", "img", "loop15.png"))), QIcon.Mode.Normal, QIcon.State.On)
        loop_toggle_icon.addPixmap(QPixmap(str(Path("ui", "img", "no_loop15.png"))), QIcon.Mode.Normal, QIcon.State.Off)
        self.loop_toggle_action = QAction(self)
        self.loop_toggle_action.setText("Toggle Loop")
        self.loop_toggle_action.triggered.connect(lambda checked: on_loop_changed(checked))
        self.loop_toggle_action.setIcon(loop_toggle_icon)
        self.loop_toggle_action.setToolTip("Toggle Loop")
        self.loop_toggle_action.setCheckable(True)
        self.player_controls.addAction(self.loop_toggle_action)

    def add_time_label(self):
        self.time_label = QLabel(f"{self.current_time_string}/{self.duration_string}")
        self.time_label.setMargin(3)
        self.player_controls.addWidget(self.time_label)

    def add_volume_toggle(self):
        def on_volume_toggle(checked: bool) -> None:
            post(Post.PLAYER_VOLUME_MUTE, checked)
            self.volume_slider.setEnabled(not checked)

        volume_toggle_icon = QIcon()
        volume_toggle_icon.addPixmap(QPixmap(str(Path("ui", "img", "mute15.png"))), QIcon.Mode.Normal, QIcon.State.On)
        volume_toggle_icon.addPixmap(QPixmap(str(Path("ui", "img", "unmute15.png"))), QIcon.Mode.Normal, QIcon.State.Off)
        self.volume_toggle_action = QAction(self)
        self.volume_toggle_action.setText("Toggle Volume")
        self.volume_toggle_action.triggered.connect(lambda checked: on_volume_toggle(checked))
        self.volume_toggle_action.setIcon(volume_toggle_icon)
        self.volume_toggle_action.setToolTip("Mute / Unmute")
        self.volume_toggle_action.setCheckable(True)
        self.player_controls.addAction(self.volume_toggle_action)
    
    def add_volume_slider(self):
        def on_volume_slide(value: int) -> None:
            post(Post.PLAYER_VOLUME_CHANGE, value)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setMinimum(0)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(100)
        self.volume_slider.setToolTip("Volume")
        self.volume_slider.valueChanged.connect(lambda value: on_volume_slide(value))
        self.volume_slider.setStyleSheet(
            "QSlider {margin-right: 4px;}"
            "QSlider::groove:horizontal { height: 4px; background: grey;}" + 
            "QSlider::handle::horizontal { background: grey; border: 2px solid #ff964f; width: 8px; margin: -4px 0; border-radius: 6px;}"
        )
        self.player_controls.addWidget(self.volume_slider)
    
    def add_playback_rate_spinbox(self):
        def on_playback_rate_changed(rate: float) -> None:
            post(Post.PLAYER_PLAYBACK_RATE_TRY, rate)

            if get(Get.MEDIA_TYPE) == "youtube":
                self.pr_spinbox_update_silent()

            else:
                self.last_playback_rate = rate

        self.pr_spinbox = QDoubleSpinBox()
        self.pr_spinbox.setMinimum(0)
        self.pr_spinbox.setValue(1.0)
        self.pr_spinbox.setSingleStep(0.25)
        self.pr_spinbox.setFixedWidth(self.pr_spinbox.height() // 8)
        self.pr_spinbox.setSuffix(" x")
        self.pr_spinbox.setToolTip("Playback Rate")
        self.pr_spinbox.setKeyboardTracking(False)
        self.pr_spinbox.valueChanged.connect(on_playback_rate_changed)
        self.player_controls.addWidget(self.pr_spinbox)

    def pr_spinbox_update_silent(self) -> None:
        self.pr_spinbox.blockSignals(True)
        self.pr_spinbox.clearFocus()
        self.pr_spinbox.setValue(self.last_playback_rate)
        self.pr_spinbox.blockSignals(False)

    def reset(self):
        self.blockSignals(True)
        self.play_toggle_action.setChecked(False)
        self.volume_toggle_action.setChecked(False)
        self.volume_slider.setValue(100)
        self.loop_toggle_action.setChecked(False)
        self.last_playback_rate = 1
        self.pr_spinbox.setValue(1)
        self.blockSignals(False)


class PlayerToolbarElement(Enum):
    TOGGLE_PLAY_PAUSE = auto()
    TOGGLE_LOOP = auto()
    TOGGLE_VOLUME = auto()
    SLIDER_VOLUME = auto()
    SPINBOX_PLAYBACK = auto()


class PlayerStatus(Enum):
    NO_MEDIA = auto()
    PLAYER_ENABLED = auto()
    WAITING_FOR_YOUTUBE = auto()