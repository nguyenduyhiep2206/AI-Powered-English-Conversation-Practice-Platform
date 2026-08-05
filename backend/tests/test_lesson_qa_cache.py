"""Tests for Lesson Q&A Redis cache key prefix."""

from app.services.lesson_qa_cache import cache_key, normalize_query
from app.services.tutor_rag_cache import cache_key as tutor_cache_key


def test_lesson_qa_cache_key_uses_prefix():
    q = normalize_query("  What does reservation mean? ")
    key = cache_key(q, [3, 1])
    assert key.startswith("lesson_qa:rag:")
    assert key != tutor_cache_key(q, [3, 1])


def test_lesson_qa_cache_key_changes_when_scope_changes():
    q = normalize_query("What does because mean?")
    before = cache_key(q, [270], scope=[(52, 4755)])
    after = cache_key(q, [270], scope=[(51, 4727)])
    assert before != after
    assert before.startswith("lesson_qa:rag:")
    assert after.startswith("lesson_qa:rag:")


def test_lesson_qa_cache_key_stable_for_same_scope():
    q = normalize_query("What does because mean?")
    a = cache_key(q, [270], scope=[(51, 4727), (48, 4626)])
    b = cache_key(q, [270], scope=[(48, 4626), (51, 4727)])
    assert a == b
