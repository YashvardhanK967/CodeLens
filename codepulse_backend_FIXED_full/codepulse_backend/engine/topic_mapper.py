import re

# Add aliases here whenever your data-fetching teammate discovers a new platform tag.
_ALIASES = {
    "dp": "Dynamic Programming",
    "dynamic programming": "Dynamic Programming",
    "dynamic-programming": "Dynamic Programming",
    "dynamic_programming": "Dynamic Programming",
    "array": "Arrays",
    "arrays": "Arrays",
    "string": "Strings",
    "strings": "Strings",
    "math": "Math",
    "mathematics": "Math",
    "binary search": "Binary Search",
    "binary-search": "Binary Search",
    "sorting": "Sorting",
    "sort": "Sorting",
    "two pointers": "Two Pointers",
    "two-pointers": "Two Pointers",
    "sliding window": "Sliding Window",
    "sliding-window": "Sliding Window",
    "greedy": "Greedy",
    "graph": "Graphs",
    "graphs": "Graphs",
    "tree": "Trees",
    "trees": "Trees",
    "dfs": "Depth First Search",
    "depth first search": "Depth First Search",
    "depth-first search": "Depth First Search",
    "bfs": "Breadth First Search",
    "breadth first search": "Breadth First Search",
    "breadth-first search": "Breadth First Search",
    "backtracking": "Backtracking",
    "recursion": "Recursion",
    "bit manipulation": "Bit Manipulation",
    "bit-manipulation": "Bit Manipulation",
    "heap": "Heaps",
    "heaps": "Heaps",
    "priority queue": "Heaps",
    "priority-queue": "Heaps",
    "stack": "Stacks",
    "stacks": "Stacks",
    "queue": "Queues",
    "queues": "Queues",
    "linked list": "Linked Lists",
    "linked-list": "Linked Lists",
    "trie": "Tries",
    "union find": "Disjoint Set Union",
    "union-find": "Disjoint Set Union",
    "dsu": "Disjoint Set Union",
    "segment tree": "Segment Trees",
    "segment-tree": "Segment Trees",
    "database": "Databases",
    "sql": "SQL",
    "oop": "Object Oriented Programming",
    "object oriented programming": "Object Oriented Programming",
}

# --- Cross-platform vocabulary (Codeforces / LeetCode / GeeksforGeeks / CodeChef spellings) ---
# Keys must be lower-case with SPACES (see _key). Add new platform tags here.
_ALIASES.update({
    # graphs
    "graph theory": "Graphs",
    "dfs and similar": "Depth First Search",
    "shortest path": "Shortest Path",
    "shortest paths": "Shortest Path",
    "topological sort": "Topological Sort",
    # bits
    "bitmask": "Bit Manipulation",
    "bitmasks": "Bit Manipulation",
    "bit mask": "Bit Manipulation",
    # hashing
    "hash table": "Hash Table",
    "hash map": "Hash Table",
    "hashmap": "Hash Table",
    "hashing": "Hash Table",
    # sorting / heaps / misc spelling differences
    "sortings": "Sorting",
    "heap (priority queue)": "Heaps",
    "tries": "Tries",
    "disjoint set": "Disjoint Set Union",
    "disjoint set union": "Disjoint Set Union",
    "doubly linked list": "Linked Lists",
    "linked lists": "Linked Lists",
    "matrix": "Matrix",
    "matrices": "Matrix",
    "probabilities": "Probability",
    "probability": "Probability",
    "games": "Game Theory",
    "game theory": "Game Theory",
    "binary indexed tree": "Fenwick Tree",
    "fenwick tree": "Fenwick Tree",
    "2 sat": "2-SAT",
})
# NOTE: "number theory" is deliberately NOT merged into "Math" - Codeforces and LeetCode both treat
# them as separate tags. Merge them here too if you want one combined row.


def _key(tag: str) -> str:
    # Underscores AND hyphens are treated as spaces, so "divide-and-conquer" and
    # "divide and conquer" always land on the same topic (alias keys below use spaces).
    value = tag.strip().lower().replace("_", " ").replace("-", " ")
    value = re.sub(r"\s+", " ", value)
    return value


def normalize_topic(tag_name: str) -> str:
    """Map common aliases to one canonical label; preserve unknown tags."""
    key = _key(tag_name)
    if not key:
        return "Uncategorized"
    if key in _ALIASES:
        return _ALIASES[key]
    # Preserve unknown tags rather than silently losing information.
    return " ".join(word.upper() if word in {"sql", "api", "oop"} else word.capitalize() for word in key.split())
