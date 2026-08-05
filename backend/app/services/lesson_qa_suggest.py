def build_suggested_prompts(
    *,
    skill_title: str,
    objective: str | None,
    targets: list[str],
    max_n: int = 5,
) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()

    def add(s: str) -> None:
        t = " ".join(s.split())
        key = t.lower()
        if not t or key in seen or len(out) >= max_n:
            return
        seen.add(key)
        out.append(t)

    for surface in targets[:3]:
        s = (surface or "").strip()
        if s:
            add(f'What does "{s}" mean?')
            add(f'How do I use "{s}"?')
    title = (skill_title or "this lesson").strip() or "this lesson"
    add(f"Give an example sentence for {title}.")
    if objective and objective.strip():
        add(f"Can you explain: {objective.strip()}?")
    add(f"What should I practice in {title}?")
    # Ensure at least 3
    fallbacks = [
        f"What is the main point of {title}?",
        f"Common mistakes with {title}?",
        f"Give me two useful phrases for {title}.",
    ]
    for f in fallbacks:
        add(f)
        if len(out) >= 3:
            break
    return out[:max_n]
