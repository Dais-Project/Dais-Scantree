from __future__ import annotations


def test_scandir_recursive_bfs_gitignore_switch_changes_result_set(make_tree, scan_relpaths) -> None:
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

    filtered = scan_relpaths(root, include_hidden=False, include_gitignored=False)
    unfiltered = scan_relpaths(root, include_hidden=False, include_gitignored=True)

    assert "notes.txt" in filtered
    assert "important.log" in filtered
    assert "debug.log" not in filtered
    assert "ignored_dir" not in filtered
    assert "ignored_dir/inside.txt" not in filtered

    assert "debug.log" in unfiltered
    assert "ignored_dir" in unfiltered
    assert "ignored_dir/inside.txt" in unfiltered


def test_scandir_recursive_bfs_applies_nested_gitignore_and_negation(make_tree, scan_relpaths) -> None:
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

    filtered = scan_relpaths(root, include_hidden=False, include_gitignored=False)

    assert "pkg" in filtered
    assert "pkg/readme.md" in filtered
    assert "pkg/a.tmp" not in filtered
    assert "pkg/important.tmp" in filtered


def test_scandir_recursive_bfs_nested_gitignore_relative_directory_rule(make_tree, scan_relpaths) -> None:
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

    filtered = scan_relpaths(root, include_hidden=False, include_gitignored=False)

    assert "pkg" in filtered
    assert "pkg/build" not in filtered
    assert "pkg/build/ignored.txt" not in filtered
    assert "pkg/keep" in filtered
    assert "pkg/keep/alive.txt" in filtered

    # 子目录规则应仅作用于该子目录，不应影响根目录同名路径
    assert "build" in filtered
    assert "build/root_level.txt" in filtered
