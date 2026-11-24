"""Static site checks, runnable with python3 -m unittest tests/test_site.py."""

from html.parser import HTMLParser
from pathlib import Path
import re
import unittest
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[1]
APPS = ("ads-invoices", "pigeon")
PAGES = ("index.html", "privacy.html", "terms.html")
VOID_ELEMENTS = {
    "area", "base", "br", "col", "embed", "hr", "img", "input", "link",
    "meta", "param", "source", "track", "wbr",
}


class PageParser(HTMLParser):
    """Collect links and enforce explicit, balanced markup for this minimal site."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.doctypes = []
        self.elements = []
        self.links = []
        self.stack = []
        self.errors = []

    def handle_decl(self, decl):
        self.doctypes.append(decl.lower())

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.elements.append((tag, attrs, tuple(self.stack)))
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        if tag not in VOID_ELEMENTS:
            self.stack.append(tag)

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)
        if tag not in VOID_ELEMENTS:
            self.handle_endtag(tag)

    def handle_endtag(self, tag):
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()
        else:
            self.errors.append(f"Unexpected closing tag </{tag}>")


def parse_page(path):
    parser = PageParser()
    parser.feed(path.read_text(encoding="utf-8"))
    parser.close()
    return parser


def local_destination(source, href):
    """Resolve paths from the source page or site root, ignoring query/fragment."""
    url = urlsplit(href)
    if url.scheme or url.netloc:
        return None
    path = unquote(url.path)
    if not path:
        return source
    base = ROOT if path.startswith("/") else source.parent
    return (base / path.lstrip("/")).resolve()


class SiteTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.html_files = sorted(
            path for path in ROOT.rglob("*.html")
            if not any(part.startswith(".") for part in path.relative_to(ROOT).parts)
        )

    def test_html_syntax_and_structure(self):
        self.assertTrue(self.html_files, "No HTML files found")
        for path in self.html_files:
            with self.subTest(page=str(path.relative_to(ROOT))):
                parser = parse_page(path)
                # Google's verification endpoint must remain a plain-text token.
                if path.parent == ROOT and re.fullmatch(r"google[0-9a-f]+\.html", path.name):
                    self.assertEqual(
                        path.read_text(encoding="utf-8").strip(),
                        f"google-site-verification: {path.name}",
                    )
                    continue
                self.assertIn("doctype html", parser.doctypes)
                self.assertEqual(parser.errors, [])
                self.assertEqual(parser.stack, [], "Unclosed HTML tags")
                for tag in ("html", "head", "title", "body"):
                    matches = [element for element in parser.elements if element[0] == tag]
                    self.assertEqual(len(matches), 1, f"Expected one <{tag}>")
                    expected_parent = {"html": (), "head": ("html",),
                                       "title": ("html", "head"), "body": ("html",)}
                    self.assertEqual(matches[0][2], expected_parent[tag])
                self.assertTrue(any(
                    tag == "html" and attrs.get("lang") == "en"
                    for tag, attrs, _ in parser.elements
                ))
                head_elements = [
                    (tag, attrs) for tag, attrs, parents in parser.elements
                    if parents == ("html", "head")
                ]
                self.assertTrue(any(
                    tag == "meta" and attrs.get("charset", "").lower() == "utf-8"
                    for tag, attrs in head_elements
                ), "Missing UTF-8 charset")
                self.assertTrue(any(
                    tag == "meta" and attrs.get("name", "").lower() == "viewport"
                    and "width=device-width" in attrs.get("content", "")
                    for tag, attrs in head_elements
                ), "Missing responsive viewport")
                self.assertTrue(any(
                    tag == "link" and attrs.get("rel") == "stylesheet"
                    and local_destination(path, attrs.get("href", "")) == ROOT / "style.css"
                    for tag, attrs in head_elements
                ), "Missing shared stylesheet")

    def test_internal_links_resolve(self):
        for path in self.html_files:
            for href in parse_page(path).links:
                with self.subTest(page=str(path.relative_to(ROOT)), href=href):
                    self.assertIsNotNone(href, "Anchor href must have a value")
                    destination = local_destination(path, href)
                    if destination is None:
                        continue
                    self.assertTrue(destination.is_relative_to(ROOT), "Link escapes site root")
                    if destination.is_dir():
                        destination /= "index.html"
                    self.assertTrue(destination.is_file(), f"Missing link target: {destination}")

    def test_apps_have_complete_pages(self):
        for app in (*APPS, "_template"):
            for page in PAGES:
                with self.subTest(app=app, page=page):
                    self.assertTrue((ROOT / app / page).is_file())

    def test_template_placeholders(self):
        for page in PAGES:
            with self.subTest(page=page):
                self.assertIn("APP_NAME", (ROOT / "_template" / page).read_text(encoding="utf-8"))

    def test_external_links_use_https(self):
        for path in self.html_files:
            for href in parse_page(path).links:
                with self.subTest(page=str(path.relative_to(ROOT)), href=href):
                    url = urlsplit(href)
                    if url.scheme in ("http", "https") or url.netloc:
                        self.assertEqual(url.scheme, "https")
                        self.assertTrue(href.startswith("https://"))
                        self.assertTrue(url.hostname, "External URL needs a hostname")

    def test_404_page(self):
        path = ROOT / "404.html"
        self.assertTrue(path.is_file())
        parser = parse_page(path)
        destinations = {local_destination(path, href) for href in parser.links}
        for destination in (ROOT, *(ROOT / app for app in APPS)):
            with self.subTest(destination=str(destination.relative_to(ROOT))):
                self.assertIn(destination, destinations)
        content = path.read_text(encoding="utf-8")
        self.assertIn("<title>Page Not Found · Personal Apps</title>", content)
        self.assertIn("<h1>Page not found</h1>", content)
        self.assertIn("https://github.com/youngkwangk/youngkwangk.github.io/issues", parser.links)


if __name__ == "__main__":
    unittest.main()
