from services.als_recommender import als_predict


def test_als_scores_unseen_items_between_zero_and_one():
    ratings = {
        (1, 10): 1,
        (1, 11): 3,
        (1, 12): 4,
        (2, 10): 3,
        (2, 13): 5,
        (3, 11): 1,
        (3, 13): 4,
    }
    scores = als_predict(ratings, 1, [13, 14])
    assert set(scores) == {13, 14}
    assert all(0 <= value <= 1 for value in scores.values())
