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
        self.assertIn("https://creativecommons.org/licenses/by/4.0/", fences)

    def test_deployment_publishes_only_site(self):
        workflow = (ROOT / ".github/workflows/pages.yml").read_text()
        self.assertIn("path: site\n", workflow)
        self.assertNotIn("path: .\n", workflow)
        self.assertIn("branches: [main]", workflow)
