from contextguard.command_classifier import classify_command


def test_small_command_passthrough():
    assert classify_command("pwd").action == "allow"


def test_large_commands_captured():
    assert classify_command("cat huge.log").action == "capture"
    assert classify_command("git diff").action == "capture"
    assert classify_command("find .").action == "capture"


def test_observed_large_inspection_bypasses_are_captured():
    commands = [
        "sed -n '1,260p' artifacts/CI_FAILURE.log",
        "tail -n 40 artifacts/CI_FAILURE.log",
        "head -n 500 artifacts/CI_FAILURE.log",
        "awk '{print}' data/warehouse-export.jsonl",
        "jq '.' data/orders.json",
        "sed -n '1,200p' one.py two.py three.py four.py",
        "rg -n ERROR artifacts/CI_FAILURE.log | head -100",
    ]
    for command in commands:
        assert classify_command(command).action == "capture", command


def test_small_scoped_source_reads_remain_direct():
    assert classify_command("sed -n '1,120p' app.py").action == "allow"
    assert classify_command("head -20 README.md").action == "allow"


def test_python_module_validation_and_tee_pipeline_are_captured():
    assert classify_command("python3 -m pytest -q").action == "capture"
    assert classify_command("python -m pytest -q 2>&1 | tee /tmp/tests.log").action == "capture"


def test_common_agent_command_families_are_captured():
    commands = [
        "cargo test --workspace",
        "go test ./...",
        "docker build .",
        "kubectl get pods -A",
        "terraform plan",
        "gh run view 123 --log",
        "pnpm test",
        "vitest run",
        "curl https://example.test/api/results.json",
    ]
    for command in commands:
        assert classify_command(command).action == "capture", command


def test_destructive_commands_not_rewritten():
    decision = classify_command("rm -rf build")
    assert decision.action == "allow"
    assert "not rewritten" in decision.reason
