import os.path
import time
import tkinter as tk
from collections import OrderedDict
from unittest.mock import patch, PropertyMock

import pytest

from tilia.ui.tkinterui import TkinterUI
from tests.conftest import pump_events
from tilia.ui.windows import WindowKind


class TiliaDummy:

    def __init__(self):
        self.media_length = 99
        self.media_metadata = {'title': 'test'}

    def get_media_path(self):
        return r'test_path'




class TestTkinterUI:

    def test_get_metadata_non_editable_fields(self, tkui):
        tkui.app = TiliaDummy()
        assert tkui.get_metadata_non_editable_fields() == OrderedDict({
            'media length': 99,
            'media path': 'test_path'
        })

    @patch('tilia.ui.tkinterui.Inspect')
    def test_on_request_window_inspect(self, inspect_mock, tkui):

        tkui.on_request_window(WindowKind.INSPECT)
        assert inspect_mock.called

        tkui.on_request_window(WindowKind.INSPECT)
        assert tkui._windows[WindowKind.INSPECT].focus.called

    @patch('tilia.ui.tkinterui.ManageTimelines')
    def test_on_request_window_manage_timelines(self, managetl_mock, tkui):
        tkui.on_request_window(WindowKind.MANAGE_TIMELINES)
        assert managetl_mock.called

    @patch('tilia.ui.tkinterui.MediaMetadataWindow')
    def test_on_request_window_media_metadata(self, mmtdata_mock, tkui):
        tkui.on_request_window(WindowKind.MEDIA_METADATA)
        assert mmtdata_mock.called


    @patch('tilia.ui.tkinterui.About')
    def test_on_request_window_about(self, about_mock, tkui):
        tkui.on_request_window(WindowKind.ABOUT)
        assert about_mock.called

