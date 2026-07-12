from contextguard.repo_ranker import is_retrieval_candidate, rank_repository, reciprocal_rank_fusion


def test_benchmark_results_are_not_retrieval_candidates():
    assert is_retrieval_candidate("contextguard/benchmarks/results/run/summary.json") is False
    assert is_retrieval_candidate("contextguard/contextguard/task_classifier.py") is True


def test_rrf_rewards_items_present_in_multiple_rankings():
    fused = reciprocal_rank_fusion(
        [
            (["both.py", "path_only.py"], 1.0, "path"),
            (["both.py", "content_only.py"], 1.0, "content"),
        ]
    )
    assert fused["both.py"]["score"] > fused["path_only.py"]["score"]
    assert fused["both.py"]["score"] > fused["content_only.py"]["score"]
