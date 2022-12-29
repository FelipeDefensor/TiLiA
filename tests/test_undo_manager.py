from unittest.mock import MagicMock, patch

import pytest

from tilia.events import Event, unsubscribe_from_all
from tilia.timelines.state_actions import StateAction
from tilia.undo_manager import UndoManager


@pytest.fixture
def um():
    _um = UndoManager()
    _um.record(
        "state0", StateAction.FILE_LOAD
    )  # simulate the fact that there will always be this record at the bootom of the stack
    yield _um
    unsubscribe_from_all(_um)


@patch("tilia.events.post")
class TestUndoManager:
    def test_constructor(self, _):
        um = UndoManager()
        unsubscribe_from_all(um)

    def test_record_state(self, _, um):
        um.record("state1", "action1")

        assert um.stack == [
            {"state": "state0", "action": StateAction.FILE_LOAD},
            {"state": "state1", "action": "action1"},
        ]

    def test_record_two_states(self, _, um):
        um.record("state1", "action1")
        um.record("state2", "action2")

        assert um.stack == [
            {"state": "state0", "action": StateAction.FILE_LOAD},
            {"state": "state1", "action": "action1"},
            {"state": "state2", "action": "action2"},
        ]

    def test_record_successive_no_repeat_states_with_same_id(self, _, um):
        um.record("state1", "action1", no_repeat=True, repeat_identifier=":||")
        um.record("state2", "action2", no_repeat=True, repeat_identifier=":||")

        assert len(um.stack) == 2
        assert um.stack[-1]["state"] == "state2"

    def test_record_successive_no_repeat_states_with_different_ids(self, _, um):
        um.record("state1", "action1", no_repeat=True, repeat_identifier=":||")
        um.record("state2", "action2", no_repeat=True, repeat_identifier="||")

        assert len(um.stack) == 3

    def test_undo(self, post_mock: MagicMock, um):
        um.record("state1", "action1")

        um.undo()

        assert um.current_state_index == -2
        post_mock.assert_called_with(Event.REQUEST_RESTORE_APP_STATE, "state0")

    def test_undo_no_action_to_undo(self, post_mock, um):
        um.undo()
        post_mock.assert_not_called()

    def test_undo_twice(self, post_mock, um):
        um.record("state1", "action1")
        um.record("state2", "action2")

        um.undo()
        um.undo()

        assert um.current_state_index == -3
        post_mock.assert_called_with(Event.REQUEST_RESTORE_APP_STATE, "state0")

    def test_redo(self, post_mock, um):
        um.record("state1", "action1")

        um.undo()
        um.redo()

        assert um.current_state_index == -1
        post_mock.assert_called_with(Event.REQUEST_RESTORE_APP_STATE, "state1")

    def test_redo_no_actions_to_redo(self, post_mock, um):
        um.record("state1", "action1")

        um.undo()
        um.redo()
        um.redo()

        assert um.current_state_index == -1
        post_mock.assert_called_with(Event.REQUEST_RESTORE_APP_STATE, "state1")

    def test_redo_twice(self, post_mock, um):
        um.record("state1", "action1")
        um.record("state2", "action2")

        um.undo()
        um.undo()
        um.redo()
        um.redo()

        assert um.current_state_index == -1
        post_mock.assert_called_with(Event.REQUEST_RESTORE_APP_STATE, "state2")

    def test_alternate_undo_and_redo(self, post_mock, um):
        um.record("state1", "action1")
        um.record("state2", "action2")

        um.undo()
        um.redo()
        um.undo()
        um.redo()

        assert um.current_state_index == -1
        post_mock.assert_called_with(Event.REQUEST_RESTORE_APP_STATE, "state2")

    def test_undo_then_record(self, post_mock, um):
        um.record("state1", "action1")
        um.record("state2", "action2")

        um.undo()

        um.record("state3", "action3")

        assert um.stack == [
            {"state": "state0", "action": StateAction.FILE_LOAD},
            {"state": "state1", "action": "action1"},
            {"state": "state3", "action": "action3"},
        ]

    def test_undo_redo_then_record(self, post_mock, um):
        um.record("state1", "action1")
        um.record("state2", "action2")
        um.record("state3", "action3")

        um.undo()
        um.undo()
        um.redo()

        um.record("state4", "action4")

        assert um.stack == [
            {"state": "state0", "action": StateAction.FILE_LOAD},
            {"state": "state1", "action": "action1"},
            {"state": "state2", "action": "action2"},
            {"state": "state4", "action": "action4"},
        ]
