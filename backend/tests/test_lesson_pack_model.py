from app.models.skill_lesson import SkillLessonDB


def test_pack_index_column_exists():
    assert hasattr(SkillLessonDB, "pack_index")
