from app.models.tutor import TutorMessageDB, TutorSessionDB


def test_tutor_table_names():
    assert TutorSessionDB.__tablename__ == "tutor_sessions"
    assert TutorMessageDB.__tablename__ == "tutor_messages"
