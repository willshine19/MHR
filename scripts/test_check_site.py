import tempfile
import unittest
from pathlib import Path

from check_site import check_site


def page(nav_prefix, body):
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>测试</title>
</head>
<body>
<nav class="site-nav"><a href="{nav_prefix}index.html">首页</a><a href="{nav_prefix}builds/mr2.html">配装</a><a href="{nav_prefix}about.html">关于</a></nav>
{body}
</body>
</html>
"""


CONTENT_BODY = """<h1 id="top">配装</h1>
<p class="page-meta">MR 2★ · Ver.16.0.2（Kiranico v16.0.0）· 2026-09-30 核对</p>
<section class="sources"><h2>资料来源</h2><ul><li><a href="https://mhrise.kiranico.com/zh">Kiranico</a></li></ul></section>"""


class CheckSiteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name).resolve()
        (self.site / "builds").mkdir()
        self.write("index.html", page("", '<a href="builds/mr2.html#top">配装</a>'))
        self.write("about.html", page("", "<p>关于</p>"))
        self.write("builds/mr2.html", page("../", CONTENT_BODY))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        (self.site / rel).write_text(text, encoding="utf-8")

    def assertError(self, keyword):
        errors = check_site(self.site)
        self.assertTrue(any(keyword in e for e in errors), errors)

    def test_valid_site_passes(self):
        self.assertEqual(check_site(self.site), [])

    def test_root_absolute_path_rejected(self):
        self.write("about.html", page("", '<a href="/builds/mr2.html">配装</a>'))
        self.assertError("以 / 开头")

    def test_missing_target_rejected(self):
        self.write("about.html", page("", '<a href="builds/mr3.html">MR3</a>'))
        self.assertError("目标不存在")

    def test_missing_anchor_rejected(self):
        self.write("about.html", page("", '<a href="builds/mr2.html#nope">锚点</a>'))
        self.assertError("锚点不存在")

    def test_http_link_rejected(self):
        self.write("about.html", page("", '<a href="http://example.com">外链</a>'))
        self.assertError("https")

    def test_forbidden_term_rejected(self):
        self.write("about.html", page("", "<p>傀异炼成</p>"))
        self.assertError("非官方译名「傀异」")

    def test_wrong_term_example_allowed(self):
        self.write("about.html", page("", '<p>写「怪异炼化」，不写<del class="wrong-term">傀异炼成</del></p>'))
        self.assertEqual(check_site(self.site), [])

    def test_content_page_requires_meta(self):
        self.write("builds/mr2.html", page("../", CONTENT_BODY.replace("2026-09-30 核对", "")))
        self.assertError("page-meta")

    def test_content_page_requires_sources(self):
        self.write("builds/mr2.html", page("../", CONTENT_BODY.replace("https://mhrise.kiranico.com/zh", "#top")))
        self.assertError("资料来源")

    def test_nav_must_match(self):
        self.write("about.html", page("", "").replace('builds/mr2.html">配装', 'about.html">配装'))
        self.assertError("导航")

    def test_lang_required(self):
        self.write("about.html", page("", "").replace(' lang="zh-CN"', ""))
        self.assertError("lang")


if __name__ == "__main__":
    unittest.main()
