"""Tests for SessionService."""

import uuid

import pytest

from app.models.schemas import Message, VizConfig
from app.services.session_service import SessionService


@pytest.fixture()
def session_service() -> SessionService:
    return SessionService(db_path=":memory:")


class TestCreateSession:
    def test_returns_string_uuid(self, session_service: SessionService):
        session_id = session_service.create_session()
        assert isinstance(session_id, str)
        # Should be a valid UUID
        uuid.UUID(session_id)


class TestGetSession:
    def test_returns_session_with_correct_id(self, session_service: SessionService):
        session_id = session_service.create_session()
        session = session_service.get_session(session_id)
        assert session is not None
        assert session.id == session_id

    def test_session_with_no_messages_has_empty_list(self, session_service: SessionService):
        session_id = session_service.create_session()
        session = session_service.get_session(session_id)
        assert session is not None
        assert session.messages == []


class TestAddMessage:
    def test_persists_messages(self, session_service: SessionService):
        session_id = session_service.create_session()
        msg = Message(role="user", content="Hello")
        session_service.add_message(session_id, msg)

        session = session_service.get_session(session_id)
        assert session is not None
        assert len(session.messages) == 1
        assert session.messages[0].role == "user"
        assert session.messages[0].content == "Hello"

    def test_messages_in_chronological_order(self, session_service: SessionService):
        session_id = session_service.create_session()
        session_service.add_message(session_id, Message(role="user", content="First"))
        session_service.add_message(session_id, Message(role="assistant", content="Second"))
        session_service.add_message(session_id, Message(role="user", content="Third"))

        session = session_service.get_session(session_id)
        assert session is not None
        assert [m.content for m in session.messages] == ["First", "Second", "Third"]


class TestListSessions:
    def test_returns_all_sessions(self, session_service: SessionService):
        session_service.create_session()
        session_service.create_session()
        session_service.create_session()

        result = session_service.list_sessions()
        assert len(result["sessions"]) == 3

    def test_returns_most_recent_first(self, session_service: SessionService):
        id1 = session_service.create_session()
        id2 = session_service.create_session()
        id3 = session_service.create_session()

        result = session_service.list_sessions()
        sessions = result["sessions"]
        assert sessions[0]["session_id"] == id3
        assert sessions[1]["session_id"] == id2
        assert sessions[2]["session_id"] == id1


class TestGetMessagesWindow:
    def test_returns_only_last_n_turns(self, session_service: SessionService):
        session_id = session_service.create_session()
        # Add 4 turns (8 messages)
        for i in range(4):
            session_service.add_message(session_id, Message(role="user", content=f"User {i}"))
            session_service.add_message(
                session_id, Message(role="assistant", content=f"Assistant {i}")
            )

        # Request 2 turns = last 4 messages
        window = session_service.get_messages_window(session_id, max_turns=2)
        assert len(window) == 4
        assert window[0].content == "User 2"
        assert window[1].content == "Assistant 2"
        assert window[2].content == "User 3"
        assert window[3].content == "Assistant 3"

    def test_fewer_messages_than_window_returns_all(self, session_service: SessionService):
        session_id = session_service.create_session()
        session_service.add_message(session_id, Message(role="user", content="Only one"))

        window = session_service.get_messages_window(session_id, max_turns=5)
        assert len(window) == 1
        assert window[0].content == "Only one"
