from app.services.skill_drill_blueprint import blueprint_for_skill_drill


def test_grammar_blueprint_length_and_kinds():
    bp = blueprint_for_skill_drill("grammar", 6)
    assert len(bp) == 6
    kinds = [b["item_kind"] for b in bp]
    assert kinds.count("reading_target") <= 2
    assert "form_choose" in kinds
    assert "fix_grammar" in kinds


def test_grammar_blueprint_pack_checkpoint_default():
    bp = blueprint_for_skill_drill("grammar", 10)
    assert len(bp) == 10
    kinds = [b["item_kind"] for b in bp]
    assert kinds.count("form_choose") >= 2
    assert "cloze_form" in kinds
    assert "fix_grammar" in kinds


def test_vocab_blueprint_has_reading_cap():
    bp = blueprint_for_skill_drill("vocabulary", 8)
    assert len(bp) == 8
    assert sum(1 for b in bp if b["item_kind"] == "reading_target") <= 2
