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
    "傀異": "这是日文/繁中字形，简中官方译名是「怪异」（怪异炼化、怪异克服）",
    "原初爵银龙": "简中官方译名是「原初形态爵银龙」",
    "原初爵銀龍": "这是繁中译名，简中官方译名是「原初形态爵银龙」",
    "怪异调查": "简中官方译名是「怪异探究任务」",
    "怪異調查": "这是繁中字形，简中官方译名是「怪异探究任务」",
    "加工屋": "简中官方译名是「加工店」",
}
NAV_TARGETS = ["index.html", "builds/index.html", "monsters/index.html", "about.html"]
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
        # 子目录里的页面是内容页；子目录的 index.html 是列表页，不受内容页规则约束
        if page.parent != site and page.name != "index.html":
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
