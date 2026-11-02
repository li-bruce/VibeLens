"""Bounded typed-path queries and expansion of registered summary witnesses."""

from collections import deque

from .contract import context_key


class SearchLimit(Exception):
    """Retain a claim when the configured reasoning budget is exhausted."""


class Budget:
    def __init__(self, maximum):
        self.remaining = maximum

    def spend(self):
        self.remaining -= 1
        if self.remaining < 0:
            raise SearchLimit


def adjacency(entries, active, context, relations, budget):
    result = {}
    for ident in sorted(active):
        budget.spend()
        item = entries[ident]
        if item.get("relation") in relations and context_key(item) == context:
            result.setdefault(item["edge"]["from"], []).append(item)
    return result


def path(graph, start, end, budget, sequence=None, *, excluded=None, repeat=None):
    """Find a directed witness using exact relation types and actual endpoint IDs."""
    pending = deque([(start, 0)])
    parents = {(start, 0): None}
    final = None
    while pending:
        node, depth = pending.popleft()
        budget.spend()
        if node == end and (depth == len(sequence) if sequence else depth >= 2):
            final = (node, depth)
            break
        if sequence and depth >= len(sequence):
            continue
        for item in graph.get(node, ()):
            budget.spend()
            edge = item["edge"]
            if edge["id"] == excluded or (sequence and item.get("relation") != sequence[depth]):
                continue
            if sequence is None and item.get("relation") != repeat:
                continue
            # Unbounded transitive queries only need to distinguish one hop from
            # two or more hops; fixed compositions retain their exact position.
            following = (edge["to"], depth + 1 if sequence else min(2, depth + 1))
            if following not in parents:
                parents[following] = ((node, depth), edge["id"])
                pending.append(following)
    if final is None:
        return None
    witness = []
    while parents[final] is not None:
        final, ident = parents[final]
        witness.append(ident)
    return list(reversed(witness))


def reachable(graph, start, end, budget, *, excluded):
    """A cycle inside this relation family prevents its contraction."""
    pending = [start]
    seen = set()
    while pending:
        node = pending.pop()
        budget.spend()
        if node == end:
            return True
        if node in seen:
            continue
        seen.add(node)
        for item in graph.get(node, ()):
            if item["edge"]["id"] != excluded:
                pending.append(item["edge"]["to"])
    return False


def leaf_path(ident, decisions, maximum):
    """Expand later-elided witness edges without recursion or invented edges."""
    pending = [(ident, frozenset())]
    output = []
    budget = Budget(maximum)
    while pending:
        budget.spend()
        key, ancestors = pending.pop()
        if key in ancestors:
            raise ValueError("Cyclic relation witness definitions")
        decision = decisions[key]
        if decision["status"] == "represented":
            pending.extend((child, ancestors | {key}) for child in reversed(decision["path"]))
        elif decision["status"] == "duplicate":
            pending.append((decision["duplicate_of"], ancestors | {key}))
        else:
            output.append(key)
    return output
