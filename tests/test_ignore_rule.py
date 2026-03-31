from __future__ import annotations

from pathlib import Path

import pathspec

from dais_scantree.ignore_rule import IgnoreRuleNode, is_hidden, load_gitignore_spec


def test_check_ignore_applies_parent_gitignore_rules(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
    (tmp_path / "app.log").write_text("", encoding="utf-8")
    (tmp_path / "app.txt").write_text("", encoding="utf-8")

    root_node = IgnoreRuleNode(tmp_path, load_gitignore_spec(tmp_path))

    assert root_node.check_ignore(tmp_path / "app.log") is True
    assert root_node.check_ignore(tmp_path / "app.txt") is False


def test_check_ignore_child_negation_overrides_parent_ignore(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("*.log\n", encoding="utf-8")
    child = tmp_path / "pkg"
    child.mkdir()
    (child / ".gitignore").write_text("!keep.log\n", encoding="utf-8")
    (child / "keep.log").write_text("", encoding="utf-8")
    (child / "other.log").write_text("", encoding="utf-8")

    root_node = IgnoreRuleNode(tmp_path, load_gitignore_spec(tmp_path))
    child_node = IgnoreRuleNode(child, load_gitignore_spec(child), root_node)

    assert child_node.check_ignore(child / "keep.log") is False
    assert child_node.check_ignore(child / "other.log") is True


def test_check_ignore_child_rules_override_parent_negation(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("*.tmp\n!shared.tmp\n", encoding="utf-8")
    child = tmp_path / "build"
    child.mkdir()
    (child / ".gitignore").write_text("*.tmp\n", encoding="utf-8")
    target = child / "shared.tmp"
    target.write_text("", encoding="utf-8")

    root_node = IgnoreRuleNode(tmp_path, load_gitignore_spec(tmp_path))
    child_node = IgnoreRuleNode(child, load_gitignore_spec(child), root_node)

    assert child_node.check_ignore(target) is True


def test_check_ignore_uses_last_match_within_same_spec(tmp_path: Path) -> None:
    target = tmp_path / "important.log"
    target.write_text("", encoding="utf-8")

    spec_unignore_last = pathspec.PathSpec.from_lines("gitignore", ["*.log", "!important.log"])
    spec_ignore_last = pathspec.PathSpec.from_lines("gitignore", ["!important.log", "*.log"])

    node_unignore_last = IgnoreRuleNode(tmp_path, spec_unignore_last)
    node_ignore_last = IgnoreRuleNode(tmp_path, spec_ignore_last)

    assert node_unignore_last.check_ignore(target) is False
    assert node_ignore_last.check_ignore(target) is True


def test_load_gitignore_spec_returns_none_when_missing(tmp_path: Path) -> None:
    assert load_gitignore_spec(tmp_path) is None


def test_load_gitignore_spec_loads_valid_spec(tmp_path: Path) -> None:
    (tmp_path / ".gitignore").write_text("*.cache\n", encoding="utf-8")

    spec = load_gitignore_spec(tmp_path)

    assert spec is not None
    node = IgnoreRuleNode(tmp_path, spec)
    cache_file = tmp_path / "result.cache"
    cache_file.write_text("", encoding="utf-8")
    assert node.check_ignore(cache_file) is True


def test_check_ignore_returns_false_for_path_outside_rule_chain(tmp_path: Path) -> None:
    root = tmp_path / "root"
    root.mkdir()
    (root / ".gitignore").write_text("*\n", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("", encoding="utf-8")

    node = IgnoreRuleNode(root, load_gitignore_spec(root))

    assert node.check_ignore(outside) is False


def test_is_hidden_only_depends_on_name() -> None:
    assert is_hidden(Path(".env")) is True
    assert is_hidden(Path("dir/.secret")) is True
    assert is_hidden(Path("visible.txt")) is False
