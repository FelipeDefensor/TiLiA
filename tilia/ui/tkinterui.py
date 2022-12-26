"""
Defines the TkinterUI class, which composes the TiLiA object, and its dependencies.
The TkinterUI is responsible for high-level control of the GUI.
"""

from __future__ import annotations
from collections import OrderedDict
from typing import TYPE_CHECKING, Any, Callable
import sys
import tkinter as tk
import tkinter.font
import tkinter.filedialog
import tkinter.messagebox
import tkinter.simpledialog
import traceback
import time


from tilia import globals_, events, settings
from tilia.player import player_ui
from tilia.exceptions import UserCancelledSaveError, UserCancelledOpenError
from tilia.timelines.timeline_kinds import TimelineKind
from tilia.events import Event, subscribe
from . import file
from .common import ask_yes_no, ask_for_directory
from .event_handler import TkEventHandler
from .timelines.common import TimelineUICollection
from .windows.common import AppWindow
from .windows.manage_timelines import ManageTimelines
from .windows.metadata import MetadataWindow
from .windows.inspect import Inspect
from .windows.kinds import WindowKind

if TYPE_CHECKING:
    from tilia.main import TiLiA

import logging

logger = logging.getLogger(__name__)


def handle_exception(exc_type, exc_value, exc_traceback) -> None:
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return

    logging.error("Uncaught exception", exc_info=(exc_type, exc_value, exc_traceback))
    traceback.print_tb(exc_traceback)
    time.sleep(0.1)  # needed so traceback gets fully printed before type and value
    print(exc_type)
    print(exc_value)


class TkinterUI:
    """
    Responsible for high-level control of the GUI:
        - Instances the tk.TK object;
        - Is composed of the high level tkinter frames (toolbar parent, timelines parent, etc...);
        - Is composed of the TkinterUIMenus class;
        - Is composed of a TkEventHandler which translates tkinter events into events.py events;
        - Keeps 'global' interface data such as window and timeline dimensions.
    """

    def __init__(self, app: TiLiA):

        subscribe(self, Event.MENU_OPTION_FILE_LOAD_MEDIA, self.on_menu_file_load_media)
        subscribe(self, Event.UI_REQUEST_WINDOW_INSPECTOR, lambda: self.on_request_window(WindowKind.INSPECT))
        subscribe(self, Event.UI_REQUEST_WINDOW_MANAGE_TIMELINES, lambda: self.on_request_window(WindowKind.MANAGE_TIMELINES))
        subscribe(self, Event.UI_REQUEST_WINDOW_METADATA, lambda: self.on_request_window(WindowKind.METADATA))
        subscribe(self, Event.REQUEST_DISPLAY_ERROR, self.on_display_error)
        subscribe(self, Event.INSPECT_WINDOW_CLOSED, lambda: self.on_window_closed(WindowKind.INSPECT))
        subscribe(self, Event.MANAGE_TIMELINES_WINDOW_CLOSED, lambda: self.on_window_closed(WindowKind.MANAGE_TIMELINES))
        subscribe(self, Event.METADATA_WINDOW_CLOSED, lambda: self.on_window_closed(WindowKind.METADATA))
        subscribe(self, Event.TILIA_FILE_LOADED, self.on_tilia_file_loaded)

        logger.debug("Starting TkinterUI...")

        self._app = app
        self._setup_tk_root()

        self.default_font = tkinter.font.nametofont("TkDefaultFont")

        self.timeline_width = globals_.DEFAULT_TIMELINE_WIDTH
        self.timeline_padx = globals_.DEFAULT_TIMELINE_PADX

        self.window_width = globals_.DEFAULT_WINDOW_WIDTH
        self.window_height = globals_.DEFAULT_WINDOW_HEIGHT

        self._setup_frames()
        self._setup_menus()

        self.event_handler = TkEventHandler(self.root)

        self._create_timeline_ui_collection()

        self._windows = {
            WindowKind.INSPECT: None,
            WindowKind.METADATA: None,
            WindowKind.MANAGE_TIMELINES: None
        }

        logger.debug("Tkinter UI started.")


    def _setup_tk_root(self):
        self.root = tk.Tk()
        set_startup_geometry(self.root)
        self.root.focus_set()

        self.root.report_callback_exception = handle_exception

        self.root.title(globals_.APP_NAME)
        icon = tk.PhotoImage(file=globals_.APP_ICON_PATH)
        self.root.iconphoto(True, icon)

        self.root.protocol(
            "WM_DELETE_WINDOW", lambda: events.post(Event.REQUEST_CLOSE_APP)
        )

    def _setup_menus(self):
        self.menus = TkinterUIMenus(self, self.root)

    def launch(self):
        logger.debug("Entering Tkinter UI mainloop.")
        self.root.mainloop()

    @property
    def timeline_total_size(self):
        return self.timeline_width + 2 * self.timeline_padx

    def _create_timeline_ui_collection(self):

        self.timeline_ui_collection = TimelineUICollection(
            self,
            self.scrollable_frame,
            self.hscrollbar,
            self.timelines_toolbar_frame
        )

    def get_window_size(self):
        return self.root.winfo_width()

    def get_timeline_ui_collection(self):
        return self.timeline_ui_collection

    def _setup_frames(self):
        # create frames
        self.main_frame = tk.Frame(self.root)

        self.app_toolbars_frame = AppToolbarsFrame(self.main_frame)
        self.timelines_toolbar_frame = tk.Frame(
            self.main_frame
        )

        _scrollable_frame = ScrollableFrame(self.main_frame)
        self.scrollable_frame = _scrollable_frame.frame

        self.hscrollbar = tk.Scrollbar(self.main_frame, orient=tk.HORIZONTAL)

        # pack frames
        self.app_toolbars_frame.pack(fill="x")
        self.timelines_toolbar_frame.pack(fill="x")
        self.hscrollbar.pack(fill="x", side=tk.BOTTOM)
        _scrollable_frame.pack(side=tk.TOP, fill="both", expand=True)

        self.main_frame.pack(fill="both", expand=True)

    # noinspection PyTypeChecker,PyUnresolvedReferences
    def on_request_window(self, kind: WindowKind):

        if kind == WindowKind.INSPECT:
            if not self._windows[WindowKind.INSPECT]:
                self._windows[WindowKind.INSPECT] = Inspect(self.root)
            else:
                self._windows[WindowKind.INSPECT].toplevel.focus_set()

        elif kind == WindowKind.MANAGE_TIMELINES:
            if not self._windows[WindowKind.MANAGE_TIMELINES]:
                self._windows[WindowKind.MANAGE_TIMELINES] = ManageTimelines(
                    self, self.get_timeline_info_for_manage_timelines_window()
                )
            else:
                self._windows[WindowKind.MANAGE_TIMELINES].toplevel.focus_set()

        elif kind == WindowKind.METADATA:
            if not self._windows[WindowKind.METADATA]:
                self._windows[WindowKind.METADATA] = MetadataWindow(
                    self,
                    self._app.media_metadata,
                    self.get_metadata_non_editable_fields()
                )
            else:
                self._windows[WindowKind.METADATA].toplevel.focus_set()

    def on_window_closed(self, kind: WindowKind):
        self._windows[kind] = None

    def on_tilia_file_loaded(self):
        windows_to_close = [WindowKind.INSPECT, WindowKind.MANAGE_TIMELINES, WindowKind.METADATA]

        for window_kind in windows_to_close:
            if window := self._windows[window_kind]:
                window.destroy()

    @staticmethod
    def on_display_error(title: str, message: str):
        tk.messagebox.showerror(title, message)

    def get_metadata_non_editable_fields(self) -> dict[str]:

        return OrderedDict({
            'media length': self._app.media_length,
            'media path': self._app.get_media_path()
        })

    def get_timeline_info_for_manage_timelines_window(self) -> list[tuple[int, str]]:
        return [
            (tlui.timeline.id, str(tlui))
            for tlui in sorted(self.timeline_ui_collection.get_timeline_uis(), key=lambda t: t.timeline.id)
        ]

    def get_elements_for_pasting(self) -> dict[str: dict | TimelineKind]:
        return self._app.get_elements_for_pasting()

    def get_id(self) -> str:
        return self._app.get_id()

    def get_media_length(self):
        return self._app.media_length

    @staticmethod
    def on_menu_file_load_media():
        media_path = file.choose_media_file()

        events.post(Event.REQUEST_LOAD_MEDIA, media_path)

    @staticmethod
    def get_file_save_path(initial_filename: str) -> str | None:
        path = tk.filedialog.asksaveasfilename(
            defaultextension=f"{globals_.FILE_EXTENSION}",
            initialfile=initial_filename,
            filetypes=((f"{globals_.APP_NAME} files", f"*.{globals_.FILE_EXTENSION}"),),
        )

        if not path:
            raise UserCancelledSaveError("User cancelled or closed save window dialog.")

        return path

    @staticmethod
    def get_file_open_path():
        path = tk.filedialog.askopenfilename(
            title=f"Open {globals_.APP_NAME} file...",
            filetypes=((f"{globals_.APP_NAME} files", f"*.{globals_.FILE_EXTENSION}"),),
        )

        if not path:
            raise UserCancelledOpenError("User cancelled or closed open window dialog.")

        return path

    @staticmethod
    def ask_save_changes():
        return tk.messagebox.askyesnocancel(
            "Save changes?", f"Save changes to current file?"
        )

    @staticmethod
    def ask_string(title: str, prompt: str) -> str:
        return tk.simpledialog.askstring(title, prompt=prompt)

    def ask_yes_no(self, title: str, prompt: str) -> bool:
        return ask_yes_no(title, prompt)

    def get_timeline_ui_attribute_by_id(self, id_: int, attribute: str) -> Any:
        return self.timeline_ui_collection.get_timeline_ui_attribute_by_id(
            id_, attribute
        )

    @staticmethod
    def ask_for_directory(title: str) -> str | None:
        return ask_for_directory(title)


class AppToolbarsFrame(tk.Frame):
    def __init__(self, *args, **kwargs):
        super(AppToolbarsFrame, self).__init__(*args, **kwargs)

        self.playback_frame = player_ui.PlayerUI(self)

        self.auto_scroll_checkbox = CheckboxItem(
            label="Auto-scroll",
            value=settings.settings["general"]["auto-scroll"],
            set_func=lambda: settings.edit_setting(
                "general", "auto-scroll", self.auto_scroll_checkbox.variable.get()
            ),
            parent=self
        )

        self.playback_frame.pack(side=tk.LEFT, anchor=tk.W)
        self.auto_scroll_checkbox.pack(side=tk.LEFT, anchor=tk.W)


class ScrollableFrame(tk.Frame):
    """Tk.Frame does not support scrolling. This workaround relies
    on a frame placed inside a canvas, which does support scrolling.
    self.frame is the frame that must be used by outside widgets."""
    def __init__(self, parent) -> None:
        super().__init__(parent)
        self.canvas = tk.Canvas(self, borderwidth=0, highlightthickness=0)
        self.frame = tk.Frame(self.canvas)
        self.vsb = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=self.vsb.set)

        self.vsb.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)
        self.canvas.create_window((0, 0), window=self.frame, anchor="nw",
                                  tags="self.frame")

        self.frame.bind("<Configure>", self.on_frame_configure)
        self.canvas.bind("<Configure>", lambda e: events.post(Event.ROOT_WINDOW_RESIZED, e.width, e.height))

    def on_frame_configure(self, event):
        '''Reset the scroll region to encompass the inner frame'''
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))


class CheckboxItem(tk.Frame):
    def __init__(
        self, label: str, value: bool, set_func: Callable, parent, *args, **kwargs
    ):
        """Checkbox toolbar item to be displayed above timeline toolbars.
        value is the default boolean value of the checkbox.
        set_func is the function that will be called on checkbox change.
        set_func will be called with the checkbox itself as first parameter,
        emulating a method call (with self as first parameter)."""
        super().__init__(parent, *args, **kwargs)
        self.variable = tk.BooleanVar(value=value)
        self.checkbox = tk.Checkbutton(
            self, command=set_func, variable=self.variable
        )
        self.label = tk.Label(self, text=label)

        self.checkbox.pack(side=tk.LEFT)
        self.label.pack(side=tk.LEFT)


class TkinterUIMenus(tk.Menu):
    def __init__(self, tkinterui: TkinterUI, parent):
        self._tkinterui = tkinterui
        super().__init__(parent)

        parent.config(menu=self)

        # FILE MENU
        self.file_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="File", menu=self.file_menu, underline=0)

        self.file_menu.add_command(
            label="New...",
            command=lambda: events.post(Event.REQUEST_NEW_FILE),
        )
        self.file_menu.add_command(
            label="Open...",
            command=lambda: events.post(Event.FILE_REQUEST_TO_OPEN),
            underline=0,
        )
        self.file_menu.add_command(
            label="Save",
            command=lambda: events.post(Event.FILE_REQUEST_TO_SAVE, save_as=False),
            accelerator="Ctrl+S",
            underline=0,
        )
        self.file_menu.add_command(
            label="Save as...",
            command=lambda: events.post(Event.FILE_REQUEST_TO_SAVE, save_as=True),
            accelerator="Ctrl+Shift+S",
            underline=5,
        )
        self.file_menu.add_command(
            label="Load media file...",
            underline=0,
            command=lambda: events.post(Event.MENU_OPTION_FILE_LOAD_MEDIA),
        )
        self.file_menu.add_separator()

        self.file_menu.add_command(
            label="Media metadata...",
            command=lambda: events.post(Event.UI_REQUEST_WINDOW_METADATA),
            underline=0
        )

        # EDIT MENU
        self.edit_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="Edit", menu=self.edit_menu, underline=0)

        self.edit_menu.add_command(
            label="Undo",
            command=lambda: events.post(Event.REQUEST_TO_UNDO),
            underline=0,
            accelerator="Ctrl + Z"
        )
        self.edit_menu.add_command(
            label="Redo",
            command=lambda: events.post(Event.REQUEST_TO_REDO),
            underline=0,
            accelerator="Ctrl + Y"
        )

        # self.edit_menu.add_command(label='Clear timeline', command=event_handlers.on_cleartimeline, underline=0)

        # TIMELINES MENU
        self.timelines_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="Timelines", menu=self.timelines_menu, underline=0)

        self.timelines_menu.add_timelines = tk.Menu(self.timelines_menu, tearoff=0)

        for kind in TimelineKind:
            self.timelines_menu.add_timelines.add_command(
                label=kind.value.capitalize(),
                command=lambda kind_=kind: events.post(
                    Event.APP_ADD_TIMELINE, kind_
                ),
                underline=0,
            )

        self.timelines_menu.add_cascade(
            label="Add...",
            menu=self.timelines_menu.add_timelines,
            underline=0,
        )

        self.timelines_menu.add_command(
            label="Manage...",
            underline=0,
            command=lambda: events.post(Event.UI_REQUEST_WINDOW_MANAGE_TIMELINES),
        )

        self.timelines_menu.add_command(
            label="Clear all",
            underline=0,
            command=lambda: events.post(Event.TIMELINES_REQUEST_TO_CLEAR_ALL_TIMELINES),
            state="disabled",
        )

        # VIEW MENU
        self.view_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="View", menu=self.view_menu, underline=0)
        self.view_window_menu = tk.Menu(self.view_menu, tearoff=0)
        self.view_menu.add_cascade(
            label="Window", menu=self.view_window_menu, underline=0
        )
        self.view_window_menu.add_command(
            label="Inspect",
            command=lambda: events.post(Event.UI_REQUEST_WINDOW_INSPECTOR),
            underline=0,
        )
        self.view_menu.add_separator()
        self.view_menu.add_command(
            label="Zoom in",
            accelerator="Ctrl + +",
            command=lambda: events.post(Event.REQUEST_ZOOM_IN),
        )
        self.view_menu.add_command(
            label="Zoom out",
            accelerator="Ctrl + -",
            command=lambda: events.post(Event.REQUEST_ZOOM_OUT),
        )

        # DEVELOPMENT WINDOW OPTION
        if globals_.DEVELOPMENT_MODE:
            self.view_window_menu.add_command(
                label="Development",
                command=lambda: events.post(Event.UI_REQUEST_WINDOW_DEVELOPMENT),
                underline=0,
            )

        # HELP MENU
        self.help_menu = tk.Menu(self, tearoff=0)
        self.add_cascade(label="Help", menu=self.help_menu, underline=0)
        self.help_menu.add_command(label="Help...", state="disabled", underline=0)
        self.help_menu.add_command(
            label="About...",
            underline=0,
            command=lambda: events.post(Event.UI_REQUEST_WINDOW_ABOUT),
            state="disabled",
        )

        class AboutWindow(AppWindow):
            def __init__(self):
                super(AboutWindow, self).__init__()
                self.title(f"{globals_.APP_NAME}")
                tk.Label(self, text=globals_.APP_NAME).pack()
                tk.Label(self, text=f"Version {globals_.VERSION}").pack()
                # TODO add licensing information
                tk.Label(self, text="Felipe Defensor").pack()
                tk.Label(self, text="https://github.com/FelipeDefensor/TiLiA").pack()


def get_curr_screen_geometry(root):
    """
    Workaround to get the size of the current screen in a multi-screen setup.

    Returns:
        geometry (str): The standard Tk geometry string.
            [width]x[height]+[left]+[top]
    """
    root.update_idletasks()
    root.attributes("-fullscreen", True)
    geometry = root.winfo_geometry()

    return geometry


def get_startup_geometry(root: tk.Tk()):
    """
    Uses get_curr_screen_geometry to return initial window size in tkinter's geometry format.
    """

    STARTUP_HEIGHT = 300

    root.update_idletasks()
    root.attributes("-fullscreen", True)
    screen_geometry = root.winfo_geometry()

    root.attributes("-fullscreen", False)

    screen_width = int(screen_geometry.split("x")[0])
    window_geometry = f"{screen_width - 50}x{STARTUP_HEIGHT}+18+10"

    return window_geometry


def set_startup_geometry(root):

    geometry = get_startup_geometry(root)
    root.overrideredirect(True)
    root.geometry(geometry)
    root.overrideredirect(False)