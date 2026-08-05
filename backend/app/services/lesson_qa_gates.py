from __future__ import annotations

_ACK = frozenset({
    "hi", "hello", "ok", "okay", "thanks", "thank you", "yeah", "yup",
})


def should_retrieve(content: str) -> bool:
    t = (content or "").strip()
    if not t:
        return False
    if len(t) < 8:
        return False
    if " ".join(t.lower().split()) in _ACK:
        return False
    return True
