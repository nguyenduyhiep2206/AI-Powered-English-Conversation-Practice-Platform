from app.services.skill_drill_blueprint import blueprint_for_skill_drill


def test_grammar_blueprint_length_and_kinds():
    bp = blueprint_for_skill_drill("grammar", 6)
    assert len(bp) == 6
    kinds = [b["item_kind"] for b in bp]
    assert "spot_error" in kinds
    assert "sentence_build" in kinds
    assert "form_choose" in kinds
    assert "fix_grammar" in kinds


def test_grammar_blueprint_pack_checkpoint_default():
    bp = blueprint_for_skill_drill("grammar", 10)
    assert len(bp) == 10
    kinds = [b["item_kind"] for b in bp]
    assert kinds.count("form_choose") >= 2
    assert "cloze_form" in kinds
    assert "fix_grammar" in kinds
    assert kinds.count("sentence_build") <= 2


def test_vocab_blueprint_has_kind_caps():
    bp = blueprint_for_skill_drill("vocabulary", 8)
    assert len(bp) == 8
    kinds = [b["item_kind"] for b in bp]
    assert kinds.count("reading_target") <= 2
    assert kinds.count("matching") <= 1
    assert kinds.count("sentence_build") <= 2
    assert "matching" in kinds
    assert "sentence_build" in kinds


def test_default_blueprint_has_new_kinds():
    bp = blueprint_for_skill_drill("reading", 6)
    assert len(bp) == 6
    kinds = [b["item_kind"] for b in bp]
    assert "dialogue_complete" in kinds
    assert "multi_select" in kinds
    assert kinds.count("reading_target") <= 2
