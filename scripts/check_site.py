#!/usr/bin/env python3
"""检查 site/ 下的静态页面。

用法：python3 scripts/check_site.py [站点目录，默认 site]

检查项：站内链接和锚点能打开、不用以 / 开头的路径、外链用 https、
页面基本结构（lang、viewport、title、导航）、内容页的元信息、本页目录和资料来源、
非官方译名、离线缓存（每页的 head 标签、sw.js 预缓存列表、manifest）、
_redirects 跳转规则。有问题时逐条列出，并以状态码 1 退出。
"""
import json
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
PRECACHE = re.compile(r"const PRECACHE = \[(.*?)\];", re.S)
# 不进离线缓存的文件：service worker 自己，以及只给 Cloudflare 读的跳转规则
NOT_PRECACHED = {"sw.js", "_redirects"}
PWA_HEAD = ["manifest.webmanifest", "assets/js/sw-register.js"]
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
        self.head_assets = []  # <link rel="manifest"> 和 <script src> 的地址
        self.h2_ids = []  # 每个 h2 的 id，没有 id 记 None
        self.has_toc = False
        self.toc_links = []
        self._stack = []  # (标签名, 标记)，标记是 nav / sources / meta / title / toc 或 None

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
        if tag == "h2":
            self.h2_ids.append(a.get("id"))
        if (tag == "link" and a.get("rel") == "manifest") or (tag == "script" and a.get("src")):
            self.head_assets.append(a.get("href") or a.get("src"))
        url = a.get("href") if tag in ("a", "link") else a.get("src") if tag in ("img", "script") else None
        if url is not None:
            context = self._context()
            self.links.append(url)
            if "nav" in context:
                self.nav_links.append(url)
            if "sources" in context and tag == "a":
                self.source_links.append(url)
            if "toc" in context and tag == "a":
                self.toc_links.append(url)
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
        elif tag == "details" and "toc" in classes:
            marker = "toc"
            self.has_toc = True
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
    # 按 HTML 规范，#top 在页面里没有对应 id 时也会回到页面顶部
    if fragment and fragment != "top" and target in parsed and fragment not in parsed[target][0].ids:
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
    pwa = (site / "sw.js").exists()
    pwa_head = {(site / t).resolve() for t in PWA_HEAD}
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
        if pwa and not pwa_head <= {resolve_link(u, page, site)[0] for u in p.head_assets}:
            err(f"<head> 缺少离线缓存用的 {PWA_HEAD}，照抄其他页面 <head> 里的 manifest 到 sw-register.js 那几行")
        # 子目录里的页面是内容页；子目录的 index.html 是列表页，不受内容页规则约束
        if page.parent != site and page.name != "index.html":
            if META_VERSION not in p.meta_text or not META_DATE.search(p.meta_text):
                err(f'内容页的 <p class="page-meta"> 需包含「{META_VERSION}」和「YYYY-MM-DD 核对」')
            if not any(u.startswith("https://") for u in p.source_links):
                err('内容页缺少 <section class="sources"> 资料来源外链')
            if None in p.h2_ids:
                err("内容页的 <h2> 都要有 id")
            elif not p.has_toc:
                err('内容页缺少 <details class="toc"> 本页目录')
            elif [urlsplit(u).fragment for u in p.toc_links] != p.h2_ids:
                err(f"本页目录应依次链接到全部 h2：{['#' + i for i in p.h2_ids]}")
        plain = TAG.sub("", WRONG_TERM.sub("", text))
        for term, why in FORBIDDEN_TERMS.items():
            if term in plain:
                err(f"出现非官方译名「{term}」：{why}")
    if pwa:
        errors += check_precache(site) + check_manifest(site)
    if (site / "_redirects").exists():
        errors += check_redirects(site)
    return errors


def check_precache(site):
    """sw.js 的 PRECACHE 要和 site/ 下的文件一一对应，否则新页面离线时打不开。"""
    m = PRECACHE.search((site / "sw.js").read_text(encoding="utf-8"))
    if not m:
        return ["sw.js: 找不到 const PRECACHE = [...]"]
    listed = set(re.findall(r'"([^"]+)"', m.group(1)))
    files = set()
    for p in site.rglob("*"):
        rel = p.relative_to(site)
        if p.is_file() and not any(part.startswith(".") for part in rel.parts):  # 跳过 .DS_Store 之类
            files.add(rel.as_posix())
    files -= NOT_PRECACHED
    return [f"sw.js: PRECACHE 缺少 {f}" for f in sorted(files - listed)] + \
        [f"sw.js: PRECACHE 里的 {f} 不存在" for f in sorted(listed - files)]


def check_manifest(site):
    path = site / "manifest.webmanifest"
    if not path.exists():
        return ["manifest.webmanifest 不存在"]
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except ValueError as e:
        return [f"manifest.webmanifest: JSON 格式错误：{e}"]
    refs = [data.get("start_url", "")] + [icon.get("src", "") for icon in data.get("icons", [])]
    return [f"manifest.webmanifest: 文件不存在：{r}" for r in refs if not r or not (site / r).is_file()]


def check_redirects(site):
    """_redirects 每行是「/来源 目标 [状态码]」，路径相对 Cloudflare 上的站点根目录。"""
    errors = []
    lines = (site / "_redirects").read_text(encoding="utf-8").splitlines()
    for n, line in enumerate(lines, 1):
        parts = line.split()
        if not parts or parts[0].startswith("#"):
            continue
        where = f"_redirects: 第 {n} 行"
        if len(parts) not in (2, 3) or not parts[0].startswith("/"):
            errors.append(f"{where}格式应为「/来源 目标 [状态码]」")
            continue
        source, dest = parts[0], parts[1]
        code = parts[2] if len(parts) == 3 else "302"
        if dest.startswith("/"):
            dynamic = ":" in dest or "*" in dest  # 占位符、通配符的目标没法逐个核对
            if not dynamic and not (site / urlsplit(dest).path.lstrip("/")).is_file():
                errors.append(f"{where}的目标不存在：{dest}")
        elif not dest.startswith("https://"):
            errors.append(f"{where}的目标要以 / 或 https:// 开头：{dest}")
        # Cloudflare 不管来源文件在不在都会跳转，现有页面写成来源就再也打不开了
        if code != "200" and (site / source.lstrip("/")).is_file():
            errors.append(f"{where}的来源 {source} 是现有文件，跳转后这个页面就打不开了")
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
