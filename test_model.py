import unittest
from src.model import predict_match, double_chance

class ModelTests(unittest.TestCase):
    def test_probabilities_sum_approximately_one(self):
        p = predict_match(1.4, 1.1)
        self.assertAlmostEqual(p["p_home"] + p["p_draw"] + p["p_away"], 1.0, places=3)

    def test_over_under_complement(self):
        p = predict_match(1.4, 1.1)
        self.assertAlmostEqual(p["p_over25"] + p["p_under25"], 1.0, places=8)

    def test_btts_complement(self):
        p = predict_match(1.4, 1.1)
        self.assertAlmostEqual(p["p_btts_yes"] + p["p_btts_no"], 1.0, places=8)

    def test_double_chance(self):
        p = predict_match(1.4, 1.1)
        dc = double_chance(p)
        self.assertAlmostEqual(dc["1X"], p["p_home"] + p["p_draw"])

if __name__ == "__main__":
    unittest.main()
