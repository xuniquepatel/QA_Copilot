import re, random
random.seed(1337)

def boundary_values_from_predicates(preds: list[str]):
    """Regex constants; add ±1 boundaries; include generic edges."""
    candidates = set()
    for p in preds or []:
        for m in re.finditer(r"(-?\d+)", p):
            n = int(m.group(1))
            candidates.update([n-1, n, n+1])
    candidates.update([0, 1, -1])
    return sorted(set(candidates))[:8]
