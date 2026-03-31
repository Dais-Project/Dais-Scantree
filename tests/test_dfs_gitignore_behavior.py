from __future__ import annotations

from pathlib import Path
from dais_scantree import dfs as scantree_dfs


def _scan_relpaths(
    root: Path,
    *,
    scan_limit: int = 10_000,
    max_depth: int | None = None,
    include_hidden: bool = False,
    include_gitignored: bool = False,
) -> list[str]:
    entries = list(
        scantree_dfs(
            root,
            scan_limit=scan_limit,
            max_depth=max_depth,
            include_hidden=include_hidden,
            include_gitignored=include_gitignored,
        )
    )
    resolved_root = root.resolve()
    return [Path(entry.path).resolve().relative_to(resolved_root).as_posix() for entry, _ in entries]


def test_scandir_recursive_dfs_gitignore_switch_changes_result_set(make_tree) -> None:
    root = make_tree(
        {
            ".gitignore": "ignored_dir/\n*.log\n!important.log\n",
            "notes.txt": "",
            "debug.log": "",
            "important.log": "",
            "ignored_dir": {
                "inside.txt": "",
            },
        }
    )

    filtered = _scan_relpaths(root, include_hidden=False, include_gitignored=False)
    unfiltered = _scan_relpaths(root, include_hidden=False, include_gitignored=True)

    assert "notes.txt" in filtered
    assert "important.log" in filtered
    assert "debug.log" not in filtered
    assert "ignored_dir" not in filtered
    assert "ignored_dir/inside.txt" not in filtered

    assert "debug.log" in unfiltered
    assert "ignored_dir" in unfiltered
    assert "ignored_dir/inside.txt" in unfiltered


def test_scandir_recursive_dfs_applies_nested_gitignore_and_negation(make_tree) -> None:
    root = make_tree(
        {
            "pkg": {
                ".gitignore": "*.tmp\n!important.tmp\n",
                "a.tmp": "",
                "important.tmp": "",
                "readme.md": "",
            }
        }
    )

    filtered = _scan_relpaths(root, include_hidden=False, include_gitignored=False)

    assert "pkg" in filtered
    assert "pkg/readme.md" in filtered
    assert "pkg/a.tmp" not in filtered
    assert "pkg/important.tmp" in filtered


def test_scandir_recursive_dfs_nested_gitignore_relative_directory_rule(make_tree) -> None:
    root = make_tree(
        {
            "pkg": {
                ".gitignore": "build/\n",
                "build": {"ignored.txt": ""},
                "keep": {"alive.txt": ""},
            },
            "build": {"root_level.txt": ""},
        }
    )

    filtered = _scan_relpaths(root, include_hidden=False, include_gitignored=False)

    assert "pkg" in filtered
    assert "pkg/build" not in filtered
    assert "pkg/build/ignored.txt" not in filtered
    assert "pkg/keep" in filtered
    assert "pkg/keep/alive.txt" in filtered

    # 子目录规则应仅作用于该子目录，不应影响根目录同名路径
    assert "build" in filtered
    assert "build/root_level.txt" in filtered
