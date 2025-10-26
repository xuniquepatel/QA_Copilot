import pathlib
from lxml import etree

class CoverageReader:
    def __init__(self, repo_root: pathlib.Path, coverage_xml_path: str | None):
        self.repo_root = repo_root
        self.coverage_xml_path = pathlib.Path(coverage_xml_path) if coverage_xml_path else None

    def load(self):
        """Return {'covered': {file: set(lines)}, 'totals': {file: total_lines}}."""
        covered, totals = {}, {}
        if not self.coverage_xml_path or not self.coverage_xml_path.exists():
            return {"covered": covered, "totals": totals}
        tree = etree.parse(str(self.coverage_xml_path))
        for cls in tree.findall('.//class'):
            filename = cls.get('filename')
            if not filename:
                continue
            path = (self.repo_root / filename).resolve()
            cov_lines = set()
            total = 0
            for line in cls.findall('.//line'):
                num = int(line.get('number'))
                hits = int(line.get('hits'))
                total += 1
                if hits > 0:
                    cov_lines.add(num)
            covered[str(path)] = cov_lines
            totals[str(path)] = total
        return {"covered": covered, "totals": totals}
