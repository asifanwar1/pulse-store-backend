from pydantic_core import to_jsonable_python

from pydantic_ai import ModelMessagesTypeAdapter
from pydantic_ai.messages import ModelMessage


def serialize_new_messages(messages: list[ModelMessage]) -> list[dict]:
    return to_jsonable_python(messages)


def deserialize_turns(turns: list[list[dict]]) -> list[ModelMessage]:
    """`turns` is every stored row's message_data, oldest first."""
    combined: list[dict] = [message for turn in turns for message in turn]
    if not combined:
        return []
    return ModelMessagesTypeAdapter.validate_python(combined)
