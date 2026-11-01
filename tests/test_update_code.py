from pathlib import Path


def test_target_exists():
    target = Path(__file__).parents[1] / "update_code.py"
    assert target.exists()


def test_target_is_python():
    target = Path(__file__).parents[1] / "update_code.py"
    compile(target.read_text(encoding="utf-8"), str(target), "exec")
