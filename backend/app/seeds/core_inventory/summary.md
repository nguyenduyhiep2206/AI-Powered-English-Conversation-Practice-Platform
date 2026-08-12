# Core Inventory A1 skill catalog (draft)

**Sources:** EAQUALS_British_Council_Core_Curriculum_April2011.pdf (Essential guide + Appendix E); Core-Inventory-Posters-2018-update.pdf (A1).  
**Scope:** A1 only (for review). A2–C1 not generated yet.  
**License note:** Catalog derived under rights confirmed by product owner; do not redistribute the PDFs.

## Counts

| skill_type | n |
|------------|---|
| grammar | 28 |
| functional | 8 |
| vocabulary | 11 |
| **total** | **47** |

- Prerequisite edges: **40** (~1.43 per grammar node)
- Target band: 45–55 (hard max 65) → **OK**
- Mix: grammar 60%, functional 17%, vocabulary 23%

## Merges

- Questions + question forms → `questions_basic`
- Can/can't (ability) + can/could (requests) → `can_cant`
- Hobbies/pastimes + leisure activities → `vocab_hobbies_leisure`
- Town/shops vocabulary + topic Shopping → `vocab_town_shops`
- Past simple regular/irregular common → single `past_simple` at A1
- Poster listening/reading/writing can-dos folded into functional nodes (not separate skills)
- Colours + clothes (Appendix E) → `vocab_colours_clothes`

## Intentionally not separate nodes

- Individual exponent sentences from posters
- Classroom strategies (gesture, ask to repeat) as skills
- Reading/writing micro can-dos without Essential-guide language point

## Diff vs existing `cefr_ladder_a1_a2.py` A1

Adds functional layer (greetings, numbers, prices, time, directions, routines…), denser vocab/topics, discourse connectors, have_got, demonstratives, determiners, intensifiers, I'd like, verb-ing likes. Some slug renames vs ladder (`articles_a_an_the`→`articles_basic`, `possessives`→split adjectives/'s`).

## Files

- `skills.jsonl`
- `edges.jsonl`
