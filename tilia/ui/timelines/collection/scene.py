from __future__ import annotations

from PyQt6.QtWidgets import QGraphicsScene


class TimelineUIsScene(QGraphicsScene):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
