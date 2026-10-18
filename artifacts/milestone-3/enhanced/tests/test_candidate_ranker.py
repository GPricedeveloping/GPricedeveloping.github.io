import pytest

from services.candidate_ranker import rank_candidates, score_candidate


def water_candidate(**changes):
    candidate = {
        "animal_id": "A100",
        "name": "Marley",
        "animal_type": "Dog",
        "breed": "Labrador Retriever Mix",
        "sex_upon_outcome": "Intact Female",
        "age_upon_outcome_in_weeks": 91,
        "location_lat": 30.27,
        "location_long": -97.74,
    }
    candidate.update(changes)
    return candidate


def test_complete_midrange_candidate_scores_100():
    assert score_candidate(water_candidate(), "water") == 100


def test_missing_or_mismatched_fields_lower_the_score():
    complete = water_candidate()
    weaker = water_candidate(
        animal_type="Cat",
        sex_upon_outcome="Neutered Male",
        location_lat=None,
    )
    assert score_candidate(complete, "water") > score_candidate(weaker, "water")


def test_rank_candidates_returns_only_top_k_in_score_order():
    candidates = [
        water_candidate(animal_id="boundary-low", age_upon_outcome_in_weeks=26),
        water_candidate(animal_id="near-middle", age_upon_outcome_in_weeks=80),
        water_candidate(animal_id="middle", age_upon_outcome_in_weeks=91),
        water_candidate(animal_id="boundary-high", age_upon_outcome_in_weeks=156),
    ]

    ranked = rank_candidates(candidates, "water", k=2)

    assert [animal["animal_id"] for animal in ranked] == ["middle", "near-middle"]
    assert [animal["rank"] for animal in ranked] == [1, 2]
    assert ranked[0]["suitability_score"] >= ranked[1]["suitability_score"]


def test_equal_scores_keep_input_order():
    candidates = [
        water_candidate(animal_id="first", age_upon_outcome_in_weeks=26),
        water_candidate(animal_id="second", age_upon_outcome_in_weeks=156),
    ]
    ranked = rank_candidates(candidates, "water", k=2)
    assert [animal["animal_id"] for animal in ranked] == ["first", "second"]


def test_ranking_does_not_change_source_records():
    candidate = water_candidate()
    rank_candidates([candidate], "water")
    assert "rank" not in candidate
    assert "suitability_score" not in candidate


def test_empty_and_reset_inputs_return_no_ranked_candidates():
    assert rank_candidates([], "water") == []
    assert rank_candidates([water_candidate()], "reset") == []


def test_missing_fields_do_not_crash_scoring():
    assert score_candidate({}, "water") == 0
    ranked = rank_candidates([{}], "water")
    assert ranked[0]["suitability_score"] == 0


@pytest.mark.parametrize("invalid_k", [0, -1, 1.5, True])
def test_invalid_k_is_rejected(invalid_k):
    with pytest.raises(ValueError, match="positive integer"):
        rank_candidates([water_candidate()], "water", k=invalid_k)


def test_unknown_rescue_type_is_rejected():
    with pytest.raises(ValueError, match="Unknown rescue filter"):
        rank_candidates([water_candidate()], "space-rescue")
