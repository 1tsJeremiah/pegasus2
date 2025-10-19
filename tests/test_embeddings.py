import math
from codex_vector.embeddings import generate_embedding

def test_len_det_norm():
    t = "quick brown"
    v1 = generate_embedding(t, 64); v2 = generate_embedding(t, 64)
    assert len(v1) == 64 and v1 == v2
    n = (sum(x*x for x in v1)) ** 0.5
    assert 0.99 <= n <= 1.01
