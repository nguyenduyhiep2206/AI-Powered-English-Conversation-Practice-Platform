from app.services.lesson_qa_gates import should_retrieve


def test_should_retrieve_skips_short_and_acks():
    assert should_retrieve("Hi") is False
    assert should_retrieve("ok") is False
    assert should_retrieve("thanks") is False
    assert should_retrieve("  ") is False


def test_should_retrieve_accepts_lesson_questions():
    assert should_retrieve("What does reservation mean?") is True
    assert should_retrieve("How do I use I'd like?") is True
