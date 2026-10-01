# 站点骨架与第一页 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建好 `site/` 静态站点骨架（首页、关于页、共用样式），写出第一页「长枪配装：MR 2★」，并配好检查脚本和 GitHub Pages 部署工作流。

**Architecture:** 纯手写 HTML + 一个共用 CSS，不用 JS、不用构建工具。`scripts/check_site.py` 负责检查链接、路径、页面约定和译名，本地和 CI 都跑它。GitHub Actions 只把 `site/` 目录发布到 Pages。

**Tech Stack:** HTML、CSS、Python 3 标准库（检查脚本和 unittest）、GitHub Actions（checkout@v7、configure-pages@v6、upload-pages-artifact@v5、deploy-pages@v5）。

**Spec:** `docs/specs/2026-09-30-site-structure-design.md`；内容规则见 `CLAUDE.md`。

## Global Constraints

- 全站简体中文；名称一律采用游戏内简中官方译名（以 Kiranico `/zh` 为准）。不写「傀异」「原初爵银龙」「原初爵銀龍」「怪异调查」「加工屋」「铁虫丝技」。
- 数据基准 Switch 版 Ver.16.0.2；数值与 Kiranico v16.0.0 一致。
- 站内链接和资源一律用相对路径，不能以 `/` 开头；外链用 `https://`。
- 文件名和目录用英文小写 kebab-case。
- 每页：`<html lang="zh-CN">`、viewport meta、非空 `<title>`、顶部 `<nav class="site-nav">` 依次链接 首页 `index.html` / 配装 `builds/mr2.html` / 关于 `about.html`。
- 内容页（`site/` 子目录下的页面）：标题下有 `<p class="page-meta">`，包含「Ver.16.0.2」和「YYYY-MM-DD 核对」；底部有 `<section class="sources">`，至少一个 `https://` 外链。
- 正文最大宽度 720px 居中，两侧 16px 边距；375px 宽度下页面不出现横向滚动；支持 `prefers-color-scheme: dark`。
- 所有 git 操作在分支 `site-skeleton` 上进行，不直接提交到 `main`。

## Review Focus

1. 在 375px 宽的手机上打开有宽表格的页面：表格在自己的容器里横向滚动，整页不出现横向滚动条。（Task 2、Task 3 的浏览器检查）
2. 站点部署在 `/<仓库名>/` 子路径下：所有站内链接依然能打开。（检查脚本拒绝以 `/` 开头的路径；Task 2、Task 3 从仓库根目录起服务，在 `/site/` 子路径下逐个请求链接）
3. 系统切到深色模式：文字、表格、提示框都清晰可读。（Task 2、Task 3 的深色模式截图检查）
4. 以后写新内容时混进非官方译名：检查脚本报错，除非用 `<del class="wrong-term">` 标成反例。（Task 1 的单元测试）
5. 页面上的防具技能、孔位、珠子、武器数值与 Kiranico 不一致。（Task 3 的数据核对步骤）

---

### Task 1: 检查脚本

**Files:**
- Create: `scripts/check_site.py`
- Test: `scripts/test_check_site.py`

**Interfaces:**
- Consumes: 无
- Produces: `check_site(site: pathlib.Path) -> list[str]`，参数是已经 `resolve()` 过的站点目录，返回错误信息列表（空表示通过）；命令行 `python3 scripts/check_site.py [站点目录，默认 site]`，有问题时以状态码 1 退出。错误信息中的关键词：「以 / 开头」「目标不存在」「锚点不存在」「https」「非官方译名」「page-meta」「资料来源」「导航」「lang」。

- [ ] **Step 1: 建分支**

```bash
git checkout -b site-skeleton
```

- [ ] **Step 2: 写失败的测试**

创建 `scripts/test_check_site.py`：

```python
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
```

- [ ] **Step 3: 运行测试，确认失败**

Run: `python3 -m unittest discover -s scripts -v`
Expected: 报错 `ModuleNotFoundError: No module named 'check_site'`

- [ ] **Step 4: 实现检查脚本**

创建 `scripts/check_site.py`：

```python
#!/usr/bin/env python3
"""检查 site/ 下的静态页面。

用法：python3 scripts/check_site.py [站点目录，默认 site]

检查项：站内链接和锚点能打开、不用以 / 开头的路径、外链用 https、
页面基本结构（lang、viewport、title、导航）、内容页的元信息和资料来源、
非官方译名。有问题时逐条列出，并以状态码 1 退出。
"""
import re
import sys
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit

# 非官方译名 -> 说明。页面里作为反例展示时，用 <del class="wrong-term">…</del> 包起来即可豁免。
FORBIDDEN_TERMS = {
    "傀异": "简中官方译名是「怪异」（怪异炼化、怪异克服）",
    "原初爵银龙": "简中官方译名是「原初形态爵银龙」",
    "原初爵銀龍": "这是繁中译名，简中官方译名是「原初形态爵银龙」",
    "怪异调查": "简中官方译名是「怪异探究任务」",
    "加工屋": "简中官方译名是「加工店」",
}
NAV_TARGETS = ["index.html", "builds/mr2.html", "about.html"]
META_VERSION = "Ver.16.0.2"
META_DATE = re.compile(r"\d{4}-\d{2}-\d{2} 核对")
WRONG_TERM = re.compile(r'<del class="wrong-term">.*?</del>', re.S)
TAG = re.compile(r"<[^>]+>")
VOID_TAGS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.lang = None
        self.has_viewport = False
        self.title = ""
        self.meta_text = ""
        self.ids = set()
        self.links = []
        self.nav_links = []
        self.source_links = []
        self._stack = []  # (标签名, 标记)，标记是 nav / sources / meta / title 或 None

    def _context(self):
        return {marker for _, marker in self._stack if marker}

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        classes = (a.get("class") or "").split()
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "html":
            self.lang = a.get("lang")
        if tag == "meta" and a.get("name") == "viewport":
            self.has_viewport = True
        url = a.get("href") if tag in ("a", "link") else a.get("src") if tag in ("img", "script") else None
        if url is not None:
            context = self._context()
            self.links.append(url)
            if "nav" in context:
                self.nav_links.append(url)
            if "sources" in context and tag == "a":
                self.source_links.append(url)
        if tag in VOID_TAGS:
            return
        marker = None
        if tag == "nav" and "site-nav" in classes:
            marker = "nav"
        elif tag == "section" and "sources" in classes:
            marker = "sources"
        elif tag == "p" and "page-meta" in classes:
            marker = "meta"
        elif tag == "title":
            marker = "title"
        self._stack.append((tag, marker))

    def handle_endtag(self, tag):
        for i in range(len(self._stack) - 1, -1, -1):
            if self._stack[i][0] == tag:
                del self._stack[i:]
                break

    def handle_data(self, data):
        context = self._context()
        if "title" in context:
            self.title += data
        if "meta" in context:
            self.meta_text += data


def resolve_link(url, page, site):
    """把站内相对链接解析成 (目标文件, 锚点)。"""
    parts = urlsplit(url)
    target = (page.parent / parts.path).resolve() if parts.path else page
    if target.is_dir():
        target = target / "index.html"
    return target, parts.fragment


def check_link(url, page, site, parsed, err):
    if url.startswith(("https://", "mailto:")):
        return
    if url.startswith("http://"):
        err(f"外链请用 https：{url}")
        return
    if url.startswith("/"):
        err(f"不能用以 / 开头的路径（Pages 部署在子路径下会 404）：{url}")
        return
    target, fragment = resolve_link(url, page, site)
    if site not in target.parents:
        err(f"链接指向站点目录之外：{url}")
        return
    if not target.exists():
        err(f"链接目标不存在：{url}")
        return
    if fragment and target in parsed and fragment not in parsed[target][0].ids:
        err(f"锚点不存在：{url}")


def check_site(site):
    pages = sorted(p.resolve() for p in site.rglob("*.html"))
    if not pages:
        return [f"{site} 下没有 HTML 页面"]
    parsed = {}
    for page in pages:
        text = page.read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(text)
        parsed[page] = (parser, text)

    errors = []
    expected_nav = [(site / t).resolve() for t in NAV_TARGETS]
    for page, (p, text) in parsed.items():
        rel = page.relative_to(site).as_posix()

        def err(msg, rel=rel):
            errors.append(f"{rel}: {msg}")

        if p.lang != "zh-CN":
            err('<html> 需要 lang="zh-CN"')
        if not p.has_viewport:
            err("缺少 viewport meta")
        if not p.title.strip():
            err("缺少 <title>")
        nav = [resolve_link(u, page, site)[0] for u in p.nav_links]
        if nav != expected_nav:
            err(f"导航链接应依次指向 {NAV_TARGETS}")
        for url in p.links:
            check_link(url, page, site, parsed, err)
        if page.parent != site:
            if META_VERSION not in p.meta_text or not META_DATE.search(p.meta_text):
                err(f'内容页的 <p class="page-meta"> 需包含「{META_VERSION}」和「YYYY-MM-DD 核对」')
            if not any(u.startswith("https://") for u in p.source_links):
                err('内容页缺少 <section class="sources"> 资料来源外链')
        plain = TAG.sub("", WRONG_TERM.sub("", text))
        for term, why in FORBIDDEN_TERMS.items():
            if term in plain:
                err(f"出现非官方译名「{term}」：{why}")
    return errors


def main():
    site = Path(sys.argv[1] if len(sys.argv) > 1 else "site")
    if not site.is_dir():
        print(f"找不到站点目录：{site}")
        return 1
    site = site.resolve()
    errors = check_site(site)
    for e in errors:
        print(e)
    if errors:
        print(f"共 {len(errors)} 个问题")
        return 1
    print(f"OK：{len(list(site.rglob('*.html')))} 个页面检查通过")
    return 0


if __name__ == "__main__":
    sys.exit(main())
```

- [ ] **Step 5: 运行测试，确认通过**

Run: `python3 -m unittest discover -s scripts -v`
Expected: `Ran 11 tests` … `OK`

- [ ] **Step 6: 确认在没有 site/ 时脚本会失败**

Run: `python3 scripts/check_site.py; echo "exit=$?"`
Expected: `找不到站点目录：site` 和 `exit=1`

- [ ] **Step 7: Commit**

```bash
git add scripts/check_site.py scripts/test_check_site.py
git commit -m "feat: 添加站点检查脚本"
```

---

### Task 2: 站点外壳（共用样式、首页、关于页）

**Files:**
- Create: `site/assets/css/site.css`
- Create: `site/index.html`
- Create: `site/about.html`
- Create: `site/builds/mr2.html`（占位，Task 3 写入正文；先建出来让导航链接能打开）

**Interfaces:**
- Consumes: Task 1 的 `python3 scripts/check_site.py`
- Produces: CSS 类名供 Task 3 使用：`.wrap`、`.site-header`、`.site-name`、`.site-nav`（当前页链接加 `aria-current="page"`）、`.site-footer`、`.lead`、`.page-meta`、`.summary`、`.note`、`.table-scroll`（包住每个表格）、`table.wide`（最小宽度 560px，窄屏时横向滚动）、`td.nowrap`、`.card`、`.sources`、`del.wrong-term`。页面骨架（header / main / footer）的写法见下面的 `index.html`。

- [ ] **Step 1: 运行检查，确认失败**

Run: `mkdir -p site && python3 scripts/check_site.py; echo "exit=$?"`
Expected: `… 下没有 HTML 页面` 和 `exit=1`

- [ ] **Step 2: 写共用样式**

创建 `site/assets/css/site.css`：

```css
:root {
  --bg: #f7f5f0;
  --surface: #ffffff;
  --text: #1f2328;
  --muted: #5d6570;
  --border: #e2ddd3;
  --accent: #b4531c;
  --accent-soft: #f8e9dd;
  --warn-bg: #fff5d6;
  --warn-border: #d9a520;
  --radius: 10px;
  color-scheme: light;
}

@media (prefers-color-scheme: dark) {
  :root {
    --bg: #15171b;
    --surface: #1d2026;
    --text: #e7e5e0;
    --muted: #9aa2ad;
    --border: #30343c;
    --accent: #f08c4f;
    --accent-soft: #3a2517;
    --warn-bg: #33290f;
    --warn-border: #a88226;
    color-scheme: dark;
  }
}

* { box-sizing: border-box; }

html { -webkit-text-size-adjust: 100%; }

body {
  margin: 0;
  background: var(--bg);
  color: var(--text);
  font: 16px/1.7 -apple-system, BlinkMacSystemFont, "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", "Noto Sans CJK SC", sans-serif;
}

a { color: var(--accent); }
a:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }

.wrap { max-width: 720px; margin: 0 auto; padding: 0 16px; }

.site-header { background: var(--surface); border-bottom: 1px solid var(--border); }
.site-header .wrap { display: flex; flex-wrap: wrap; align-items: baseline; gap: 4px 20px; padding-top: 12px; padding-bottom: 12px; }
.site-name { font-weight: 700; color: var(--text); text-decoration: none; }
.site-nav { display: flex; gap: 16px; }
.site-nav a { color: var(--muted); text-decoration: none; }
.site-nav a[aria-current="page"] { color: var(--accent); font-weight: 600; }

main.wrap { padding-top: 24px; padding-bottom: 48px; }
h1 { font-size: 1.6rem; line-height: 1.3; margin: 0 0 6px; }
h2 { font-size: 1.25rem; line-height: 1.4; margin: 36px 0 12px; padding-bottom: 6px; border-bottom: 1px solid var(--border); }
p, ul, ol { margin: 0 0 12px; }

.lead { color: var(--muted); }
.page-meta { color: var(--muted); font-size: 0.875rem; margin-bottom: 20px; }

.summary { background: var(--accent-soft); border-radius: var(--radius); padding: 14px 16px; margin: 16px 0; }
.summary p:last-child { margin-bottom: 0; }

.note { background: var(--warn-bg); border-left: 4px solid var(--warn-border); border-radius: 0 var(--radius) var(--radius) 0; padding: 10px 14px; margin: 16px 0; }
.note p:last-child { margin-bottom: 0; }

.table-scroll { overflow-x: auto; margin: 12px 0 16px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); }
table { border-collapse: collapse; width: 100%; font-size: 0.9375rem; }
table.wide { min-width: 560px; }
th, td { padding: 8px 10px; text-align: left; vertical-align: top; border-bottom: 1px solid var(--border); }
th { background: var(--accent-soft); font-weight: 600; white-space: nowrap; }
tbody tr:last-child td { border-bottom: 0; }
tfoot td { font-weight: 600; border-top: 2px solid var(--border); border-bottom: 0; }
td.nowrap { white-space: nowrap; }

.card { display: block; margin: 12px 0; padding: 14px 16px; background: var(--surface); border: 1px solid var(--border); border-radius: var(--radius); color: var(--text); text-decoration: none; }
.card strong { color: var(--accent); }

.sources { margin-top: 40px; color: var(--muted); font-size: 0.875rem; }
.sources h2 { font-size: 1rem; }
.sources a { overflow-wrap: anywhere; }

del.wrong-term { color: var(--muted); }

.site-footer { border-top: 1px solid var(--border); color: var(--muted); font-size: 0.8125rem; padding: 16px 0 32px; }
```

- [ ] **Step 3: 写首页**

创建 `site/index.html`：

```html
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>曙光长枪攻略</title>
<link rel="stylesheet" href="assets/css/site.css">
</head>
<body>
<header class="site-header">
  <div class="wrap">
    <a class="site-name" href="index.html">曙光长枪攻略</a>
    <nav class="site-nav" aria-label="主导航">
      <a href="index.html" aria-current="page">首页</a>
      <a href="builds/mr2.html">配装</a>
      <a href="about.html">关于</a>
    </nav>
  </div>
</header>
<main class="wrap">
  <h1>曙光长枪攻略</h1>
  <p class="lead">《怪物猎人 崛起：曙光》Switch 版的个人定制攻略，所有内容以最终版本 Ver.16.0.2 为准。</p>

  <h2 id="progress">当前进度</h2>
  <ul>
    <li>主武器：长枪</li>
    <li>进度：大师级 2★（2026-09-30）</li>
  </ul>

  <h2 id="current-build">当前配装</h2>
  <a class="card" href="builds/mr2.html">
    <strong>MR 2★ · 土砂龙X 全套</strong><br>
    防具自带防御性能 5、攻击守势 3；插满装饰品后攻击 7、弱点特效 3
  </a>

  <h2 id="pages">全部页面</h2>
  <ul>
    <li><a href="builds/mr2.html">长枪配装：MR 2★</a>：技能优先级、土砂龙X 全套、装饰品与武器</li>
    <li><a href="about.html">关于</a>：版本基准、资料来源、译名说明</li>
  </ul>
</main>
<footer class="site-footer">
  <div class="wrap">《怪物猎人 崛起：曙光》Switch 版个人攻略 · 数据基准 Ver.16.0.2</div>
</footer>
</body>
</html>
```

- [ ] **Step 4: 写关于页**

创建 `site/about.html`：

```html
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>关于 · 曙光长枪攻略</title>
<link rel="stylesheet" href="assets/css/site.css">
</head>
<body>
<header class="site-header">
  <div class="wrap">
    <a class="site-name" href="index.html">曙光长枪攻略</a>
    <nav class="site-nav" aria-label="主导航">
      <a href="index.html">首页</a>
      <a href="builds/mr2.html">配装</a>
      <a href="about.html" aria-current="page">关于</a>
    </nav>
  </div>
</header>
<main class="wrap">
  <h1>关于</h1>
  <p class="lead">给自己看的《怪物猎人 崛起：曙光》Switch 版攻略，主武器长枪。</p>

  <h2 id="version">版本基准</h2>
  <p>所有内容以 Switch 版最终版本 <strong>Ver.16.0.2</strong>（2024-01-22）为准。16.0.0 之后官方再没有做过平衡调整，所以数据库里标注 v16.0.0 的数值就是最终数值。</p>
  <div class="table-scroll">
    <table>
      <thead><tr><th>版本</th><th>日期</th><th>内容</th></tr></thead>
      <tbody>
        <tr><td>10.0.2</td><td class="nowrap">2022-06-30</td><td>曙光发售</td></tr>
        <tr><td>10.0.3</td><td class="nowrap">2022-07-08</td><td>平衡调整</td></tr>
        <tr><td>11.0.1</td><td class="nowrap">2022-08-10</td><td>第 1 次免费更新</td></tr>
        <tr><td>11.0.2</td><td class="nowrap">2022-08-26</td><td>平衡调整</td></tr>
        <tr><td>12.0.0</td><td class="nowrap">2022-09-29</td><td>第 2 次免费更新</td></tr>
        <tr><td>12.0.1</td><td class="nowrap">2022-10-14</td><td>平衡调整</td></tr>
        <tr><td>13.0.0</td><td class="nowrap">2022-11-24</td><td>第 3 次免费更新</td></tr>
        <tr><td>14.0.0</td><td class="nowrap">2023-02-07</td><td>第 4 次免费更新</td></tr>
        <tr><td>15.0.0</td><td class="nowrap">2023-04-20</td><td>第 5 次免费更新</td></tr>
        <tr><td>16.0.0</td><td class="nowrap">2023-06-08</td><td>追加更新，最后一次内容与平衡调整</td></tr>
        <tr><td>16.0.1</td><td class="nowrap">2023-07-07</td><td>问题修正</td></tr>
        <tr><td>16.0.2</td><td class="nowrap">2024-01-22</td><td>停止发布部分联动内容</td></tr>
      </tbody>
    </table>
  </div>
  <p>Ver.16.0.2 停止发布了 4 个联动活动任务和 2 个联动随从艾露猫，没下载过的现在拿不到了。</p>

  <h2 id="sources">资料来源</h2>
  <p>按可信度从高到低：</p>
  <ol>
    <li><a href="https://www.monsterhunter.com/rise-sunbreak/update/zh-cn/">Capcom 官方更新资料</a>：版本改动以这里为准。</li>
    <li><a href="https://mhrise.kiranico.com/zh">Kiranico</a>、<a href="https://mhrice.info/">MHRice</a>：从游戏数据中提取的数值和简中译名。</li>
    <li><a href="https://gamecat.fun/rise/zh/">游猫网</a>：中文 wiki 和配装器。</li>
    <li>GameWith、Game8 等攻略站：配装和打法思路。要看文章日期，数值回到 Kiranico 核对。</li>
  </ol>

  <h2 id="terms">译名说明</h2>
  <p>名称一律采用游戏内的简体中文官方译名。常见的非官方写法：</p>
  <div class="table-scroll">
    <table>
      <thead><tr><th>官方简中</th><th>不用</th></tr></thead>
      <tbody>
        <tr><td>怪异炼化</td><td><del class="wrong-term">傀异炼成</del></td></tr>
        <tr><td>怪异探究任务</td><td><del class="wrong-term">怪异调查</del></td></tr>
        <tr><td>原初形态爵银龙</td><td><del class="wrong-term">原初爵银龙</del>、<del class="wrong-term">原初爵銀龍</del>（繁中）</td></tr>
        <tr><td>加工店</td><td><del class="wrong-term">加工屋</del></td></tr>
      </tbody>
    </table>
  </div>
</main>
<footer class="site-footer">
  <div class="wrap">《怪物猎人 崛起：曙光》Switch 版个人攻略 · 数据基准 Ver.16.0.2</div>
</footer>
</body>
</html>
```

- [ ] **Step 5: 写配装页占位**

创建 `site/builds/mr2.html`（Task 3 会整页替换）：

```html
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>长枪配装：MR 2★ · 曙光长枪攻略</title>
<link rel="stylesheet" href="../assets/css/site.css">
</head>
<body>
<header class="site-header">
  <div class="wrap">
    <a class="site-name" href="../index.html">曙光长枪攻略</a>
    <nav class="site-nav" aria-label="主导航">
      <a href="../index.html">首页</a>
      <a href="mr2.html" aria-current="page">配装</a>
      <a href="../about.html">关于</a>
    </nav>
  </div>
</header>
<main class="wrap">
  <h1>长枪配装：MR 2★</h1>
  <p class="page-meta">MR 2★ · Ver.16.0.2（Kiranico v16.0.0）· 2026-09-30 核对</p>
  <section class="sources">
    <h2 id="sources">资料来源</h2>
    <ul><li><a href="https://mhrise.kiranico.com/zh">Kiranico</a></li></ul>
  </section>
</main>
<footer class="site-footer">
  <div class="wrap">《怪物猎人 崛起：曙光》Switch 版个人攻略 · 数据基准 Ver.16.0.2</div>
</footer>
</body>
</html>
```

- [ ] **Step 6: 运行检查，确认通过**

Run: `python3 scripts/check_site.py`
Expected: `OK：3 个页面检查通过`

- [ ] **Step 7: 在浏览器里检查手机宽度、深色模式和子路径**

在仓库根目录后台启动服务（从根目录起服务，站点处在 `/site/` 子路径下，模拟 Pages 的 `/<仓库名>/`）：

Run（后台）: `python3 -m http.server 8765 --bind 127.0.0.1`

用 Chrome DevTools MCP：
1. `new_page` 打开 `http://127.0.0.1:8765/site/index.html`，再用 `emulate` 把视口设为 375×812。
2. 对 `index.html` 和 `about.html` 分别用 `evaluate_script` 执行下面的函数，期望 `overflow` 为 `false`，`broken` 为空数组：

```js
async () => {
  const links = [...document.querySelectorAll('a[href], link[href]')]
    .map(el => el.href)
    .filter(href => href.startsWith(location.origin));
  const results = await Promise.all(links.map(href => fetch(href).then(r => [href, r.status])));
  return {
    overflow: document.documentElement.scrollWidth > window.innerWidth,
    broken: results.filter(([, status]) => status !== 200),
  };
}
```

3. 用 `emulate` 切换到深色配色（`prefers-color-scheme: dark`），对两页分别 `take_screenshot`。确认背景是深色、文字和表格清晰、导航当前项是橙色。
4. 检查完停掉服务。

- [ ] **Step 8: Commit**

```bash
git add site/
git commit -m "feat: 添加站点外壳（共用样式、首页、关于页）"
```

---

### Task 3: 第一页「长枪配装：MR 2★」

**Files:**
- Modify: `site/builds/mr2.html`（整页替换）

**Interfaces:**
- Consumes: Task 2 的 CSS 类名和页面骨架；Task 1 的检查脚本
- Produces: 页面锚点 `#skills`、`#armor`、`#decorations`、`#weapons`、`#sources`

- [ ] **Step 1: 写整页内容**

用下面的内容替换 `site/builds/mr2.html`：

```html
<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>长枪配装：MR 2★ · 曙光长枪攻略</title>
<link rel="stylesheet" href="../assets/css/site.css">
</head>
<body>
<header class="site-header">
  <div class="wrap">
    <a class="site-name" href="../index.html">曙光长枪攻略</a>
    <nav class="site-nav" aria-label="主导航">
      <a href="../index.html">首页</a>
      <a href="mr2.html" aria-current="page">配装</a>
      <a href="../about.html">关于</a>
    </nav>
  </div>
</header>
<main class="wrap">
  <h1>长枪配装：MR 2★</h1>
  <p class="page-meta">MR 2★ · Ver.16.0.2（Kiranico v16.0.0）· 2026-09-30 核对</p>

  <div class="summary">
    <p><strong>结论：穿土砂龙X 全套。</strong>防具自带防御性能 5、攻击守势 3，两个长枪核心技能直接满级；插满装饰品后，攻击 7、弱点特效 3。</p>
  </div>

  <h2 id="skills">技能优先级</h2>
  <p>长枪通用，不限于这个进度。效果数值来自 Kiranico 的技能说明。</p>
  <div class="table-scroll">
    <table class="wide">
      <thead><tr><th>技能</th><th>目标</th><th>效果</th><th>理由</th></tr></thead>
      <tbody>
        <tr><td class="nowrap"><strong>防御性能</strong></td><td class="nowrap">Lv5</td><td>Lv5：大幅减少攻击威力，减少耐力消耗量 30%</td><td>长枪大部分时间都在举盾，满级最稳</td></tr>
        <tr><td class="nowrap"><strong>攻击守势</strong></td><td class="nowrap">Lv3</td><td>Lv3：抓准时机防御成功后，一定时间内攻击力 1.15 倍</td><td>长枪最主要的增伤手段</td></tr>
        <tr><td class="nowrap"><strong>攻击</strong></td><td class="nowrap">Lv4 以上</td><td>Lv4：攻击力 1.05 倍 +7；Lv7：攻击力 1.1 倍 +10</td><td>Lv4 开始才有倍率加成</td></tr>
        <tr><td class="nowrap"><strong>弱点特效</strong></td><td class="nowrap">Lv3</td><td>Lv3：攻击有效部位时会心率 +50%</td><td>长枪擅长持续攻击同一个部位</td></tr>
        <tr><td class="nowrap">超会心</td><td class="nowrap">有孔就加</td><td>Lv1：会心攻击的伤害倍率 1.3 倍</td><td>有了会心率之后才有价值</td></tr>
        <tr><td class="nowrap">看破</td><td class="nowrap">有孔就加</td><td>Lv1：会心率 +5%</td><td>补会心率</td></tr>
        <tr><td class="nowrap">翔虫使</td><td class="nowrap">可选</td><td>Lv1：能使用野生翔虫的时间 1.3 倍；Lv3：追加在地上时回复速度上升</td><td>GameWith 推荐给长枪，能更频繁地使用消耗翔虫的招式</td></tr>
        <tr><td class="nowrap">防御强化</td><td class="nowrap">暂缓</td><td>可以防御一般无法防御的攻击；Lv1 减少伤害 30%</td><td>遇到挡不住的招式再补</td></tr>
      </tbody>
    </table>
  </div>

  <h2 id="armor">防具：土砂龙X 全套</h2>
  <p>土砂龙在 MR 1★ 任务「满身的泥泞就是王牌」（沙原）中登场。</p>
  <div class="table-scroll">
    <table class="wide">
      <thead><tr><th>防具</th><th>技能</th><th>孔位</th></tr></thead>
      <tbody>
        <tr><td class="nowrap">土砂龙X头盔</td><td>攻击 1、防御 1、攻击守势 1、散弹・扩散箭强化 1</td><td class="nowrap">④①</td></tr>
        <tr><td class="nowrap">土砂龙X铠甲</td><td>攻击 2、防御 2、泥雪耐性 2</td><td class="nowrap">④</td></tr>
        <tr><td class="nowrap">土砂龙X腕甲</td><td>攻击 2、攻击守势 1、滑走强化 1、散弹・扩散箭强化 1</td><td class="nowrap">②①</td></tr>
        <tr><td class="nowrap">土砂龙X腰甲</td><td>防御性能 3、防御 1</td><td class="nowrap">③</td></tr>
        <tr><td class="nowrap">土砂龙X护腿</td><td>防御性能 2、防御 1、攻击守势 1</td><td class="nowrap">②①</td></tr>
      </tbody>
      <tfoot>
        <tr><td>合计</td><td>防御性能 5、攻击守势 3、攻击 5、防御 5（另有泥雪耐性 2、滑走强化 1、散弹・扩散箭强化 2，对长枪没用）</td><td class="nowrap">④④③②②①①①</td></tr>
      </tfoot>
    </table>
  </div>

  <h2 id="decorations">装饰品</h2>
  <div class="table-scroll">
    <table class="wide">
      <thead><tr><th>插在</th><th>装饰品</th><th>加成</th></tr></thead>
      <tbody>
        <tr><td>头盔④、铠甲④、腰甲③</td><td class="nowrap">痛击珠【2】×3</td><td>弱点特效 +3</td></tr>
        <tr><td>腕甲②、护腿②</td><td class="nowrap">攻击珠【2】×2</td><td>攻击 +2</td></tr>
        <tr><td>头盔①、腕甲①、护腿①</td><td class="nowrap">耐绝珠【1】×3</td><td>昏厥耐性 +3（Lv3：不会变为昏厥状态）</td></tr>
        <tr><td>武器孔</td><td class="nowrap">超心珠【2】、达人珠【2】</td><td>超会心 +1、看破 +1（远古巴别塔・改的 ③② 孔）；也可以换一个成翔虫珠【2】</td></tr>
      </tbody>
    </table>
  </div>
  <p><strong>插满后：</strong>攻击 7、弱点特效 3、防御性能 5、攻击守势 3、防御 5、昏厥耐性 3、超会心 1、看破 1。</p>
  <div class="note">
    <p>Lv4 的珠子要用怪异原珠或明王原珠制作，MR 2★ 还做不了，所以 ④ 孔先插 2～3 级的珠子。</p>
    <p>上面这些 1～2 级珠子能不能做，以游戏里加工店的显示为准。缺痛击珠时，用挑战珠【2】（挑战者）或达人珠【2】（看破）代替。</p>
  </div>

  <h2 id="weapons">武器参考</h2>
  <div class="table-scroll">
    <table class="wide">
      <thead><tr><th>武器</th><th>攻击</th><th>属性 / 会心</th><th>孔位</th><th>说明</th></tr></thead>
      <tbody>
        <tr><td class="nowrap">远古巴别塔・改</td><td>240</td><td>无属性</td><td class="nowrap">③②</td><td>防御力加成 +30；Game8、GameWith 都推荐</td></tr>
        <tr><td class="nowrap">飞雷枪【御手杵】改</td><td>240</td><td>雷 27，会心率 +15%</td><td class="nowrap">②①</td><td>GameWith 推荐进入 MR 2★ 后换用</td></tr>
        <tr><td class="nowrap">骨爪长枪</td><td>240</td><td>水 32</td><td class="nowrap">④③</td><td>防御力加成 +30；三把里孔位最多</td></tr>
      </tbody>
    </table>
  </div>

  <section class="sources">
    <h2 id="sources">资料来源</h2>
    <ul>
      <li><a href="https://gamewith.jp/mhrize/article/show/348824">GameWith：长枪序盘推荐装备（2025-07-10 更新）</a></li>
      <li><a href="https://game8.co/games/Monster-Hunter-Rise/archives/380801">Game8：Master Rank Lance Builds</a></li>
      <li><a href="https://mhrise.kiranico.com/zh/data/armors?view=7">Kiranico：RARE 8 防具</a></li>
      <li><a href="https://mhrise.kiranico.com/zh/data/skills">Kiranico：装备技能</a></li>
      <li><a href="https://mhrise.kiranico.com/zh/data/decorations">Kiranico：装饰品</a></li>
      <li><a href="https://mhrise.kiranico.com/zh/data/weapons?view=6">Kiranico：长枪</a></li>
      <li><a href="https://mhrise.kiranico.com/zh/data/quests?view=hub_master">Kiranico：大师级集会所任务</a></li>
    </ul>
  </section>
</main>
<footer class="site-footer">
  <div class="wrap">《怪物猎人 崛起：曙光》Switch 版个人攻略 · 数据基准 Ver.16.0.2</div>
</footer>
</body>
</html>
```

- [ ] **Step 2: 运行检查，确认通过**

Run: `python3 scripts/check_site.py`
Expected: `OK：3 个页面检查通过`

- [ ] **Step 3: 和 Kiranico 核对数据**

Run:

```bash
python3 - <<'EOF'
import html, re, urllib.request
UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126 Safari/537.36"}
def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8")
def rows(url, kind):
    for r in re.findall(r"<tr[^>]*>(.*?)</tr>", get(url), re.S):
        m = re.search(r"data/%s/\d+\"[^>]*>(.*?)</a>" % kind, r, re.S)
        if m:
            cells = [c.strip() for c in html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " | ", r))).split("|") if c.strip()]
            yield html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip(), cells, re.findall(r"deco(\d)\.png", r)
base = "https://mhrise.kiranico.com/zh/data/"
for name, cells, slots in rows(base + "armors?view=7", "armors"):
    if name.startswith("土砂龙X"):
        print(name, "slots", slots, "|", " ".join(c for c in cells if not re.fullmatch(r"-?\d+", c)))
for name, cells, slots in rows(base + "decorations", "decorations"):
    if name in ("痛击珠【2】", "攻击珠【2】", "耐绝珠【1】", "超心珠【2】", "达人珠【2】", "翔虫珠【2】", "挑战珠【2】"):
        print(name, cells[1:3])
for name, cells, slots in rows(base + "weapons?view=6", "weapons"):
    if name in ("远古巴别塔・改", "飞雷枪【御手杵】改", "骨爪长枪"):
        print(name, cells[3:8], "slots", slots)
EOF
```

Expected（和页面逐项对照）：
- 土砂龙X头盔 孔 1、4，技能 攻击1 防御1 攻击守势1 散弹・扩散箭强化1
- 土砂龙X铠甲 孔 4，攻击2 防御2 泥雪耐性2
- 土砂龙X腕甲 孔 1、2，攻击2 滑走强化1 攻击守势1 散弹・扩散箭强化1
- 土砂龙X腰甲 孔 3，防御性能3 防御1
- 土砂龙X护腿 孔 1、2，防御性能2 防御1 攻击守势1
- 痛击珠【2】弱点特效 Lv1、攻击珠【2】攻击 Lv1、耐绝珠【1】昏厥耐性 Lv1、超心珠【2】超会心 Lv1、达人珠【2】看破 Lv1、翔虫珠【2】翔虫使 Lv1、挑战珠【2】挑战者 Lv1
- 远古巴别塔・改 240，防御力加成 +30，孔 3、2；飞雷枪【御手杵】改 240、27、会心率 +15%，孔 1、2；骨爪长枪 240、32、防御力加成 +30，孔 4、3

有任何一项对不上，以 Kiranico 为准修改页面，再重新运行 Step 2。

- [ ] **Step 4: 在浏览器里检查手机宽度、深色模式和子路径**

同 Task 2 Step 7 的做法：从仓库根目录后台启动 `python3 -m http.server 8765 --bind 127.0.0.1`，用 Chrome DevTools MCP 打开 `http://127.0.0.1:8765/site/builds/mr2.html`，视口 375×812，执行下面的函数，期望 `overflow` 为 `false`、`broken` 为空数组、`tablesScroll` 全部为 `true`（宽表格在自己的容器里滚动）：

```js
async () => {
  const links = [...document.querySelectorAll('a[href], link[href]')]
    .map(el => el.href)
    .filter(href => href.startsWith(location.origin));
  const results = await Promise.all(links.map(href => fetch(href).then(r => [href, r.status])));
  return {
    overflow: document.documentElement.scrollWidth > window.innerWidth,
    broken: results.filter(([, status]) => status !== 200),
    tablesScroll: [...document.querySelectorAll('table.wide')].map(t => t.parentElement.scrollWidth > t.parentElement.clientWidth),
  };
}
```

再切换到深色配色 `take_screenshot`，确认提示框、表格表头、合计行都清晰可读。检查完停掉服务。

- [ ] **Step 5: Commit**

```bash
git add site/builds/mr2.html
git commit -m "feat: 添加长枪配装 MR 2★ 页面"
```

---

### Task 4: 部署工作流与 CLAUDE.md

**Files:**
- Create: `.github/workflows/pages.yml`
- Modify: `CLAUDE.md`（「项目概述」「语言与译名」「发布（GitHub Pages）」三节）

**Interfaces:**
- Consumes: Task 1 的 `scripts/check_site.py` 和 `scripts/test_check_site.py`；`site/` 目录
- Produces: 推送到 `main` 时自动检查并部署 `site/`

- [ ] **Step 1: 写部署工作流**

创建 `.github/workflows/pages.yml`：

```yaml
name: Deploy site to GitHub Pages

on:
  push:
    branches: [main]
  workflow_dispatch:

permissions:
  contents: read
  pages: write
  id-token: write

concurrency:
  group: pages
  cancel-in-progress: false

jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: github-pages
      url: ${{ steps.deployment.outputs.page_url }}
    steps:
      - uses: actions/checkout@v7
      - name: Test check script
        run: python3 -m unittest discover -s scripts
      - name: Check site
        run: python3 scripts/check_site.py site
      - uses: actions/configure-pages@v6
      - uses: actions/upload-pages-artifact@v5
        with:
          path: site
      - id: deployment
        uses: actions/deploy-pages@v5
```

- [ ] **Step 2: 校验 YAML 语法**

Run: `ruby -ryaml -e 'y = YAML.load_file(".github/workflows/pages.yml"); puts y["jobs"]["deploy"]["steps"].map { |s| s["uses"] || s["name"] }'`
Expected:

```
actions/checkout@v7
Test check script
Check site
actions/configure-pages@v6
actions/upload-pages-artifact@v5
actions/deploy-pages@v5
```

- [ ] **Step 3: 更新 CLAUDE.md「项目概述」**

把「项目概述」一节中这一段：

```markdown
当前仓库只有初始提交，还没有目录结构、构建工具或 Pages 部署配置。确定这些之后回来更新本文件（目录约定、预览/部署命令）。
```

替换为：

```markdown
这是给用户本人看的**定制攻略**：主武器长枪，内容打到哪写到哪。当前进度写在 `site/index.html` 的「当前进度」里，推荐装备前先确认进度，只用当前进度能拿到的素材。

### 目录与约定

- `site/` 是发布到 Pages 的全部内容；`docs/specs/`、`docs/plans/` 放设计和计划；`scripts/` 放检查脚本。
- 配装页是 `site/builds/mr<N>.html`，每个进度一页。以后需要时再加 `site/lance/`（长枪操作、招式）和 `site/monsters/<英文 slug>.html`（长枪视角的怪物笔记）。
- 文件名用英文小写 kebab-case；页面内容用简中官方译名。
- 每页顶部都有相同的手写导航（首页 / 配装 / 关于）。导航改动时，所有页面和 `scripts/check_site.py` 的 `NAV_TARGETS` 要一起改。
- 内容页（`site/` 子目录下的页面）标题下必须有 `<p class="page-meta">`（进度 · Ver.16.0.2 · YYYY-MM-DD 核对），底部必须有 `<section class="sources">` 资料来源。
- 新增或更新内容页后，同步更新首页的「当前配装」和「全部页面」。
- 样式都在 `site/assets/css/site.css`，颜色用 `:root` 变量并带深色模式；宽表格用 `<div class="table-scroll"><table class="wide">` 包住。

### 命令

- 检查站点：`python3 scripts/check_site.py`
- 检查脚本的测试：`python3 -m unittest discover -s scripts`；只跑一个：`python3 -m unittest discover -s scripts -k test_forbidden_term_rejected`
- 本地预览：在仓库根目录运行 `python3 -m http.server 8000`，打开 `http://localhost:8000/site/`（站点处在子路径下，和 Pages 的部署方式一致）
```

- [ ] **Step 4: 更新 CLAUDE.md「语言与译名」的示例**

在「语言与译名」一节，把这一行：

```markdown
  - 应写「原初形态爵银龙」，不写繁中的「原初爵銀龍」，也不写资讯站标题里的「原初爵银龙」。
```

替换为：

```markdown
  - 应写「原初形态爵银龙」，不写繁中的「原初爵銀龍」，也不写资讯站标题里的「原初爵银龙」。
  - 应写「怪异探究任务」（Anomaly Investigations），不写「怪异调查」；应写「加工店」，不写「加工屋」。
  - 这些写法已加进 `scripts/check_site.py` 的 `FORBIDDEN_TERMS`，新发现的误用也加进去；页面里需要作为反例展示时，用 `<del class="wrong-term">` 包起来。
```

- [ ] **Step 5: 更新 CLAUDE.md「发布（GitHub Pages）」**

把整个「发布（GitHub Pages）」一节替换为：

```markdown
## 发布（GitHub Pages）

- 推送到 `main` 后，`.github/workflows/pages.yml` 会先跑检查脚本的测试和 `check_site.py`，然后只把 `site/` 目录部署到 Pages。需要在 GitHub 仓库的 Pages 设置里把来源设为「GitHub Actions」。用 Actions 部署不会经过 Jekyll，不需要 `.nojekyll`。
- 站内链接和资源一律用**相对路径**：项目型 Pages 部署在 `/<仓库名>/` 子路径下，以 `/` 开头的绝对路径上线后会 404（检查脚本会拦下来）。
```

- [ ] **Step 6: 全量检查**

Run: `python3 -m unittest discover -s scripts && python3 scripts/check_site.py`
Expected: 测试 `OK`，然后 `OK：3 个页面检查通过`

- [ ] **Step 7: Commit**

```bash
git add .github/workflows/pages.yml CLAUDE.md docs/specs/2026-09-30-site-structure-design.md docs/plans/2026-09-30-site-skeleton.md
git commit -m "feat: 添加 Pages 部署工作流，更新 CLAUDE.md"
```
