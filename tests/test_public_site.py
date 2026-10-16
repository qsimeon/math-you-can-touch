"""Public pages remain self-contained and visitor-facing."""
import unittest
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]


class References(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = []
        self.links = []

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag in ("script", "img") and attrs.get("src"):
            self.assets.append(attrs["src"])
        if tag == "link" and attrs.get("href"):
            self.assets.append(attrs["href"])
        if tag == "a" and attrs.get("href"):
            self.links.append(attrs["href"])


class PublicSiteTests(unittest.TestCase):
    def test_runtime_assets_and_relative_links_exist(self):
        for page in (ROOT / "site").glob("*.html"):
            parsed = References()
            parsed.feed(page.read_text())
            for asset in parsed.assets:
                self.assertFalse(urlsplit(asset).scheme, (page.name, asset))
            for link in parsed.assets + parsed.links:
                url = urlsplit(link)
                if not url.scheme and url.path:
                    self.assertFalse(url.path.startswith("/"), (page.name, link))
                    self.assertTrue((page.parent / url.path).is_file(), (page.name, link))

    def test_visitor_copy_has_no_private_release_status(self):
        for name in ("index.html", "fences.html", "beaver.html", "site.js"):
            text = (ROOT / "site" / name).read_text()
            for phrase in ("private source repository", "Formal status:", "official Autolab", "Lean proof"):
                self.assertNotIn(phrase, text, name)

    def test_public_copy_marks_checker_limits_and_sources(self):
        beaver = (ROOT / "site/beaver.html").read_text()
        index = (ROOT / "site/index.html").read_text()
        fences = (ROOT / "site/fences.html").read_text()
        self.assertIn("Unresolved at 100", beaver)
        self.assertIn("https://oeis.org/A060843", beaver)
        self.assertIn("https://oeis.org/A060843", index)
        self.assertIn("per-change logs", index)
        self.assertIn("Pavlo Savchuk", fences)
        self.assertIn("kobon_18_93tri_lines.svg", fences)
        self.assertIn("https://creativecommons.org/licenses/by/4.0/", fences)
        data = (ROOT / "site/data.js").read_text()
        self.assertIn("line-order/blob/2631b8793eb351be2ad6b8a91b7194eeb67e25bb/README.md", data)

    def test_research_lesson_has_exact_gap_and_scope(self):
        index = (ROOT / "site/index.html").read_text()
        research = (ROOT / "docs/RESEARCH.md").read_text()
        readme = (ROOT / "README.md").read_text()
        for phrase in ("58 bounded fence segments", "only three", "136 triangle outlines",
                       "only 16 undivided yards", "docs/RESEARCH.md"):
            self.assertIn(phrase, index)
        for phrase in ("288 - 2p", "U = E - 3T", "triple intersections",
                       "checked computation that no mathematician has yet reviewed", "5,912", "20,736 fully labeled"):
            self.assertIn(phrase.lower(), research.lower())
        self.assertIn("tests.test_segment_audit", readme)

    def test_deployment_publishes_only_site(self):
        workflow = (ROOT / ".github/workflows/pages.yml").read_text()
        self.assertIn("path: site\n", workflow)
        self.assertNotIn("path: .\n", workflow)
        self.assertIn("branches: [main]", workflow)
