from app.services.mastery_service import (
    MASTERY_STRONG,
    MASTERY_WEAK,
    grade_mcq,
    next_mastery,
)


def test_tra_loi_dung_tang_mastery():
    assert next_mastery(0.3, correct=True) > 0.3


def test_tra_loi_sai_giam_mastery():
    assert next_mastery(0.6, correct=False) < 0.6


def test_clamp():
    assert 0.0 <= next_mastery(0.99, correct=True) <= 1.0
    assert 0.0 <= next_mastery(0.01, correct=False) <= 1.0


def test_nguong():
    assert MASTERY_WEAK == 0.4
    assert MASTERY_STRONG == 0.7


def test_cham_mcq_khong_phan_biet_hoa():
    assert grade_mcq("Have lived", "have lived") is True
    assert grade_mcq("have lived", "lived") is False
