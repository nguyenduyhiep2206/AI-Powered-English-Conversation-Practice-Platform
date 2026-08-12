#!/usr/bin/env python3
"""Build A2–C1 Core Inventory skill catalogs (run manually; writes jsonl + summaries)."""

from __future__ import annotations

import json
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any

OUT = Path(__file__).resolve().parent


def skill(
    slug: str,
    title: str,
    level: str,
    stype: str,
    diff: int,
    refs: list[str],
    notes: str | None = None,
) -> dict[str, Any]:
    assert len(title) <= 60, title
    assert 1 <= diff <= 10
    obj: dict[str, Any] = {
        "slug": slug,
        "title": title,
        "cefr_level": level,
        "skill_type": stype,
        "difficulty_in_level": diff,
        "source_refs": refs,
    }
    if notes:
        obj["notes"] = notes
    return obj


def edge(frm: str, to: str) -> dict[str, str]:
    return {"from_slug": frm, "to_slug": to, "relation": "prerequisite"}


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n",
        encoding="utf-8",
    )


def validate(
    skills: list[dict[str, Any]], edges: list[dict[str, str]], *, label: str
) -> dict[str, Any]:
    by = {s["slug"]: s for s in skills}
    assert len(by) == len(skills), "duplicate slugs"
    dangling = [
        e
        for e in edges
        if e["from_slug"] not in by or e["to_slug"] not in by
    ]
    g: dict[str, list[str]] = defaultdict(list)
    indeg = Counter({s["slug"]: 0 for s in skills})
    for e in edges:
        g[e["from_slug"]].append(e["to_slug"])
        indeg[e["to_slug"]] += 1
    q = deque([n for n, d in indeg.items() if d == 0])
    seen = 0
    while q:
        n = q.popleft()
        seen += 1
        for m in g[n]:
            indeg[m] -= 1
            if indeg[m] == 0:
                q.append(m)
    acyclic = seen == len(skills)
    inversions = []
    for e in edges:
        fd = by[e["from_slug"]]["difficulty_in_level"]
        td = by[e["to_slug"]]["difficulty_in_level"]
        if fd > td:
            inversions.append((e["from_slug"], fd, e["to_slug"], td))
    touched: set[str] = set()
    for e in edges:
        touched.add(e["from_slug"])
        touched.add(e["to_slug"])
    isolated = sorted(s["slug"] for s in skills if s["slug"] not in touched)
    types = Counter(s["skill_type"] for s in skills)
    n = len(skills)
    return {
        "label": label,
        "ok": (
            acyclic
            and not inversions
            and not dangling
            and not isolated
            and 45 <= n <= 65
            and types.get("reading", 0) >= 1
        ),
        "nodes": n,
        "edges": len(edges),
        "acyclic": acyclic,
        "topo": f"{seen}/{n}",
        "inversions": inversions,
        "dangling": dangling,
        "isolated": isolated,
        "types": dict(types),
        "reading": types.get("reading", 0),
    }


def report_validation(r: dict[str, Any]) -> str:
    inv = (
        "none"
        if not r["inversions"]
        else "\n".join(
            f"- `{a}` ({da}) → `{b}` ({db})" for a, da, b, db in r["inversions"]
        )
    )
    return f"""# Self-validation — {r['label']}

| Check | Result |
|-------|--------|
| Acyclic | {"PASS" if r['acyclic'] else "FAIL"} ({r['topo']}) |
| No inversions | {"PASS" if not r['inversions'] else "FAIL"} |
| No dangling slugs | {"PASS" if not r['dangling'] else "FAIL"} |
| No isolated nodes | {"PASS" if not r['isolated'] else "FAIL"} |
| Node count 45–65 | {"PASS" if 45 <= r['nodes'] <= 65 else "FAIL"} ({r['nodes']}) |
| ≥1 reading | {"PASS" if r['reading'] >= 1 else "FAIL"} |
| **Overall** | **{"PASS" if r['ok'] else "FAIL"}** |

## Counts
- nodes: {r['nodes']}
- edges: {r['edges']}
- skill_type: {r['types']}

## Inversions
{inv}

## Isolated
{r['isolated'] if r['isolated'] else 'none'}

## Dangling
{r['dangling'] if r['dangling'] else 'none'}
"""


# ---------------------------------------------------------------------------
# A2
# ---------------------------------------------------------------------------

def build_a2() -> tuple[list[dict], list[dict], list[dict], str]:
    L = "A2"
    skills = [
        # foundations / recycle with A2 focus
        skill("questions_a2", "Questions (A2 expansion)", L, "grammar", 1, ["poster:A2", "essential:grammar"], "Poster A2 Questions"),
        skill("adverbs_frequency_a2", "Adverbs of frequency (A2)", L, "grammar", 2, ["poster:A2", "essential:grammar"]),
        skill("articles_countable_uncountable", "Articles with countable/uncountable nouns", L, "grammar", 2, ["poster:A2", "essential:grammar"]),
        skill("adjectives_comparative_a2", "Comparative adjectives (than + definite article)", L, "grammar", 2, ["poster:A2"], "Scaffold retained"),
        skill("prepositional_phrases_a2", "Prepositional phrases (place/time/movement)", L, "grammar", 2, ["poster:A2", "essential:grammar"], "Includes 'Prepositions of time: on/in/at' from the A2 poster, taught together with place/movement prepositional phrases."),
        skill("directions_a2", "Asking for and giving directions (A2)", L, "functional", 3, ["poster:A2"], "Scaffold retained; expands A1 directions"),
        skill("adjectives_superlative_a2", "Superlative adjectives (the…)", L, "grammar", 3, ["poster:A2", "essential:grammar"]),
        skill("countables_much_many", "Countables/uncountables with much/many", L, "grammar", 3, ["poster:A2", "essential:grammar"]),
        skill("possessives_extended_a2", "Possessives ('s / s')", L, "grammar", 3, ["poster:A2", "essential:grammar"]),
        skill("going_to_a2", "Going to (plans & evidence)", L, "grammar", 3, ["poster:A2", "essential:grammar"]),
        skill("modals_can_could_a2", "Can / could (A2)", L, "grammar", 3, ["poster:A2", "essential:grammar"]),
        skill("past_simple_a2", "Past simple (A2 consolidation)", L, "grammar", 3, ["poster:A2", "essential:grammar"]),
        skill("vocab_colours_clothes", "Colours and clothes", L, "vocabulary", 3, ["poster:A2", "appendixE:173-174"], "Scaffold; relocated from A1"),
        skill("vocab_travel_services", "Travel and services vocabulary", L, "vocabulary", 4, ["poster:A2", "appendixE:171"], "Scaffold; relocated from A1"),
        skill("vocab_ways_travelling", "Ways of travelling", L, "vocabulary", 4, ["appendixE:176", "poster:A2"]),
        # mid
        skill("will_future", "Will (decisions & predictions)", L, "grammar", 4, ["poster:A2", "essential:grammar"]),
        skill("present_continuous_future", "Present continuous for future", L, "grammar", 4, ["poster:A2", "essential:grammar", "appendixE:75"], "Plain present continuous is recycled from A1; this node covers the A2-specific future-use extension only."),
        skill("wh_questions_past", "Wh- questions in the past", L, "grammar", 4, ["poster:A2", "essential:grammar"]),
        skill("adverbial_phrases_word_order", "Adverbial phrases & word order", L, "grammar", 4, ["poster:A2", "essential:grammar"]),
        skill("describing_people", "Describing people", L, "functional", 4, ["poster:A2", "essential:functions", "appendixE:10"]),
        skill("describing_things", "Describing things", L, "functional", 4, ["poster:A2", "essential:functions", "appendixE:11"]),
        skill("requests_a2", "Making requests", L, "functional", 4, ["poster:A2", "essential:functions", "appendixE:12"]),
        skill("vocab_food_drink_a2", "Food and drink (A2)", L, "vocabulary", 4, ["poster:A2", "essential:vocabulary"]),
        skill("vocab_town_shops_a2", "Town, shops and shopping (A2)", L, "vocabulary", 4, ["poster:A2", "essential:vocabulary"]),
        skill("reading_short_info_texts", "Reading short informational texts", L, "reading", 5, ["poster:A2"], "Brochures/leaflets/websites; A2 scenario texts"),
        skill("going_to_vs_will", "Going to vs will", L, "grammar", 5, ["poster:A2", "essential:grammar"]),
        skill("past_continuous", "Past continuous", L, "grammar", 5, ["poster:A2", "essential:grammar"]),
        skill("gerunds", "Gerunds", L, "grammar", 5, ["poster:A2", "essential:grammar"]),
        skill("modals_have_to", "Have to / don't have to", L, "grammar", 5, ["poster:A2", "essential:grammar", "appendixE:113"]),
        skill("modals_should", "Should (advice)", L, "grammar", 5, ["poster:A2", "essential:grammar", "appendixE:115"]),
        skill("describing_places", "Describing places", L, "functional", 5, ["poster:A2", "essential:functions", "appendixE:19"]),
        skill("describing_habits_routines_a2", "Describing habits and routines (A2)", L, "functional", 5, ["poster:A2", "essential:functions", "appendixE:9"]),
        skill("suggestions", "Making suggestions", L, "functional", 6, ["poster:A2", "essential:functions", "appendixE:13"]),
        skill("advice", "Giving advice", L, "functional", 6, ["poster:A2", "appendixE:14"]),
        skill("vocab_personality_feelings", "Adjectives: personality, description, feelings", L, "vocabulary", 5, ["poster:A2", "essential:vocabulary"]),
        skill("vocab_hobbies_leisure_a2", "Hobbies and leisure (A2)", L, "vocabulary", 5, ["poster:A2", "essential:topics"]),
        skill("verb_ing_or_infinitive", "Verb + -ing / infinitive (like, want)", L, "grammar", 5, ["poster:A2", "essential:grammar"]),
        skill("phrasal_verbs_common", "Common phrasal verbs", L, "grammar", 6, ["poster:A2", "essential:grammar"]),
        skill("linkers_sequential_past", "Sequential past linkers (first, then, finally)", L, "grammar", 6, ["poster:A2", "essential:discourse", "appendixE:48"], "discourse"),
        skill("obligation_necessity", "Talking about obligation and necessity", L, "functional", 6, ["poster:A2", "essential:functions", "appendixE:18"]),
        skill("invitations_offers", "Invitations and offers", L, "functional", 6, ["poster:A2", "appendixE:15-16"]),
        skill("arrangements_meeting", "Making arrangements to meet", L, "functional", 6, ["poster:A2", "appendixE:17"]),
        skill("vocab_holidays_a2", "Holidays (A2)", L, "vocabulary", 6, ["poster:A2", "essential:topics"]),
        skill("vocab_work_jobs_a2", "Work and jobs (A2)", L, "vocabulary", 6, ["poster:A2", "essential:topics"]),
        skill("vocab_education", "Education vocabulary", L, "vocabulary", 6, ["poster:A2", "essential:topics"]),
        skill("present_perfect_basic", "Present perfect (experience / just)", L, "grammar", 7, ["poster:A2", "essential:grammar", "appendixE:81"]),
        skill("describing_past_experiences", "Describing past experiences & storytelling", L, "functional", 7, ["poster:A2", "essential:functions", "appendixE:20"]),
        skill("zero_first_conditional", "Zero and first conditional", L, "grammar", 7, ["poster:A2", "essential:grammar"]),
        skill("imperatives_a2", "Imperatives (A2 instructions)", L, "grammar", 2, ["poster:A2", "essential:grammar"]),
        skill("vocab_shopping_a2", "Shopping language (A2)", L, "vocabulary", 5, ["poster:A2", "essential:topics"], "Topic Shopping; overlaps town/shops"),
    ]

    edges = [
        edge("questions_a2", "adverbs_frequency_a2"),
        edge("questions_a2", "modals_can_could_a2"),
        edge("questions_a2", "requests_a2"),
        edge("articles_countable_uncountable", "countables_much_many"),
        edge("adjectives_comparative_a2", "adjectives_superlative_a2"),
        edge("adjectives_comparative_a2", "vocab_colours_clothes"),
        edge("adjectives_comparative_a2", "describing_people"),
        edge("adjectives_superlative_a2", "describing_places"),
        edge("directions_a2", "vocab_travel_services"),
        edge("directions_a2", "vocab_town_shops_a2"),
        edge("going_to_a2", "will_future"),
        edge("going_to_a2", "present_continuous_future"),
        edge("will_future", "going_to_vs_will"),
        edge("present_continuous_future", "going_to_vs_will"),
        edge("present_continuous_future", "arrangements_meeting"),
        edge("modals_can_could_a2", "requests_a2"),
        edge("modals_can_could_a2", "suggestions"),
        edge("past_simple_a2", "wh_questions_past"),
        edge("past_simple_a2", "past_continuous"),
        edge("wh_questions_past", "describing_past_experiences"),
        edge("past_continuous", "describing_past_experiences"),
        edge("past_simple_a2", "linkers_sequential_past"),
        edge("linkers_sequential_past", "describing_past_experiences"),
        edge("prepositional_phrases_a2", "directions_a2"),
        edge("prepositional_phrases_a2", "adverbial_phrases_word_order"),
        edge("adverbs_frequency_a2", "describing_habits_routines_a2"),
        edge("adverbial_phrases_word_order", "describing_habits_routines_a2"),
        edge("gerunds", "verb_ing_or_infinitive"),
        edge("verb_ing_or_infinitive", "suggestions"),
        edge("modals_have_to", "obligation_necessity"),
        edge("modals_should", "advice"),
        edge("modals_should", "obligation_necessity"),
        edge("countables_much_many", "vocab_food_drink_a2"),
        edge("vocab_colours_clothes", "describing_things"),
        edge("describing_people", "vocab_personality_feelings"),
        edge("vocab_personality_feelings", "describing_places"),
        edge("vocab_travel_services", "vocab_ways_travelling"),
        edge("vocab_ways_travelling", "vocab_holidays_a2"),
        edge("vocab_hobbies_leisure_a2", "describing_habits_routines_a2"),
        edge("vocab_education", "vocab_work_jobs_a2"),
        edge("vocab_town_shops_a2", "vocab_shopping_a2"),
        edge("vocab_shopping_a2", "reading_short_info_texts"),
        edge("past_simple_a2", "present_perfect_basic"),
        edge("present_perfect_basic", "describing_past_experiences"),
        edge("advice", "zero_first_conditional"),
        edge("modals_should", "zero_first_conditional"),
        edge("questions_a2", "imperatives_a2"),
        edge("imperatives_a2", "directions_a2"),
        edge("requests_a2", "invitations_offers"),
        edge("suggestions", "invitations_offers"),
        edge("invitations_offers", "arrangements_meeting"),
        edge("possessives_extended_a2", "describing_people"),
        edge("phrasal_verbs_common", "describing_past_experiences"),
        edge("past_simple_a2", "phrasal_verbs_common"),
        edge("vocab_holidays_a2", "describing_past_experiences"),
        edge("vocab_work_jobs_a2", "obligation_necessity"),
        edge("describing_things", "reading_short_info_texts"),
        edge("going_to_vs_will", "arrangements_meeting"),
    ]

    bridges = [
        edge("past_simple", "past_simple_a2"),
        edge("going_to", "going_to_a2"),
        edge("comparatives_superlatives", "adjectives_comparative_a2"),
        edge("directions", "directions_a2"),
        edge("can_cant", "modals_can_could_a2"),
        edge("present_continuous", "present_continuous_future"),
        edge("questions_basic", "questions_a2"),
        # Fix 5 — same-construct progressions A1→A2
        edge("describing_habits_routines", "describing_habits_routines_a2"),
        edge("vocab_holidays", "vocab_holidays_a2"),
        edge("imperatives", "imperatives_a2"),
        edge("vocab_food_drink", "vocab_food_drink_a2"),
        edge("vocab_hobbies_leisure", "vocab_hobbies_leisure_a2"),
        edge("adverbs_frequency", "adverbs_frequency_a2"),
        edge("vocab_town_shops", "vocab_town_shops_a2"),
        edge("vocab_work_jobs", "vocab_work_jobs_a2"),
    ]

    summary = """# Core Inventory A2 skill catalog

**Sources:** Essential Guide A2 column; Poster A2; Appendix D/E (A2).  
**Scaffold incorporated:** `vocab_travel_services`, `vocab_colours_clothes`, `adjectives_comparative_a2`, `directions_a2`.

## Counts
See `self_validation_a2.md`.

## Merges
- Shopping topic + town/shops practice → `vocab_shopping_a2` + `vocab_town_shops_a2`
- Invitations + offers → `invitations_offers`
- Food/drink A2 listed separately from A1 node (level-scoped slug `*_a2`)
- Discourse sequential past linkers → grammar node `linkers_sequential_past`

## Omissions / deferred
- Exact duplicate listing of A1-only items not re-created as new A2 teaching targets unless Essential A2 column lists them (e.g. basic *to be*)
- Dimension adjectives (Appendix E 175) MERGED into `describing_things` / `vocab_colours_clothes`
- Full phrasal-verb inventory beyond “common” OMITTED (single teachable node)
"""
    return skills, edges, bridges, summary


# ---------------------------------------------------------------------------
# B1
# ---------------------------------------------------------------------------

def build_b1() -> tuple[list[dict], list[dict], list[dict], str]:
    L = "B1"
    skills = [
        skill("adverbs_range_b1", "Adverbs (broader range)", L, "grammar", 2, ["poster:B1", "essential:grammar"]),
        skill("intensifiers_too_enough", "Intensifiers too / enough", L, "grammar", 2, ["poster:B1", "essential:grammar"]),
        skill("comparatives_superlatives_b1", "Comparatives & superlatives (B1)", L, "grammar", 2, ["poster:B1", "essential:grammar"]),
        skill("connecting_cause_effect", "Connectors: cause, effect, contrast", L, "grammar", 3, ["poster:B1", "essential:grammar"], "discourse-adjacent"),
        skill("modals_must_have_to", "Must / have to", L, "grammar", 3, ["poster:B1", "essential:grammar"]),
        skill("modals_might_may_probably", "Might / may / will probably", L, "grammar", 3, ["poster:B1", "essential:grammar"]),
        skill("past_simple_b1", "Past simple (B1 narrative)", L, "grammar", 3, ["poster:B1", "essential:grammar"]),
        skill("past_continuous_b1", "Past continuous (B1)", L, "grammar", 3, ["poster:B1", "essential:grammar"]),
        skill("present_perfect_b1", "Present perfect (B1 expansion)", L, "grammar", 4, ["poster:B1", "essential:grammar"]),
        skill("present_perfect_vs_past", "Present perfect vs past simple", L, "grammar", 5, ["poster:B1", "essential:grammar"]),
        skill("present_perfect_continuous", "Present perfect continuous", L, "grammar", 6, ["poster:B1", "essential:grammar"]),
        skill("future_continuous", "Future continuous", L, "grammar", 5, ["poster:B1", "essential:grammar"]),
        skill("will_going_to_prediction", "Will & going to for prediction", L, "grammar", 4, ["poster:B1", "essential:grammar"]),
        skill("modals_must_cant_deduction", "Must / can't (deduction)", L, "grammar", 6, ["poster:B1", "essential:grammar"]),
        skill("modals_should_might_have", "Should have / might have", L, "grammar", 8, ["poster:B1", "essential:grammar"]),
        skill("conditionals_2nd_3rd", "Second and third conditionals", L, "grammar", 7, ["poster:B1", "essential:grammar"]),
        skill("complex_question_tags", "Complex question tags", L, "grammar", 5, ["poster:B1", "essential:grammar"]),
        skill("wh_questions_past_b1", "Wh- questions in the past (B1)", L, "grammar", 3, ["poster:B1", "essential:grammar"]),
        skill("simple_passive", "Simple passive", L, "grammar", 6, ["poster:B1", "essential:grammar"]),
        skill("reported_speech_range", "Reported speech (range of tenses)", L, "grammar", 8, ["poster:B1", "essential:grammar"]),
        skill("phrasal_verbs_extended", "Phrasal verbs (extended)", L, "grammar", 6, ["poster:B1", "essential:grammar"]),
        skill("past_perfect", "Past perfect", L, "grammar", 7, ["poster:B1", "essential:grammar"]),
        skill("linkers_sequential_past_b1", "Sequential past linkers (B1)", L, "grammar", 4, ["poster:B1", "essential:discourse"], "discourse"),
        skill("checking_understanding", "Checking understanding", L, "functional", 2, ["poster:B1", "essential:functions"]),
        skill("initiating_closing_conversation", "Initiating and closing conversation", L, "functional", 2, ["poster:B1", "essential:functions"]),
        skill("managing_interaction", "Managing interaction (interrupt/change topic)", L, "functional", 4, ["poster:B1", "essential:functions"]),
        skill("expressing_opinions", "Expressing opinions; agreeing/disagreeing", L, "functional", 4, ["poster:B1", "essential:functions"]),
        skill("opinion_justification", "Giving opinions with justification", L, "functional", 5, ["poster:B1", "essential:functions"], "Early spiral introduction; full B2 treatment is opinion_justification_b2."),
        skill("describing_experiences_events", "Describing experiences and events", L, "functional", 6, ["poster:B1", "essential:functions"]),
        skill("describing_feelings_emotion", "Describing feelings and emotion", L, "functional", 4, ["poster:B1", "essential:functions"]),
        skill("describing_places_b1", "Describing places (B1)", L, "functional", 3, ["poster:B1", "essential:functions"]),
        skill("interacting_informally", "Interacting informally (interest/sympathy)", L, "functional", 5, ["poster:B1", "essential:functions"], "Early spiral introduction; full B2 treatment is interacting_informally_b2."),
        skill("speculating_b1", "Speculating", L, "functional", 6, ["poster:B1", "essential:functions"], "Early spiral introduction; full B2 treatment is speculating_b2."),
        skill("taking_initiative_interaction", "Taking the initiative in interaction", L, "functional", 6, ["poster:B1", "essential:functions"], "Early spiral introduction; full B2 treatment is taking_initiative_b2."),
        skill("synthesizing_glossing_info", "Synthesizing / evaluating / glossing info", L, "functional", 8, ["poster:B1", "essential:functions"], "Early spiral introduction; full B2 treatment is synthesizing_info_b2."),
        skill("expressing_reaction", "Expressing reaction (e.g. indifference)", L, "functional", 5, ["poster:B1", "essential:functions"], "Early spiral introduction; full B2 treatment is expressing_reaction_b2."),
        skill("vocab_collocation_b1", "Collocation (familiar topics)", L, "vocabulary", 4, ["poster:B1", "essential:vocabulary"]),
        skill("vocab_colloquial_b1", "Colloquial language (B1)", L, "vocabulary", 5, ["poster:B1", "essential:vocabulary"]),
        skill("vocab_town_shops_b1", "Town, shops and shopping (B1)", L, "vocabulary", 3, ["poster:B1", "essential:vocabulary"]),
        skill("vocab_travel_services_b1", "Travel and services (B1)", L, "vocabulary", 3, ["poster:B1", "essential:vocabulary"]),
        skill("vocab_books_literature", "Books and literature", L, "vocabulary", 6, ["poster:B1", "essential:topics"]),
        skill("vocab_education_b1", "Education (B1)", L, "vocabulary", 4, ["poster:B1", "essential:topics"]),
        skill("vocab_film", "Film vocabulary", L, "vocabulary", 5, ["poster:B1", "essential:topics"]),
        skill("vocab_leisure_b1", "Leisure activities (B1)", L, "vocabulary", 3, ["poster:B1", "essential:topics"]),
        skill("vocab_media_b1", "Media vocabulary", L, "vocabulary", 6, ["poster:B1", "essential:topics"]),
        skill("vocab_news_lifestyles", "News, lifestyles and current affairs", L, "vocabulary", 7, ["poster:B1", "essential:topics"]),
        skill("reading_factual_articles", "Reading straightforward factual texts", L, "reading", 7, ["poster:B1"], "B1 reading can-do: main points of factual texts"),
        skill("past_tense_responses", "Past tense responses", L, "grammar", 4, ["poster:B1", "essential:grammar"]),
        skill("used_to_b1", "Used to", L, "grammar", 5, ["appendixD", "appendixE:69"], "Common B1 narrative; Appendix E B1 area"),
        skill("vocab_feelings_extended", "Feelings & attitudes lexis", L, "vocabulary", 5, ["poster:B1"], "Supports describing feelings/emotion"),
    ]

    edges = [
        edge("checking_understanding", "initiating_closing_conversation"),
        edge("initiating_closing_conversation", "managing_interaction"),
        edge("managing_interaction", "taking_initiative_interaction"),
        edge("expressing_opinions", "opinion_justification"),
        edge("expressing_opinions", "expressing_reaction"),
        edge("opinion_justification", "interacting_informally"),
        edge("adverbs_range_b1", "intensifiers_too_enough"),
        edge("comparatives_superlatives_b1", "describing_places_b1"),
        edge("connecting_cause_effect", "opinion_justification"),
        edge("modals_must_have_to", "modals_must_cant_deduction"),
        edge("modals_might_may_probably", "speculating_b1"),
        edge("modals_must_cant_deduction", "speculating_b1"),
        edge("past_simple_b1", "past_continuous_b1"),
        edge("past_simple_b1", "wh_questions_past_b1"),
        edge("past_simple_b1", "present_perfect_b1"),
        edge("past_continuous_b1", "describing_experiences_events"),
        edge("present_perfect_b1", "present_perfect_vs_past"),
        edge("present_perfect_vs_past", "present_perfect_continuous"),
        edge("will_going_to_prediction", "future_continuous"),
        edge("past_simple_b1", "past_perfect"),
        edge("past_perfect", "conditionals_2nd_3rd"),
        edge("present_perfect_b1", "conditionals_2nd_3rd"),
        edge("conditionals_2nd_3rd", "modals_should_might_have"),
        edge("complex_question_tags", "interacting_informally"),
        edge("simple_passive", "vocab_news_lifestyles"),
        edge("reported_speech_range", "synthesizing_glossing_info"),
        edge("phrasal_verbs_extended", "describing_experiences_events"),
        edge("linkers_sequential_past_b1", "describing_experiences_events"),
        edge("describing_feelings_emotion", "vocab_feelings_extended"),
        edge("vocab_feelings_extended", "expressing_reaction"),
        edge("vocab_collocation_b1", "vocab_colloquial_b1"),
        edge("vocab_town_shops_b1", "vocab_travel_services_b1"),
        edge("vocab_leisure_b1", "vocab_film"),
        edge("vocab_film", "vocab_books_literature"),
        edge("vocab_education_b1", "vocab_media_b1"),
        edge("vocab_media_b1", "vocab_news_lifestyles"),
        edge("vocab_news_lifestyles", "reading_factual_articles"),
        edge("describing_experiences_events", "reading_factual_articles"),
        edge("past_tense_responses", "describing_experiences_events"),
        edge("past_simple_b1", "past_tense_responses"),
        edge("used_to_b1", "describing_experiences_events"),
        edge("past_simple_b1", "used_to_b1"),
        edge("expressing_opinions", "speculating_b1"),
        edge("taking_initiative_interaction", "synthesizing_glossing_info"),
        edge("describing_places_b1", "vocab_travel_services_b1"),
        edge("present_perfect_continuous", "describing_experiences_events"),
        edge("modals_might_may_probably", "will_going_to_prediction"),
        edge("intensifiers_too_enough", "describing_feelings_emotion"),
        edge("adverbs_range_b1", "describing_feelings_emotion"),
        edge("connecting_cause_effect", "synthesizing_glossing_info"),
        edge("vocab_colloquial_b1", "interacting_informally"),
        edge("wh_questions_past_b1", "reported_speech_range"),
        edge("present_perfect_vs_past", "reported_speech_range"),
        edge("simple_passive", "reported_speech_range"),
        edge("vocab_books_literature", "reading_factual_articles"),
    ]

    bridges = [
        edge("present_perfect_basic", "present_perfect_b1"),
        edge("past_continuous", "past_continuous_b1"),
        edge("zero_first_conditional", "conditionals_2nd_3rd"),
        edge("describing_past_experiences", "describing_experiences_events"),
        edge("phrasal_verbs_common", "phrasal_verbs_extended"),
        edge("linkers_sequential_past", "linkers_sequential_past_b1"),
        edge("modals_have_to", "modals_must_have_to"),
        edge("going_to_vs_will", "will_going_to_prediction"),
        # Fix 5 — same-construct progressions A2→B1
        edge("past_simple_a2", "past_simple_b1"),
        edge("vocab_education", "vocab_education_b1"),
        edge("wh_questions_past", "wh_questions_past_b1"),
        edge("describing_places", "describing_places_b1"),
        edge("vocab_travel_services", "vocab_travel_services_b1"),
        edge("vocab_town_shops_a2", "vocab_town_shops_b1"),
    ]

    summary = """# Core Inventory B1 skill catalog

**Sources:** Essential Guide B1; Poster B1; Appendix D/E.

## Merges
- Expressing opinions + agreeing/disagreeing → `expressing_opinions`
- Synthesizing/evaluating/glossing (two near-duplicate Essential lines) → `synthesizing_glossing_info`
- News/lifestyles/current affairs → one vocab node

## Omissions
- Exhaustive colloquial lists beyond one teachable node
- Every sub-scale of interaction strategies as separate skills (folded into managing_interaction / taking_initiative)
"""
    return skills, edges, bridges, summary


# ---------------------------------------------------------------------------
# B2
# ---------------------------------------------------------------------------

def build_b2() -> tuple[list[dict], list[dict], list[dict], str]:
    L = "B2"
    skills = [
        skill("adjectives_adverbs_b2", "Adjectives and adverbs (B2 control)", L, "grammar", 2, ["poster:B2", "essential:grammar"]),
        skill("future_continuous_b2", "Future continuous (B2)", L, "grammar", 3, ["poster:B2", "essential:grammar"]),
        skill("future_perfect", "Future perfect", L, "grammar", 5, ["poster:B2", "essential:grammar"]),
        skill("future_perfect_continuous", "Future perfect continuous", L, "grammar", 7, ["poster:B2", "essential:grammar"]),
        skill("mixed_conditionals", "Mixed conditionals", L, "grammar", 7, ["poster:B2", "essential:grammar"]),
        skill("modals_cant_neednt_have", "Can't have / needn't have", L, "grammar", 6, ["poster:B2", "essential:grammar"]),
        skill("modals_deduction_speculation", "Modals of deduction and speculation", L, "grammar", 5, ["poster:B2", "essential:grammar"]),
        skill("narrative_tenses", "Narrative tenses", L, "grammar", 6, ["poster:B2", "essential:grammar"]),
        skill("passives_b2", "Passives (B2 range)", L, "grammar", 5, ["poster:B2", "essential:grammar"]),
        skill("past_perfect_b2", "Past perfect (B2)", L, "grammar", 4, ["poster:B2", "essential:grammar"]),
        skill("past_perfect_continuous", "Past perfect continuous", L, "grammar", 6, ["poster:B2", "essential:grammar"]),
        skill("phrasal_verbs_b2", "Phrasal verbs (extended B2)", L, "grammar", 5, ["poster:B2", "essential:grammar"]),
        skill("relative_clauses", "Relative clauses", L, "grammar", 4, ["poster:B2", "essential:grammar"]),
        skill("reported_speech_b2", "Reported speech (B2)", L, "grammar", 5, ["poster:B2", "essential:grammar"]),
        skill("will_going_to_prediction_b2", "Will & going to for prediction (B2)", L, "grammar", 3, ["poster:B2", "essential:grammar"]),
        skill("wish_structures", "Wish", L, "grammar", 7, ["poster:B2", "essential:grammar"]),
        skill("would_past_habits", "Would (past habits)", L, "grammar", 6, ["poster:B2", "essential:grammar"]),
        skill("connectors_cause_contrast_b2", "Connectors: cause/effect/contrast (B2)", L, "grammar", 3, ["poster:B2", "essential:discourse"], "discourse"),
        skill("discourse_markers_formal_speech", "Discourse markers to structure formal speech", L, "grammar", 6, ["poster:B2", "essential:discourse"], "discourse"),
        skill("linkers_although_despite", "Linkers although / in spite of / despite", L, "grammar", 4, ["poster:B2", "essential:discourse"], "discourse"),
        skill("linkers_sequential_subsequently", "Sequential linkers (subsequently)", L, "grammar", 6, ["poster:B2", "essential:discourse"], "discourse"),
        skill("critiquing_reviewing", "Critiquing and reviewing", L, "functional", 6, ["poster:B2", "essential:functions"]),
        skill("describing_experiences_b2", "Describing experiences (B2)", L, "functional", 6, ["poster:B2", "essential:functions"]),
        skill("describing_feelings_b2", "Describing feelings and emotions (B2)", L, "functional", 8, ["poster:B2", "essential:functions"]),
        skill("describing_hopes_plans", "Describing hopes and plans", L, "functional", 4, ["poster:B2", "essential:functions"]),
        skill("developing_argument", "Developing an argument", L, "functional", 6, ["poster:B2", "essential:functions"]),
        skill("encouraging_another_speaker", "Encouraging another speaker to continue", L, "functional", 5, ["poster:B2", "essential:functions"]),
        skill("expressing_abstract_ideas", "Expressing abstract ideas", L, "functional", 7, ["poster:B2", "essential:functions"]),
        skill("expressing_agreement_b2", "Expressing agreement and disagreement", L, "functional", 3, ["poster:B2", "essential:functions"]),
        skill("expressing_opinions_b2", "Expressing opinions (B2)", L, "functional", 3, ["poster:B2", "essential:functions"]),
        skill("expressing_reaction_b2", "Expressing reaction (B2)", L, "functional", 8, ["poster:B2", "essential:functions"]),
        skill("interacting_informally_b2", "Interacting informally (B2)", L, "functional", 5, ["poster:B2", "essential:functions"]),
        skill("opinion_justification_b2", "Opinion with justification (B2)", L, "functional", 5, ["poster:B2", "essential:functions"]),
        skill("speculating_b2", "Speculating (B2)", L, "functional", 6, ["poster:B2", "essential:functions"]),
        skill("taking_initiative_b2", "Taking the initiative (B2)", L, "functional", 5, ["poster:B2", "essential:functions"]),
        skill("synthesizing_info_b2", "Synthesizing / evaluating / glossing (B2)", L, "functional", 7, ["poster:B2", "essential:functions"]),
        skill("vocab_collocation_b2", "Collocation (B2)", L, "vocabulary", 4, ["poster:B2", "essential:vocabulary"]),
        skill("vocab_colloquial_b2", "Colloquial language (B2)", L, "vocabulary", 5, ["poster:B2", "essential:vocabulary"]),
        skill("vocab_arts", "Arts vocabulary", L, "vocabulary", 6, ["poster:B2", "essential:topics"]),
        skill("vocab_books_literature_b2", "Books and literature (B2)", L, "vocabulary", 5, ["poster:B2", "essential:topics"]),
        skill("vocab_education_b2", "Education (B2)", L, "vocabulary", 4, ["poster:B2", "essential:topics"]),
        skill("vocab_film_b2", "Film (B2)", L, "vocabulary", 4, ["poster:B2", "essential:topics"]),
        skill("vocab_media_b2", "Media (B2)", L, "vocabulary", 5, ["poster:B2", "essential:topics"]),
        skill("vocab_news_lifestyles_b2", "News & current affairs (B2)", L, "vocabulary", 6, ["poster:B2", "essential:topics"]),
        skill("reading_viewpoint_articles", "Reading articles & viewpoints", L, "reading", 6, ["poster:B2"], "B2 reading: articles and viewpoints"),
        skill("wish_if_only_regs", "Wish / if only (regrets) intro", L, "grammar", 8, ["poster:B2"], "Aligns with wish; regrets language"),
        skill("vocab_topic_collocation_b2", "Topic-related collocation", L, "vocabulary", 6, ["poster:B2"], "Supports argument/review tasks"),
        skill("past_narrative_skills", "Narrative past (storytelling control)", L, "functional", 6, ["poster:B2"], "Pairs with narrative tenses"),
        skill("modals_speculation_talk", "Speculating with modal language", L, "functional", 6, ["poster:B2"], "Functional layer over deduction modals"),
        skill("relative_clauses_in_description", "Describing with relative clauses", L, "functional", 5, ["poster:B2"], "Applies relative_clauses"),
    ]

    edges = [
        edge("adjectives_adverbs_b2", "describing_feelings_b2"),
        edge("will_going_to_prediction_b2", "future_continuous_b2"),
        edge("future_continuous_b2", "future_perfect"),
        edge("future_perfect", "future_perfect_continuous"),
        edge("past_perfect_b2", "past_perfect_continuous"),
        edge("past_perfect_b2", "narrative_tenses"),
        edge("past_perfect_continuous", "narrative_tenses"),
        edge("narrative_tenses", "past_narrative_skills"),
        edge("passives_b2", "critiquing_reviewing"),
        edge("relative_clauses", "relative_clauses_in_description"),
        edge("relative_clauses_in_description", "describing_experiences_b2"),
        edge("reported_speech_b2", "synthesizing_info_b2"),
        edge("modals_deduction_speculation", "speculating_b2"),
        edge("modals_deduction_speculation", "modals_speculation_talk"),
        edge("modals_cant_neednt_have", "modals_speculation_talk"),
        edge("mixed_conditionals", "wish_structures"),
        edge("wish_structures", "wish_if_only_regs"),
        edge("would_past_habits", "past_narrative_skills"),
        edge("phrasal_verbs_b2", "describing_experiences_b2"),
        edge("connectors_cause_contrast_b2", "developing_argument"),
        edge("linkers_although_despite", "developing_argument"),
        edge("linkers_sequential_subsequently", "past_narrative_skills"),
        edge("discourse_markers_formal_speech", "developing_argument"),
        edge("expressing_agreement_b2", "expressing_opinions_b2"),
        edge("expressing_opinions_b2", "opinion_justification_b2"),
        edge("opinion_justification_b2", "developing_argument"),
        edge("interacting_informally_b2", "expressing_reaction_b2"),
        edge("encouraging_another_speaker", "taking_initiative_b2"),
        edge("taking_initiative_b2", "developing_argument"),
        edge("future_continuous_b2", "describing_hopes_plans"),
        edge("describing_feelings_b2", "expressing_reaction_b2"),
        edge("vocab_arts", "critiquing_reviewing"),
        edge("vocab_collocation_b2", "vocab_topic_collocation_b2"),
        edge("vocab_colloquial_b2", "interacting_informally_b2"),
        edge("vocab_education_b2", "vocab_media_b2"),
        edge("vocab_film_b2", "vocab_arts"),
        edge("vocab_books_literature_b2", "vocab_arts"),
        edge("vocab_media_b2", "vocab_news_lifestyles_b2"),
        edge("vocab_news_lifestyles_b2", "reading_viewpoint_articles"),
        edge("vocab_topic_collocation_b2", "reading_viewpoint_articles"),
        edge("developing_argument", "reading_viewpoint_articles"),
        edge("expressing_abstract_ideas", "synthesizing_info_b2"),
        edge("speculating_b2", "expressing_abstract_ideas"),
        edge("past_narrative_skills", "describing_experiences_b2"),
        edge("modals_speculation_talk", "speculating_b2"),
        edge("wish_if_only_regs", "describing_feelings_b2"),
        edge("passives_b2", "vocab_news_lifestyles_b2"),
        edge("reported_speech_b2", "critiquing_reviewing"),
        edge("interacting_informally_b2", "encouraging_another_speaker"),
        edge("describing_experiences_b2", "critiquing_reviewing"),
        edge("connectors_cause_contrast_b2", "linkers_although_despite"),
        edge("narrative_tenses", "linkers_sequential_subsequently"),
    ]

    bridges = [
        edge("conditionals_2nd_3rd", "mixed_conditionals"),
        edge("past_perfect", "past_perfect_b2"),
        edge("simple_passive", "passives_b2"),
        edge("reported_speech_range", "reported_speech_b2"),
        edge("phrasal_verbs_extended", "phrasal_verbs_b2"),
        # Fix 1 — early B1 spiral → full B2 treatment
        edge("speculating_b1", "speculating_b2"),
        edge("synthesizing_glossing_info", "synthesizing_info_b2"),
        edge("opinion_justification", "opinion_justification_b2"),
        edge("interacting_informally", "interacting_informally_b2"),
        edge("expressing_reaction", "expressing_reaction_b2"),
        edge("taking_initiative_interaction", "taking_initiative_b2"),
        edge("future_continuous", "future_continuous_b2"),
        edge("modals_must_cant_deduction", "modals_deduction_speculation"),
        # Fix 5 — same-construct progressions B1→B2
        edge("vocab_books_literature", "vocab_books_literature_b2"),
        edge("vocab_news_lifestyles", "vocab_news_lifestyles_b2"),
        edge("vocab_collocation_b1", "vocab_collocation_b2"),
        edge("vocab_film", "vocab_film_b2"),
        edge("vocab_colloquial_b1", "vocab_colloquial_b2"),
        edge("vocab_media_b1", "vocab_media_b2"),
        edge("will_going_to_prediction", "will_going_to_prediction_b2"),
    ]

    summary = """# Core Inventory B2 skill catalog

**Sources:** Essential Guide B2; Poster B2; Appendix D/E.

## Merges
- Passives (plural Essential mentions) → `passives_b2`
- Synthesizing/evaluating/glossing → `synthesizing_info_b2`
- Arts/books/film kept separate topic vocab nodes

## Omissions
- Full splitting of every discourse-marker subtype beyond formal-speech + although/despite + sequential
"""
    return skills, edges, bridges, summary


# ---------------------------------------------------------------------------
# C1
# ---------------------------------------------------------------------------

def build_c1() -> tuple[list[dict], list[dict], list[dict], str]:
    L = "C1"
    skills = [
        skill("futures_revision_c1", "Futures (revision & control)", L, "grammar", 2, ["poster:C1", "essential:grammar"]),
        skill("inversion_negative_adverbials", "Inversion with negative adverbials", L, "grammar", 6, ["poster:C1", "essential:grammar"]),
        skill("mixed_conditionals_c1", "Mixed conditionals (past/present/future)", L, "grammar", 5, ["poster:C1", "essential:grammar"]),
        skill("modals_in_the_past", "Modals in the past", L, "grammar", 5, ["poster:C1", "essential:grammar"]),
        skill("narrative_tenses_c1", "Narrative tenses incl. passive", L, "grammar", 4, ["poster:C1", "essential:grammar"]),
        skill("passive_forms_all", "Passive forms (all)", L, "grammar", 4, ["poster:C1", "essential:grammar"]),
        skill("phrasal_verbs_splitting", "Phrasal verbs (splitting)", L, "grammar", 5, ["poster:C1", "essential:grammar"]),
        skill("wish_if_only_regrets", "Wish / if only regrets", L, "grammar", 5, ["poster:C1", "essential:grammar"]),
        skill("linking_devices_logical", "Linking devices / logical markers", L, "grammar", 3, ["poster:C1", "essential:discourse"], "discourse"),
        skill("markers_structure_signpost", "Markers to structure formal/informal speech & writing", L, "grammar", 4, ["poster:C1", "essential:discourse"], "discourse"),
        skill("conceding_a_point", "Conceding a point", L, "functional", 4, ["poster:C1", "essential:functions"]),
        skill("critiquing_constructively", "Critiquing and reviewing constructively", L, "functional", 6, ["poster:C1", "essential:functions"]),
        skill("defending_viewpoint", "Defending a point of view persuasively", L, "functional", 6, ["poster:C1", "essential:functions"]),
        skill("developing_argument_systematic", "Developing an argument systematically", L, "functional", 5, ["poster:C1", "essential:functions"]),
        skill("emphasizing_a_point", "Emphasizing a point, feeling, issue", L, "functional", 6, ["poster:C1", "essential:functions"]),
        skill("expressing_attitudes_feelings", "Expressing attitudes and feelings precisely", L, "functional", 5, ["poster:C1", "essential:functions"]),
        skill("expressing_certainty_doubt", "Expressing certainty, probability, doubt", L, "functional", 4, ["poster:C1", "essential:functions"]),
        skill("expressing_opinions_tentative", "Expressing opinions tentatively; hedging", L, "functional", 5, ["poster:C1", "essential:functions"]),
        skill("expressing_reaction_c1", "Expressing reaction (nuanced, C1)", L, "functional", 7, ["poster:C1", "essential:functions"]),
        skill("expressing_shades_opinion", "Expressing shades of opinion and certainty", L, "functional", 6, ["poster:C1", "essential:functions"]),
        skill("responding_to_counterarguments", "Responding to counterarguments", L, "functional", 7, ["poster:C1", "essential:functions"]),
        skill("speculating_hypothesising", "Speculating and hypothesising about causes", L, "functional", 6, ["poster:C1", "essential:functions"]),
        skill("synthesising_evaluating_c1", "Synthesising, evaluating and glossing information", L, "functional", 7, ["poster:C1", "essential:functions"]),
        skill("vocab_approximating", "Approximating (vague language)", L, "vocabulary", 4, ["poster:C1", "essential:vocabulary"]),
        skill("vocab_collocation_c1", "Collocation (C1)", L, "vocabulary", 3, ["poster:C1", "essential:vocabulary"]),
        skill("vocab_colloquial_c1", "Colloquial language (C1)", L, "vocabulary", 4, ["poster:C1", "essential:vocabulary"]),
        skill("vocab_differentiated", "Differentiated use of vocabulary", L, "vocabulary", 6, ["poster:C1", "essential:vocabulary"]),
        skill("vocab_false_friends", "Eliminating false friends", L, "vocabulary", 5, ["poster:C1", "essential:vocabulary"]),
        skill("vocab_formal_informal_register", "Formal and informal registers", L, "vocabulary", 5, ["poster:C1", "essential:vocabulary"]),
        skill("vocab_idiomatic", "Idiomatic expressions", L, "vocabulary", 6, ["poster:C1", "essential:vocabulary"]),
        skill("vocab_arts_c1", "Arts (C1)", L, "vocabulary", 3, ["poster:C1", "essential:topics"]),
        skill("vocab_books_literature_c1", "Books and literature (C1)", L, "vocabulary", 3, ["poster:C1", "essential:topics"]),
        skill("vocab_film_c1", "Film (C1)", L, "vocabulary", 3, ["poster:C1", "essential:topics"]),
        skill("vocab_media_c1", "Media (C1)", L, "vocabulary", 4, ["poster:C1", "essential:topics"]),
        skill("vocab_news_c1", "News, lifestyles and current affairs (C1)", L, "vocabulary", 4, ["poster:C1", "essential:topics"]),
        skill("vocab_scientific", "Scientific developments", L, "vocabulary", 6, ["poster:C1", "essential:topics"]),
        skill("vocab_technical_legal", "Technical and legal language", L, "vocabulary", 7, ["poster:C1", "essential:topics"]),
        skill("reading_demanding_texts", "Reading longer demanding texts", L, "reading", 8, ["poster:C1"], "C1 reading: longer demanding texts; implied meaning"),
        skill("hedging_in_writing", "Hedging in careful expression", L, "functional", 6, ["poster:C1"], "Sub-skill of expressing_opinions_tentative, split out for finer practice granularity."),
        skill("precision_lexis_choice", "Precise lexical choice", L, "vocabulary", 7, ["poster:C1"], "Supports differentiated vocabulary"),
        skill("signposting_long_turns", "Signposting long spoken turns", L, "functional", 5, ["poster:C1"], "Sub-skill of markers_structure_signpost, split out for finer practice granularity."),
        skill("concession_in_debate", "Concession in discussion", L, "functional", 5, ["poster:C1"], "Sub-skill of conceding_a_point, split out for finer practice granularity."),
        skill("persuasive_structure", "Persuasive text/talk structure", L, "functional", 8, ["poster:C1"], "Sub-skill of defending_viewpoint, split out for finer practice granularity."),
        skill("narrative_with_passives", "Narrating with passive forms", L, "functional", 5, ["poster:C1"], "Sub-skill of narrative_tenses_c1, split out for finer practice granularity."),
        skill("hypothetical_past_modals", "Hypothetical meaning with past modals", L, "functional", 6, ["poster:C1"], "Sub-skill of modals_in_the_past, split out for finer practice granularity."),
        skill("register_shifting", "Shifting formal/informal register", L, "functional", 6, ["poster:C1"], "Sub-skill of vocab_formal_informal_register, split out for finer practice granularity."),
        skill("idioms_in_interaction", "Using idioms in interaction", L, "functional", 7, ["poster:C1"], "Sub-skill of vocab_idiomatic, split out for finer practice granularity."),
        skill("evaluating_sources", "Evaluating and glossing sources", L, "functional", 8, ["poster:C1"], "Sub-skill of synthesising_evaluating_c1, split out for finer practice granularity."),
        skill("nuance_certainty_scale", "Nuancing certainty and doubt", L, "functional", 6, ["poster:C1"], "Sub-skill of expressing_certainty_doubt, split out for finer practice granularity."),
        skill("advanced_topic_collocation", "Advanced topic collocation", L, "vocabulary", 5, ["poster:C1"], "Supports arts/media/science topics"),
    ]

    edges = [
        edge("futures_revision_c1", "mixed_conditionals_c1"),
        edge("mixed_conditionals_c1", "wish_if_only_regrets"),
        edge("modals_in_the_past", "hypothetical_past_modals"),
        edge("hypothetical_past_modals", "speculating_hypothesising"),
        edge("narrative_tenses_c1", "narrative_with_passives"),
        edge("passive_forms_all", "narrative_with_passives"),
        edge("phrasal_verbs_splitting", "idioms_in_interaction"),
        edge("linking_devices_logical", "markers_structure_signpost"),
        edge("markers_structure_signpost", "signposting_long_turns"),
        edge("conceding_a_point", "concession_in_debate"),
        edge("concession_in_debate", "responding_to_counterarguments"),
        edge("developing_argument_systematic", "critiquing_constructively"),
        edge("developing_argument_systematic", "defending_viewpoint"),
        edge("defending_viewpoint", "responding_to_counterarguments"),
        edge("defending_viewpoint", "persuasive_structure"),
        edge("emphasizing_a_point", "expressing_shades_opinion"),
        edge("expressing_attitudes_feelings", "expressing_reaction_c1"),
        edge("expressing_certainty_doubt", "nuance_certainty_scale"),
        edge("nuance_certainty_scale", "expressing_shades_opinion"),
        edge("expressing_opinions_tentative", "hedging_in_writing"),
        edge("vocab_approximating", "hedging_in_writing"),
        edge("synthesising_evaluating_c1", "evaluating_sources"),
        edge("vocab_collocation_c1", "advanced_topic_collocation"),
        edge("vocab_colloquial_c1", "register_shifting"),
        edge("vocab_formal_informal_register", "register_shifting"),
        edge("vocab_differentiated", "precision_lexis_choice"),
        edge("vocab_false_friends", "precision_lexis_choice"),
        edge("vocab_idiomatic", "idioms_in_interaction"),
        edge("vocab_arts_c1", "vocab_books_literature_c1"),
        edge("vocab_film_c1", "vocab_arts_c1"),
        edge("vocab_media_c1", "vocab_news_c1"),
        edge("vocab_news_c1", "vocab_scientific"),
        edge("vocab_scientific", "vocab_technical_legal"),
        edge("advanced_topic_collocation", "vocab_scientific"),
        edge("vocab_technical_legal", "reading_demanding_texts"),
        edge("synthesising_evaluating_c1", "reading_demanding_texts"),
        edge("precision_lexis_choice", "reading_demanding_texts"),
        edge("inversion_negative_adverbials", "emphasizing_a_point"),
        edge("wish_if_only_regrets", "expressing_attitudes_feelings"),
        edge("signposting_long_turns", "developing_argument_systematic"),
        edge("evaluating_sources", "persuasive_structure"),
        edge("register_shifting", "critiquing_constructively"),
        edge("expressing_reaction_c1", "idioms_in_interaction"),
        edge("narrative_with_passives", "critiquing_constructively"),
        edge("responding_to_counterarguments", "persuasive_structure"),
        edge("conceding_a_point", "expressing_attitudes_feelings"),
        edge("vocab_books_literature_c1", "reading_demanding_texts"),
        edge("linking_devices_logical", "developing_argument_systematic"),
        edge("futures_revision_c1", "speculating_hypothesising"),
        edge("modals_in_the_past", "inversion_negative_adverbials"),
        edge("passive_forms_all", "vocab_technical_legal"),
        edge("vocab_collocation_c1", "vocab_differentiated"),
        edge("vocab_approximating", "vocab_colloquial_c1"),
        edge("markers_structure_signpost", "persuasive_structure"),
        edge("hedging_in_writing", "expressing_shades_opinion"),
        edge("register_shifting", "idioms_in_interaction"),
        edge("conceding_a_point", "critiquing_constructively"),
    ]

    bridges = [
        edge("mixed_conditionals", "mixed_conditionals_c1"),
        edge("wish_structures", "wish_if_only_regrets"),
        edge("passives_b2", "passive_forms_all"),
        edge("narrative_tenses", "narrative_tenses_c1"),
        edge("phrasal_verbs_b2", "phrasal_verbs_splitting"),
        edge("developing_argument", "developing_argument_systematic"),
        edge("synthesizing_info_b2", "synthesising_evaluating_c1"),
        edge("discourse_markers_formal_speech", "markers_structure_signpost"),
        edge("modals_deduction_speculation", "modals_in_the_past"),
        edge("future_perfect_continuous", "futures_revision_c1"),
        # Fix 4 — reaction progression
        edge("expressing_reaction_b2", "expressing_reaction_c1"),
        # Fix 5 — same-construct progressions B2→C1
        edge("vocab_books_literature_b2", "vocab_books_literature_c1"),
        edge("vocab_arts", "vocab_arts_c1"),
        edge("vocab_collocation_b2", "vocab_collocation_c1"),
        edge("vocab_film_b2", "vocab_film_c1"),
        edge("vocab_colloquial_b2", "vocab_colloquial_c1"),
        edge("vocab_media_b2", "vocab_media_c1"),
    ]

    summary = """# Core Inventory C1 skill catalog

**Sources:** Essential Guide C1; Poster C1; Appendix D/E.  
**Note:** Inventory itself flags weaker consensus at C1 — nodes stay closer to listed Functions/Grammar/Vocab/Topics.

## Merges
- Markers to structure formal and informal speech and writing → `markers_structure_signpost`
- Critiquing constructively kept distinct from B2 `critiquing_reviewing`

## Omissions
- Exhaustive legal/scientific sub-domain lists beyond one node each
- Native-like idioms dictionaries (single teachable idioms node)
"""
    return skills, edges, bridges, summary


def emit(
    level: str,
    skills: list[dict],
    edges: list[dict],
    bridges: list[dict],
    summary: str,
) -> None:
    lv = level.lower()
    # Keep legacy scaffold filenames for A2 as the primary files
    skills_path = OUT / f"skills_{lv}.jsonl"
    edges_path = OUT / f"edges_{lv}.jsonl"
    bridge_path = OUT / f"edges_bridge_{lv}.jsonl"
    sum_path = OUT / f"summary_{lv}.md"
    val_path = OUT / f"self_validation_{lv}.md"

    write_jsonl(skills_path, skills)
    write_jsonl(edges_path, edges)
    write_jsonl(bridge_path, bridges)
    r = validate(skills, edges, label=level)
    sum_path.write_text(
        summary
        + f"\n\n## Final counts\n- nodes: {r['nodes']}\n- edges: {r['edges']}\n"
        f"- skill_type: {r['types']}\n- bridges (to this level): {len(bridges)}\n",
        encoding="utf-8",
    )
    val_path.write_text(report_validation(r), encoding="utf-8")
    print(level, "OK" if r["ok"] else "FAIL", r)
    if not r["ok"]:
        raise SystemExit(f"Validation failed for {level}")


def load_a1_slugs() -> set[str]:
    path = OUT / "skills.jsonl"
    return {
        json.loads(line)["slug"]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    }


def validate_bridges(
    bridges: list[dict[str, str]],
    *,
    from_slugs: set[str],
    to_slugs: set[str],
    label: str,
) -> list[str]:
    errs: list[str] = []
    seen: set[tuple[str, str]] = set()
    for e in bridges:
        key = (e["from_slug"], e["to_slug"])
        if key in seen:
            errs.append(f"{label}: duplicate bridge {key[0]} → {key[1]}")
        seen.add(key)
        if e["from_slug"] not in from_slugs:
            errs.append(f"{label}: dangling from_slug {e['from_slug']}")
        if e["to_slug"] not in to_slugs:
            errs.append(f"{label}: dangling to_slug {e['to_slug']}")
    return errs


def find_duplicate_titles(skill_sets: list[list[dict[str, Any]]]) -> dict[str, list[str]]:
    titles: dict[str, list[str]] = defaultdict(list)
    for skills in skill_sets:
        for s in skills:
            titles[s["title"]].append(f"{s['cefr_level']}:{s['slug']}")
    return {t: refs for t, refs in titles.items() if len(refs) > 1}


def main() -> None:
    a1_slugs = load_a1_slugs()
    built: dict[str, tuple[list[dict], list[dict], list[dict], str]] = {
        "A2": build_a2(),
        "B1": build_b1(),
        "B2": build_b2(),
        "C1": build_c1(),
    }
    prev_slugs = a1_slugs
    bridge_errs: list[str] = []
    for level in ("A2", "B1", "B2", "C1"):
        skills, edges, bridges, summary = built[level]
        emit(level, skills, edges, bridges, summary)
        bridge_errs.extend(
            validate_bridges(
                bridges,
                from_slugs=prev_slugs,
                to_slugs={s["slug"] for s in skills},
                label=f"bridge→{level}",
            )
        )
        prev_slugs = {s["slug"] for s in skills}

    a1_skills = [
        json.loads(line)
        for line in (OUT / "skills.jsonl").read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    dups = find_duplicate_titles(
        [a1_skills] + [built[lv][0] for lv in ("A2", "B1", "B2", "C1")]
    )
    if bridge_errs:
        print("BRIDGE ERRORS:")
        for e in bridge_errs:
            print(" -", e)
        raise SystemExit("Bridge validation failed")
    if dups:
        print("DUPLICATE TITLES:", dict(dups))
        raise SystemExit("Duplicate titles across suite")
    print("Bridge refs OK; duplicate titles: none")
    print("All levels written to", OUT)


if __name__ == "__main__":
    main()
