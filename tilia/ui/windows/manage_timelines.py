from typing import Optional

from PyQt6 import QtGui
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QCheckBox,
)

from tilia.requests import (
    Post,
    post,
    Get,
    get,
    listen,
    serve,
    stop_listening_to_all,
    stop_serving_all,
)
from tilia.timelines.timeline_kinds import TimelineKind
from tilia.ui.timelines.base.timeline import TimelineUI


class ManageTimelines(QDialog):
    def __init__(self):
        super().__init__()
        self._setup_widgets()
        self._setup_checkbox()
        self._setup_requests()
        self.show()

    def _setup_widgets(self):
        layout = QHBoxLayout()
        self.setLayout(layout)

        list_widget = TimelinesListWidget()
        self.list_widget = list_widget
        list_widget.currentItemChanged.connect(self.on_list_current_item_changed)
        layout.addWidget(list_widget)

        right_layout = QVBoxLayout()

        up_button = QPushButton("▲")
        up_button.pressed.connect(list_widget.on_up_button)

        down_button = QPushButton("▼")
        down_button.pressed.connect(list_widget.on_down_button)

        checkbox = QCheckBox("Visible")
        self.checkbox = checkbox
        checkbox.stateChanged.connect(self.on_checkbox_state_changed)

        self.delete_button = QPushButton("Delete")
        self.delete_button.pressed.connect(list_widget.on_delete_button)

        self.clear_button = QPushButton("Clear")
        self.clear_button.pressed.connect(list_widget.on_clear_button)
        right_layout.addWidget(up_button)
        right_layout.addWidget(down_button)
        right_layout.addWidget(checkbox)
        right_layout.addWidget(self.clear_button)
        right_layout.addWidget(self.delete_button)

        layout.addLayout(right_layout)

    def _setup_requests(self):
        serve(
            self,
            Get.WINDOW_MANAGE_TIMELINES_TIMELINE_UIS_TO_PERMUTE,
            self.get_timeline_uis_to_permute,
        )
        serve(
            self,
            Get.WINDOW_MANAGE_TIMELINES_TIMELINE_UIS_CURRENT,
            self.get_current_timeline_ui,
        )

    def _setup_checkbox(self):
        self.on_list_current_item_changed(self.list_widget.currentItem())

    def on_list_current_item_changed(self, item):
        def update_checkbox_state(timeline_ui):
            self.checkbox.setCheckState(
                Qt.CheckState.Checked
                if timeline_ui.get_data("is_visible")
                else Qt.CheckState.Unchecked
            )

        def update_delete_and_clear_buttons(timeline_ui):
            if timeline_ui.TIMELINE_KIND == TimelineKind.SLIDER_TIMELINE:
                self.delete_button.setEnabled(False)
                self.clear_button.setEnabled(False)
            else:
                self.delete_button.setEnabled(True)
                self.clear_button.setEnabled(True)

        if not item:  # when list is being cleared
            return

        update_checkbox_state(item.timeline_ui)
        update_delete_and_clear_buttons(item.timeline_ui)

    def on_checkbox_state_changed(self, state):
        timeline_ui = self.list_widget.currentItem().timeline_ui
        if timeline_ui.get_data("is_visible") != bool(state):
            post(Post.TIMELINE_IS_VISIBLE_SET_FROM_MANAGE_TIMELINES)

    def get_timeline_uis_to_permute(self):
        return self.list_widget.timeline_uis_to_permute

    def get_current_timeline_ui(self):
        return self.list_widget.currentItem().timeline_ui

    def closeEvent(self, a0: Optional[QtGui.QCloseEvent]) -> None:
        super().closeEvent(a0)
        stop_listening_to_all(self)
        stop_listening_to_all(self.list_widget)
        stop_serving_all(self)
        post(Post.WINDOW_MANAGE_TIMELINES_CLOSE_DONE)


class TimelineListItem(QListWidgetItem):
    def __init__(self, timeline_ui: TimelineUI):
        self.timeline_ui = timeline_ui
        super().__init__(self.get_timeline_ui_str(timeline_ui))

    def get_timeline_ui_str(self, timeline_ui: TimelineUI):
        if timeline_ui.TIMELINE_KIND == TimelineKind.SLIDER_TIMELINE:
            return "Slider"
        return timeline_ui.get_data("name")


class TimelinesListWidget(QListWidget):
    def __init__(self):
        super().__init__()
        self._setup_items()

        self.setCurrentRow(0)
        self.timeline_uis_to_permute = None
        listen(self, Post.TIMELINE_SET_DATA_DONE, self.on_timeline_set_data_done)
        listen(self, Post.TIMELINE_DELETE_DONE, self.on_timeline_set_changed)
        listen(self, Post.TIMELINE_CREATE_DONE, self.on_timeline_set_changed)

    def _setup_items(self):
        for tl in get(Get.TIMELINE_UIS):
            self.addItem(TimelineListItem(tl))

    def on_timeline_set_data_done(self, _, attr, __):
        if attr != "ordinal":
            return

        prev_selected = self.currentItem()
        self.clear()
        self._setup_items()
        for i in range(self.model().rowCount()):
            if self.item(i).timeline_ui == prev_selected.timeline_ui:
                self.setCurrentRow(i)
                break

    def on_timeline_set_changed(self, *_):
        prev_index = self.currentIndex()
        self.clear()
        self._setup_items()
        self.setCurrentRow(prev_index.row())

    def on_up_button(self):
        if not self.selectedIndexes():
            return

        selected = self.selectedItems()[0]
        index = self.selectedIndexes()[0].row()
        previous = self.item(index - 1)
        if previous:
            self.timeline_uis_to_permute = (selected.timeline_ui, previous.timeline_ui)
            post(Post.TIMELINE_ORDINAL_DECREASE_FROM_MANAGE_TIMELINES)
            self.timeline_uis_to_permute = None

    def on_down_button(self):
        if not self.selectedIndexes():
            return
        selected = self.selectedItems()[0]
        index = self.selectedIndexes()[0].row()
        next = self.item(index + 1)
        if next:
            self.timeline_uis_to_permute = (selected.timeline_ui, next.timeline_ui)
            post(Post.TIMELINE_ORDINAL_INCREASE_FROM_MANAGE_TIMELINES)
            self.timeline_uis_to_permute = None

    @staticmethod
    def on_delete_button():
        post(Post.TIMELINE_DELETE_FROM_MANAGE_TIMELINES)

    @staticmethod
    def on_clear_button():
        post(Post.TIMELINE_CLEAR_FROM_MANAGE_TIMELINES)
