from app.services.passage_text import strip_embedded_mcq_choice_blocks


def test_strip_numbered_choice_dump():
    body = (
        "Subject: Office Renovation\n\n"
        "The crew ------- (1) the lobby. ------- (2).\n\n"
        "(1)\n"
        "will have painted\n"
        "paints\n"
        "is painting\n"
        "will paint\n"
    )
    cleaned = strip_embedded_mcq_choice_blocks(body)
    assert "will have painted" not in cleaned
    assert "------- (1)" in cleaned
    assert "------- (2)" in cleaned


def test_strip_lettered_choice_dump():
    body = "Notice text here.\n\n(A) one\n(B) two\n(C) three\n(D) four\n"
    cleaned = strip_embedded_mcq_choice_blocks(body)
    assert cleaned == "Notice text here."


def test_strip_embedded_stem_prompts():
    body = (
        "To: All Staff\n"
        "From: Health Services\n"
        "Subject: Annual Check-ups\n\n"
        "If you have recently ------- (1) with a cold, please reschedule. "
        "------- (2). We appreciate your cooperation.\n\n"
        "(1) Which answer choice best completes the blank?\n"
        "(2) Which sentence best completes the blank?\n"
    )
    cleaned = strip_embedded_mcq_choice_blocks(body)
    assert "Which answer choice" not in cleaned
    assert "Which sentence" not in cleaned
    assert "------- (1)" in cleaned
    assert "------- (2)" in cleaned
    assert cleaned.endswith("cooperation.")
