"""
Defines the Inspect class.
A window that allows the user to sse the relevant attributes of a TimelineComponent or its
UI.
"""

from __future__ import annotations

import logging
from tkinter import ttk
from typing import TYPE_CHECKING

import tkinter as tk
from tkinter.scrolledtext import ScrolledText

from tilia import events
from tilia.events import Event, subscribe, unsubscribe_from_all
from tilia.timelines.common import TimelineComponent
from tilia.ui.windows.exceptions import UniqueWindowDuplicate
from tilia.ui.windows.kinds import WindowKind

PADX = 5
PADY = 5


class Inspect:
    """
    A window that allows the user to sse the relevant attributes of a TimelineComponent or its UI.
    Listens for a inspectable element selected event and updates according to a dict send alongside it.
    Keeps track of selected inspectable and listens for a deselect inspectable event to allow for
    correct updating.
    """

    KIND = WindowKind.INSPECT

    def __init__(self, parent) -> None:

        subscribe(
            self,
            Event.INSPECTABLE_ELEMENT_SELECTED,
            self.on_timeline_component_selected,
        )
        subscribe(
            self,
            Event.INSPECTABLE_ELEMENT_DESELECTED,
            self.on_timeline_component_deselected,
        )

        self.inspected_objects_stack = []
        self.uicomplex_id = ""
        self.toplevel = tk.Toplevel(parent)
        self.toplevel.transient(parent)
        self.toplevel.title("Inspect")
        self.toplevel.protocol("WM_DELETE_WINDOW", self.destroy)
        self.toplevel.focus()

        self.currently_inspected_class = None
        self.field_widgets = None
        self.var_widgets = None
        self.inspector_frame = tk.Frame(self.toplevel)
        self.inspector_frame.pack()
        self.display_not_selected_frame()

        self.toplevel.bind(
            "<Escape>", lambda _: events.post(Event.REQUEST_FOCUS_TIMELINES)
        )
        events.post(Event.INSPECTOR_WINDOW_OPENED)

    def focus(self):
        self.toplevel.focus_set()

        if self.starting_focus_widget:
            self.starting_focus_widget.focus_set()
            self.starting_focus_widget.selection_range(0, tk.END)


    def destroy(self):
        unsubscribe_from_all(self)
        self.toplevel.destroy()
        events.post(Event.INSPECT_WINDOW_CLOSED)

    def display_not_selected_frame(self):
        tk.Label(
            self.inspector_frame,
            text="No object selected",
            font=("Helvetica", 16),
        ).pack(padx=PADX, pady=PADY)

    def on_timeline_component_selected(
        self,
        uicomplex_class: type(TimelineComponent),
        inspector_fields: tuple[str, str],
        inspector_values: dict[str:str],
        uicomplex_id: str,
    ):

        self.update_frame(uicomplex_class, inspector_fields)
        self.update_values(inspector_values, uicomplex_id)
        self.update_inspected_object_stack(
            uicomplex_class, inspector_fields, inspector_values, uicomplex_id
        )

    def update_inspected_object_stack(self, *uielement_args):
        if uielement_args not in self.inspected_objects_stack:
            self.inspected_objects_stack.append(uielement_args)

    def update_frame(
        self,
        uicomplex_class: type(TimelineComponent),
        inspector_fields: tuple[str, str],
    ):
        if uicomplex_class != self.currently_inspected_class:
            self.inspector_frame.destroy()
            self.inspector_frame = self.create_inspector_frame(inspector_fields)
            self.inspector_frame.pack(padx=5, pady=5, expand=True, fill=tk.X)
            self.currently_inspected_class = uicomplex_class

    def on_timeline_component_deselected(self, uicomplex_id: str):
        try:
            uicomplex_index = [
                self.inspected_objects_stack.index(obj)
                for obj in self.inspected_objects_stack
                if obj[-1] == uicomplex_id
            ][0]
        except IndexError:
            return

        self.inspected_objects_stack.pop(uicomplex_index)

        if self.inspected_objects_stack:
            (
                uicomplex_class,
                inspector_fields,
                inspector_values,
                uicomplex_id,
            ) = self.inspected_objects_stack[-1]

            self.update_frame(uicomplex_class, inspector_fields)
            self.update_values(inspector_values, uicomplex_id)
        else:
            self.clear_values()
            for _, widget in self.field_widgets.items():
                widget.config(state="disabled")

    def update_values(self, field_values: dict[str:str], uicomplex_id: str):
        self.uicomplex_id = uicomplex_id
        for field_name, value in field_values.items():
            try:
                widget = self.field_widgets[field_name]
            except KeyError:
                logging.warning(f"Inspect has no field named {field_name}")
                continue

            widget.config(state="normal")
            if type(widget) == tk.Label:
                widget.config(text=value)
            elif type(widget) == tk.Entry or type(widget) == ScrolledText:
                widget.delete(0, "end")
                widget.insert(0, value)
            else:
                raise TypeError(
                    f"Non recognized widget type {type(widget)} for inspector field."
                )

            if self.starting_focus_widget:
                self.starting_focus_widget.selection_range(0, tk.END)

    def clear_values(self):
        clearing_dict = {}
        for key in self.field_widgets.keys():
            clearing_dict[key] = ""

        self.update_values(clearing_dict, "id_cleared")

    def create_inspector_frame(self, field_tuples: tuple[str, str]):
        frame = tk.Frame(self.toplevel)
        widget1 = None
        widget2 = None
        self.starting_focus_widget = None
        self.field_widgets = {}
        self.var_widgets = {}

        for row, field_tuple in enumerate(field_tuples):
            field_name = field_tuple[0]
            field_kind = field_tuple[1]
            value_var = None
            if field_kind == "entry":

                label_and_entry = LabelAndEntry(frame, field_name)
                widget1 = label_and_entry.label
                widget2 = label_and_entry.entry
                value_var = label_and_entry.entry_var
                value_var.trace_add("write", self.on_entry_edited)
                if not self.starting_focus_widget:
                    self.starting_focus_widget = widget2

            elif field_kind == "label":
                widget1 = tk.Label(frame, text=f"{field_name}:")
                widget2 = tk.Label(frame)
            elif field_kind == "scrolled_text":
                label_and_scrolled_text = LabelAndScrolledText(frame, field_name)
                widget1 = label_and_scrolled_text.label
                widget2 = label_and_scrolled_text.scrolled_text
                if not self.starting_focus_widget:
                    self.starting_focus_widget = widget2
            elif field_kind == "separator":
                widget1 = tk.Label(frame, text=f"{field_name}")
                widget2 = ttk.Separator(frame, orient=tk.HORIZONTAL)

            widget1.grid(row=row, column=0, sticky=tk.W)
            widget2.grid(row=row, column=1, padx=5, pady=2, sticky=tk.EW)

            self.field_widgets[field_name] = widget2
            if value_var:
                self.var_widgets[str(value_var)] = field_name

            frame.columnconfigure(1, weight=1)

            if self.starting_focus_widget:
                self.starting_focus_widget.focus_set()

        return frame

    def on_entry_edited(self, var_name: str, *_):
        field_name = self.var_widgets[var_name]
        entry = self.field_widgets[field_name]
        events.post(
            Event.INSPECTOR_FIELD_EDITED, field_name, entry.get(), self.uicomplex_id
        )


class LabelAndEntry(tk.Frame):
    """Create a tk.Label(), tk.Entry() pair and a associated tk.StrVar()"""

    width = 32

    def __init__(self, parent, label, attr_to_link=None):
        super().__init__(parent)
        label_text = label + ":"
        self.label = tk.Label(parent, text=label_text)

        self.entry = tk.Entry(parent)
        self.entry_var = tk.StringVar()
        self.entry.config(textvariable=self.entry_var)

        self.linked_attr = attr_to_link


class LabelAndScrolledText:
    def __init__(self, parent, name, text: str = ""):
        self.label = tk.Label(parent, text=f"{name}:")
        self.scrolled_text = ScrolledText(parent, height=8, width=25)
        self.scrolled_text.insert(1.0, text)
        self.scrolled_text.edit_modified(False)
        # self.scrolled_text.bind("<<Modified>>", self.modify_scrolled_text)
