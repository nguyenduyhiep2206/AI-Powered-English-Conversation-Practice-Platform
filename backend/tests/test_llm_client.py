from app.services.llm_client import parse_json_content


def test_parse_json_bo_fence_markdown():
    raw = '```json\n{"questions": []}\n```'
    assert parse_json_content(raw) == {"questions": []}


def test_parse_json_thuan():
    assert parse_json_content('{"a": 1}') == {"a": 1}
