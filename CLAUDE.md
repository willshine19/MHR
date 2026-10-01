# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

《怪物猎人 崛起》（Monster Hunter Rise）+ 大型 DLC《曙光》（Sunbreak）的游戏攻略站，平台为 **Nintendo Switch 版**。内容以静态 HTML 呈现，发布到 GitHub Pages。

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

## 语言与译名

- 全站使用**简体中文**。
- 怪物、武器、防具、技能、道具、任务、系统等名称，一律采用**游戏内简体中文官方译名**。简中官方译名和繁中、日文汉字、社区叫法经常不一样，例如：
  - 应写「怪异炼化」「怪异克服」「怪异任务」，不写繁中/日文系的「傀异炼成」「傀异克服」。
  - 应写「原初形态爵银龙」，不写繁中的「原初爵銀龍」，也不写资讯站标题里的「原初爵银龙」。
  - 应写「怪异探究任务」（Anomaly Investigations），不写「怪异调查」；应写「加工店」，不写「加工屋」。
  - 这些写法已加进 `scripts/check_site.py` 的 `FORBIDDEN_TERMS`，新发现的误用也加进去；页面里需要作为反例展示时，用 `<del class="wrong-term">` 包起来。
- 查译名的方法：先在英文或日文资料里定位到条目，再到 Kiranico 找同一个条目，把 URL 的语言前缀换成 `/zh`（条目 ID 在各语言间相同），显示的就是游戏内简中文本。

## 内容准确性

目标版本：**Switch 版 Ver.16.0.2**（2024-01-22，最后一次更新）。选资料时按以下顺序取舍：

1. 能确定版本的资料，以最新版为准。多个来源说法冲突时，采用版本更新的那个。
2. 确定不了版本的资料，越新越好。可以用资料的发布或更新日期，对照下表推断它对应哪个版本。
3. 底线：资料必须写于 Sunbreak 发售之后（2022-06-30，Ver.10.0.2），并且包含 DLC 内容。本体时期（Ver.3.x 及更早）的资料不能采用。

| 版本 | 日期 | 性质 |
|---|---|---|
| 10.0.2 | 2022-06-30 | Sunbreak 发售 |
| 10.0.3 / 11.0.2 / 12.0.1 | 2022-07-08 / 08-26 / 10-14 | 平衡调整 |
| 11.0.1 · 12.0.0 · 13.0.0 | 2022-08-10 · 09-29 · 11-24 | 免费更新 TU1 · TU2 · TU3 |
| 14.0.0 · 15.0.0 | 2023-02-07 · 04-20 | TU4 · TU5 |
| 16.0.0 | 2023-06-08 | 最后一次内容与平衡更新（追加更新） |
| 16.0.1 | 2023-07-07 | 问题修正 |
| 16.0.2 | 2024-01-22 | 规格更改（下架联动内容） |

- 16.0.0 之后官方再没做过平衡调整，所以标注「v16.0.0」的数据库，数值就等于最终版。
- Ver.13.0.0.1 和 16.0.1.1 只在 Steam 上发布，Switch 没有，不要引用这两个版本的改动。
- 16.0.2 停止发布了 4 个联动活动任务（「金环尽在我手！」「别无二致的音速之影」「USJ・废神社的激斗！」「USJ・青熊们的猛烈进军！」）和 2 个联动随从艾露猫（「MEOW LIMIT!」「Yasu」）。已经下载过的可以继续玩，但无法再下载。攻略里不要把它们写成还能获取。
- 只写 Switch 版能做到的内容，不写 PC 版 Mod 和其他平台独有的差异。

## 信息来源评估（2026-09 实测）

「最终版覆盖」一列：用 Ver.16 新增的原初形态爵银龙做探针，看站点有没有收录相关内容。「curl」一列：用 `curl -A '<浏览器 UA>' -L` 能否拿到正文。

| 来源 | 数据版本 / 最终版覆盖 | 简中官方译名 | curl | 定位 |
|---|---|---|---|---|
| Capcom 官方更新页 [zh-cn](https://www.monsterhunter.com/rise-sunbreak/update/zh-cn/) | 全部版本（到 16.0.2），标注平台 | ✅ 官方 | ✅（WebFetch 会 403） | 版本改动的唯一权威；没有数值表 |
| Capcom [活动任务页](https://www.monsterhunter.com/rise-sunbreak/zh-cn/topics/event-quest/) | 官方 | ✅ | ✅ | 活动任务清单 |
| [Kiranico](https://mhrise.kiranico.com/zh) | v16.0.0 = 最终数值 ✅ | ✅ 游戏内文本 | ✅（WebFetch 也可用） | 拆包数据：怪物、武器、防具、技能、任务、道具 |
| [MHRice](https://mhrice.info/) | 可在 10.0.2 到 16.0.1 之间切换版本 ✅ | ✅ 游戏内文本（多语言） | ✅（会重定向到 mhrise.mhrice.info） | 拆包数据，用来比对某个数值在各版本间的变化 |
| [游猫网](https://gamecat.fun/rise/zh/) | 声明 v16.0.0（更新到 2023-06-08）✅ | ✅（用「怪异」系译名） | ✅（MediaWiki，支持 `index.php?search=`） | 中文 wiki + 配装器；社区维护，页面划分和游戏里不完全一致 |
| [wiki-db 配装模拟器](https://mhrise.wiki-db.com/sim/) | JS 应用，工具无法核实版本 | ❌ 日文 | ❌ 读不到数据 | 仅供人工配装 |
| [Game8](https://game8.co/games/Monster-Hunter-Rise) | 有 Ver.16 更新说明和原初形态爵银龙 ✅ | ❌ 英文 | ✅ | 英文攻略、流程、配装 |
| [Fextralife](https://monsterhunterrise.wiki.fextralife.com/Monster_Hunter_Rise_Wiki) | 有原初形态爵银龙页 ✅ | ❌ 英文 | ✅ | 英文 wiki，社区编辑 |
| [GameWith](https://gamewith.jp/mhrize/) | 首页有原初形态爵银龙 ✅ | ❌ 日文 | ✅ | 日文攻略、配装 |
| [AppMedia](https://appmedia.jp/mhrise) | 首页能看到 TU5，没看到 Ver.16 | ❌ 日文 | ✅ | 日文攻略（次选） |
| [游民星空](https://www.gamersky.com/z/mhrise/) | 有 Ver.16 文章，但大量文章写于 2022-07 | ⚠️ 标题常用非官方叫法 | ✅ | 中文攻略文章；URL 里的 `/handbook/YYYYMM/` 就是发布年月 |
| [巴哈姆特哈啦板](https://forum.gamer.com.tw/B.php?bsn=5786) | 论坛讨论 | ❌ 繁中 | ✅ | 只作为玩家讨论参考 |

**不作为来源**：monsterhunterwiki.org、アルテマ、NGA 用 curl 和 WebFetch 访问都会 403；Fandom 连接被拒；Gamekee 是 SPA，curl 拿不到正文；工具都读不到，无法核实。篝火营地的内容集中在 2022-07 及更早，神ゲー攻略首页没看到 TU5 之后的内容，版本都偏旧。B 站没有 MHR 的 wiki。用户直接提供这些站的原文时，可以按版本规则判断后参考。

## 各类内容的信息源优先级

| 内容 | 首选 | 交叉核对 / 次选 |
|---|---|---|
| 版本改动、某项内容何时加入或下架 | 官方更新页 | MHRice 切换版本比对 |
| 数值（武器面板、防具、技能效果、肉质、任务、素材与报酬） | Kiranico | MHRice → 游猫网 |
| 中文译名 | Kiranico `/zh`、MHRice 简中（游戏内文本） | 官方 zh-cn 页面 → 游猫网 |
| 活动任务 | 官方活动任务页 | Kiranico 活动任务列表（`/zh/data/quests?view=event`）；下架名单以 16.0.2 更新说明为准 |
| 配装、打法、流程等攻略性内容 | 游猫网配装器、GameWith、Game8 | Fextralife → AppMedia → 游民星空 |

- 攻略性内容不是拆包数据，要逐篇看日期：优先采用 2023-06-08（Ver.16）之后发布或更新的文章，最低也要在 2022-06-30 之后。
- 从外文或社区资料转写时，里面的数值必须回到 Kiranico 或 MHRice 核对，名称必须换成简中官方译名。

## 发布（GitHub Pages）

- 推送到 `main` 后，`.github/workflows/pages.yml` 会先跑检查脚本的测试和 `check_site.py`，然后只把 `site/` 目录部署到 Pages。需要在 GitHub 仓库的 Pages 设置里把来源设为「GitHub Actions」。用 Actions 部署不会经过 Jekyll，不需要 `.nojekyll`。
- 站内链接和资源一律用**相对路径**：项目型 Pages 部署在 `/<仓库名>/` 子路径下，以 `/` 开头的绝对路径上线后会 404（检查脚本会拦下来）。
