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
<nav class="site-nav"><a href="{nav_prefix}index.html">首页</a><a href="{nav_prefix}builds/index.html">配装</a><a href="{nav_prefix}monsters/index.html">怪物</a><a href="{nav_prefix}about.html">关于</a></nav>
{body}
</body>
</html>
"""


CONTENT_BODY = """<h1 id="top">配装</h1>
<p class="page-meta">MR 2★ · Ver.16.0.2（Kiranico v16.0.0）· 2026-09-30 核对</p>
<details class="toc"><summary>本页目录</summary><ol><li><a href="#skills">技能</a></li><li><a href="#sources">资料来源</a></li></ol></details>
<h2 id="skills">技能优先级</h2>
<section class="sources"><h2 id="sources">资料来源</h2><ul><li><a href="https://mhrise.kiranico.com/zh">Kiranico</a></li></ul></section>"""

# 离线缓存用的 head 标签，路径相对站点根目录
PWA_HEAD = """<link rel="manifest" href="{p}manifest.webmanifest">
<script src="{p}assets/js/sw-register.js" defer></script>
"""


class CheckSiteTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.site = Path(self.tmp.name).resolve()
        (self.site / "builds").mkdir()
        self.write("index.html", page("", '<a href="builds/lance-mr2.html#top">配装</a>'))
        self.write("about.html", page("", "<p>关于</p>"))
        self.write("builds/index.html", page("../", '<a href="lance-mr2.html">长枪 MR 2★</a>'))
        self.write("builds/lance-mr2.html", page("../", CONTENT_BODY))
        (self.site / "monsters").mkdir()
        self.write("monsters/index.html", page("../", "<h1>怪物</h1>"))

    def tearDown(self):
        self.tmp.cleanup()

    def write(self, rel, text):
        (self.site / rel).write_text(text, encoding="utf-8")

    def enable_pwa(self, skip_head=(), precache=None):
        """给测试站点加上离线缓存：每页补 head 标签，sw.js 的 PRECACHE 默认列出全部文件。"""
        (self.site / "assets/js").mkdir(parents=True)
        (self.site / "assets/icons").mkdir()
        self.write("assets/js/sw-register.js", "")
        self.write("assets/icons/icon.png", "")
        self.write("manifest.webmanifest", '{"start_url": "index.html", "icons": [{"src": "assets/icons/icon.png"}]}')
        for page in self.site.rglob("*.html"):
            rel = page.relative_to(self.site).as_posix()
            if rel not in skip_head:
                head = PWA_HEAD.format(p="../" * rel.count("/"))
                page.write_text(page.read_text(encoding="utf-8").replace("</head>", head + "</head>"), encoding="utf-8")
        if precache is None:
            precache = sorted(p.relative_to(self.site).as_posix() for p in self.site.rglob("*") if p.is_file())
        self.write("sw.js", 'const VERSION = "dev";\nconst PRECACHE = [\n' + "".join(f'  "{f}",\n' for f in precache) + "];\n")

    def assertError(self, keyword):
        errors = check_site(self.site)
        self.assertTrue(any(keyword in e for e in errors), errors)

    def test_valid_site_passes(self):
        self.assertEqual(check_site(self.site), [])

    def test_root_absolute_path_rejected(self):
        self.write("about.html", page("", '<a href="/builds/lance-mr2.html">配装</a>'))
        self.assertError("以 / 开头")

    def test_missing_target_rejected(self):
        self.write("about.html", page("", '<a href="builds/mr3.html">MR3</a>'))
        self.assertError("目标不存在")

    def test_missing_anchor_rejected(self):
        self.write("about.html", page("", '<a href="builds/lance-mr2.html#nope">锚点</a>'))
        self.assertError("锚点不存在")

    def test_http_link_rejected(self):
        self.write("about.html", page("", '<a href="http://example.com">外链</a>'))
        self.assertError("https")

    def test_forbidden_term_rejected(self):
        self.write("about.html", page("", "<p>傀异炼成</p>"))
        self.assertError("非官方译名「傀异」")

    def test_forbidden_term_traditional_glyphs_rejected(self):
        self.write("about.html", page("", "<p>傀異鍊成、怪異調查</p>"))
        self.assertError("非官方译名「傀異」")
        self.assertError("非官方译名「怪異調查」")

    def test_wrong_term_example_allowed(self):
        self.write("about.html", page("", '<p>写「怪异炼化」，不写<del class="wrong-term">傀异炼成</del></p>'))
        self.assertEqual(check_site(self.site), [])

    def test_section_index_is_not_content_page(self):
        self.write("builds/index.html", page("../", "<h1>配装</h1>"))
        self.assertEqual(check_site(self.site), [])

    def test_top_fragment_needs_no_element(self):
        self.write("about.html", page("", '<a href="builds/index.html#top">回到顶部</a>'))
        self.assertEqual(check_site(self.site), [])

    def test_content_page_requires_toc(self):
        body = CONTENT_BODY.replace('<details class="toc">', "<div>").replace("</details>", "</div>")
        self.write("builds/lance-mr2.html", page("../", body))
        self.assertError("本页目录")

    def test_toc_must_list_every_h2(self):
        self.write("builds/lance-mr2.html", page("../", CONTENT_BODY + '<h2 id="weapons">武器</h2>'))
        self.assertError("本页目录应依次链接到全部 h2")

    def test_content_h2_requires_id(self):
        self.write("builds/lance-mr2.html", page("../", CONTENT_BODY + "<h2>武器</h2>"))
        self.assertError("<h2> 都要有 id")

    def test_pwa_site_passes(self):
        self.enable_pwa()
        self.assertEqual(check_site(self.site), [])

    def test_pwa_page_requires_head_tags(self):
        self.enable_pwa(skip_head={"about.html"})
        self.assertError("about.html: <head> 缺少离线缓存")

    def test_precache_must_list_new_file(self):
        self.enable_pwa(precache=["index.html"])
        self.assertError("PRECACHE 缺少 builds/lance-mr2.html")

    def test_precache_rejects_missing_file(self):
        self.enable_pwa()
        (self.site / "builds/lance-mr2.html").unlink()
        self.write("builds/index.html", page("../", "<h1>配装</h1>"))
        self.assertError("PRECACHE 里的 builds/lance-mr2.html 不存在")

    def test_sw_version_placeholder_required(self):
        self.enable_pwa()
        sw = self.site / "sw.js"
        sw.write_text(sw.read_text(encoding="utf-8").replace('"dev"', '"abc1234"'), encoding="utf-8")
        self.assertError('要保留单独一行 const VERSION = "dev";')

    def test_manifest_icon_must_exist(self):
        self.enable_pwa()
        (self.site / "assets/icons/icon.png").unlink()
        self.assertError("manifest.webmanifest: 文件不存在：assets/icons/icon.png")

    def test_redirects_valid(self):
        self.write("_redirects", "# 注释\n/ /index.html 200\n/:dir/ /:dir/index.html 200\n/builds/mr2.html /builds/lance-mr2.html 301\n")
        self.assertEqual(check_site(self.site), [])

    def test_redirect_target_must_exist(self):
        self.write("_redirects", "/builds/mr2.html /builds/mr9.html 301\n")
        self.assertError("目标不存在：/builds/mr9.html")

    def test_redirect_source_must_not_be_existing_page(self):
        self.write("_redirects", "/about.html /index.html 301\n")
        self.assertError("来源 /about.html 是现有文件")

    def add_monster(self, slug="rathalos", icon=None, card=None):
        """加一个怪物页和它的图标，列表页放一张链接到它的卡片。"""
        (self.site / "assets/img/monsters").mkdir(parents=True, exist_ok=True)
        self.write(f"assets/img/monsters/{slug}.webp", "")
        if icon is None:
            icon = f'<img class="monster-icon" src="../assets/img/monsters/{slug}.webp" alt="火龙的游戏内图标" width="192" height="192">'
        if card is None:
            card = (f'<a class="card monster-card" href="{slug}.html">'
                    f'<img class="card-icon" src="../assets/img/monsters/{slug}.webp" alt="" width="192" height="192">'
                    f'<span><strong>火龙</strong></span></a>')
        self.write(f"monsters/{slug}.html", page("../", CONTENT_BODY.replace('<details', f'<p class="lead">{icon}介绍</p><details')))
        self.write("monsters/index.html", page("../", f"<h1>怪物</h1>{card}"))

    def test_monster_with_icons_passes(self):
        self.add_monster()
        self.assertEqual(check_site(self.site), [])

    def test_monster_page_requires_icon(self):
        self.add_monster(icon="")
        self.assertError('monsters/rathalos.html: 怪物页缺少 <img class="monster-icon">')

    def test_monster_icon_must_match_page(self):
        self.add_monster("tigrex")
        self.add_monster(icon='<img class="monster-icon" src="../assets/img/monsters/tigrex.webp" alt="火龙的游戏内图标" width="192" height="192">')
        self.assertError("monsters/rathalos.html: 怪物图标应为 assets/img/monsters/rathalos.webp")

    def test_monster_icon_requires_alt_text(self):
        self.add_monster(icon='<img class="monster-icon" src="../assets/img/monsters/rathalos.webp" alt="" width="192" height="192">')
        self.assertError("怪物图标的 alt 要写明是哪只怪物")

    def test_monster_card_requires_icon(self):
        self.add_monster(card='<a class="card" href="rathalos.html"><strong>火龙</strong></a>')
        self.assertError("monsters/index.html: 链接到 rathalos.html 的卡片缺少图标 assets/img/monsters/rathalos.webp")

    def test_img_requires_size(self):
        self.write("about.html", page("", '<img src="index.html" alt="">'))
        self.assertError("<img> 要写 width 和 height")

    def test_img_requires_alt(self):
        self.write("about.html", page("", '<img src="index.html" width="1" height="1">'))
        self.assertError("<img> 要写 alt")

    def test_content_page_requires_meta(self):
        self.write("builds/lance-mr2.html", page("../", CONTENT_BODY.replace("2026-09-30 核对", "")))
        self.assertError("page-meta")

    def test_content_page_requires_sources(self):
        self.write("builds/lance-mr2.html", page("../", CONTENT_BODY.replace("https://mhrise.kiranico.com/zh", "#top")))
        self.assertError("资料来源")

    def test_nav_must_match(self):
        self.write("about.html", page("", "").replace('builds/index.html">配装', 'about.html">配装'))
        self.assertError("导航")

    def test_lang_required(self):
        self.write("about.html", page("", "").replace(' lang="zh-CN"', ""))
        self.assertError("lang")


if __name__ == "__main__":
    unittest.main()
