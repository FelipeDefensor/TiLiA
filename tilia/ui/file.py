"""
Functions for displaying dialogs that relate to file and media opening and saving.
"""


import tkinter as tk
from tkinter import filedialog

from tilia import globals_

import logging

logger = logging.getLogger(__name__)


def choose_media_file():

    audio_filetypes = get_filetypes_str(
        globals_.SUPPORTED_AUDIO_FORMATS + globals_.CONVERTIBLE_AUDIO_FORMATS
    )

    video_filetypes = get_filetypes_str(globals_.SUPPORTED_VIDEO_FORMATS)

    all_filetypes = get_filetypes_str(
        globals_.SUPPORTED_AUDIO_FORMATS
        + globals_.CONVERTIBLE_AUDIO_FORMATS
        + globals_.SUPPORTED_VIDEO_FORMATS
    )

    file_path = tk.filedialog.askopenfilename(
        title="Load media...",
        filetypes=[
            ("All supported media files", all_filetypes),
            ("Audio files", audio_filetypes),
            ("Video files", video_filetypes),
            ("All files", "*.*"),
        ],
    )

    if not file_path:
        logger.debug("User cancelled or closed load media window.")
        return

    return file_path


def get_filetypes_str(formats: list):
    filetypes = ""
    for frmt in formats:
        filetypes += "." + frmt + " "

    return filetypes.rstrip()
