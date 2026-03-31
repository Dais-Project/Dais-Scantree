# Dais ScanTree

An LLM agent friendly file tree scanner.

## Usage

```python
from dais_scantree import bfs as scantree_bfs

for entry in scantree_bfs("./", scan_limit=100, include_hidden=True, include_gitignored=True):
    print(entry.path)
```
