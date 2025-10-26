def score_targets(targets, complexity, churn):
    """Return targets with 'risk' using a weighted score."""
    ranked = []
    for t in targets:
        file = t['file']; fn = t['function']
        cc = 0.0
        try:
            for entry in complexity.get(file, []):
                if entry.get('name') == fn:
                    cc = float(entry.get('complexity', 0))
                    break
        except Exception:
            cc = 0.0
        ch = float(churn.get(file, 0))
        missing = len(t['uncovered'])
        risk = 0.45*(min(1.0, missing/20)) + 0.25*(min(1.0, cc/10)) + 0.20*(min(1.0, ch/20))
        t2 = dict(t); t2['risk'] = risk
        ranked.append(t2)
    ranked.sort(key=lambda x: x['risk'], reverse=True)
    return ranked
