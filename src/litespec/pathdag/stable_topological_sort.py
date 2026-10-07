"""Stable topological sort of a path DAG (D80)."""

from __future__ import annotations

import heapq
from typing import Any, Sequence


def stable_topological_sort(nodes: Sequence[Any]) -> list[Any]:
    """Order ``nodes`` so parents precede children; ties broken by insertion order.

    Each node exposes ``node_id`` and ``parent`` (``None`` for the root). Raises
    ``ValueError`` on a cycle.
    """
    insertion_index = {n.node_id: i for i, n in enumerate(nodes)}
    indegree: dict[str, int] = {n.node_id: 0 for n in nodes}
    children: dict[str, list[str]] = {n.node_id: [] for n in nodes}
    id_to_node = {n.node_id: n for n in nodes}

    for n in nodes:
        if n.parent is not None:
            if n.parent not in id_to_node:
                raise ValueError(f"path DAG node {n.node_id!r} references unknown parent {n.parent!r}")
            indegree[n.node_id] += 1
            children[n.parent].append(n.node_id)

    heap = [(insertion_index[n.node_id], n.node_id) for n in nodes if indegree[n.node_id] == 0]
    heapq.heapify(heap)

    result: list[Any] = []
    while heap:
        _, nid = heapq.heappop(heap)
        result.append(id_to_node[nid])
        for child in children[nid]:
            indegree[child] -= 1
            if indegree[child] == 0:
                heapq.heappush(heap, (insertion_index[child], child))

    if len(result) != len(nodes):
        raise ValueError("cycle detected in path DAG")
    return result
