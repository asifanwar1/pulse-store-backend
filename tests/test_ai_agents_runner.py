from app.core.ai_agents.runner import _chunk_for_typing, _sanitize_reply

_LEAKED_TOOL_CALL_REPLY = (
    "I have the category id, sku availability, and image. I still need name, brand, "
    "retail price, cost price, stock quantity, and status. \n\n"
    "Name: Best Beauty Skin Care Product Set\nBrand: ?\nRetail Price: ?\nCost Price: ?\n"
    "Stock Quantity: ?\nStatus: DRAFT\n\n"
    "I have the category id, sku availability, and image. I still need name, brand, "
    "retail price, cost price, stock quantity, and status. \n\n"
    "Name: Best Beauty Skin Care Product Set\nBrand: ?\nRetail Price: ?\nCost Price: ?\n"
    "Stock Quantity: ?\nStatus: DRAFT\n\n"
    '<function=list_categories={"search":null}></function>'
)


def test_sanitize_reply_strips_leaked_tool_call_and_collapses_duplicate():
    cleaned = _sanitize_reply(_LEAKED_TOOL_CALL_REPLY)

    assert "<function=" not in cleaned
    assert cleaned.count("I have the category id") == 1
    assert cleaned.endswith("Status: DRAFT")


def test_sanitize_reply_leaves_normal_replies_untouched():
    reply = "Thanks! The product has been created as a draft."
    assert _sanitize_reply(reply) == reply


def test_sanitize_reply_does_not_touch_short_coincidental_repeats():
    reply = "ok ok"
    assert _sanitize_reply(reply) == reply


def test_chunk_for_typing_reassembles_to_the_original_text():
    text = "A reasonably long reply that should be split into a few pieces for replay."
    assert "".join(_chunk_for_typing(text)) == text
