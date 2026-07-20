# backend/tests/test_skill_graph_difficulty.py
from app.services.skill_graph_difficulty import difficulty_from_unit_index, median_difficulty


def test_difficulty_dau_cuoi_sach():
    assert difficulty_from_unit_index(0, 10) == 1
    assert difficulty_from_unit_index(9, 10) == 10


def test_difficulty_mot_unit():
    assert difficulty_from_unit_index(0, 1) == 1


def test_median_difficulty():
    assert median_difficulty([2, 8, 5]) == 5
    assert median_difficulty([3, 4]) == 3  # lower median for even length
