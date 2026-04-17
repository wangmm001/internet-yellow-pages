# analysis/web · 统一呈现站点 · Unified Analysis Atlas

> 把 `analysis/china/`、`analysis/countries/`、`analysis/complex_network_images/`
> 三条独立的研究轨道合并进一个共享设计系统的静态站点。
> A single dark-theme, bilingual site that unifies the three IYP analysis tracks
> (China · Nine-Country · Complex Network) under one visual language.

## 构建 · Build

```bash
cd /Volumes/data/internet-yellow-pages
python3 -m analysis.web.build
```

仅依赖 **Jinja2**（纯 Python，已在 IYP 依赖中）——无 Node/npm 工具链。
The only dependency is Jinja2 (pure Python); no Node/npm toolchain is introduced.

## 浏览 · How to view

站点里的交互图表通过 `<iframe>` 直接引用 `analysis/china/html/`、
`analysis/countries/html/`、`analysis/complex_network_images/` 下的原始产物，
因此 **必须从仓库根目录浏览**（以便 iframe 的相对路径能向上解析到同级目录）。
Plotly charts are referenced via `<iframe>` pointing at the existing artefacts
in `analysis/{china,countries,complex_network_images}/`, so the site must be
**viewed from the repo root** (so the iframe relative paths can reach up).

```bash
# 方式 1 · Local HTTP server (from repo root):
cd /Volumes/data/internet-yellow-pages
python3 -m http.server 8765
# open http://localhost:8765/analysis/web/site/index.html

# 方式 2 · Finder / file:// (double-click):
open analysis/web/site/index.html
```

提示：不要 `python -m http.server --directory analysis/web/site` — iframe
的 `../../../../china/html/...` 会越过文档根，返回 404。
Don't serve from inside `site/` — the iframes need to resolve above the doc root.

## 页面清单 · Pages (57 total)

| 层级                              | 入口                               | 数量    | 来源                                                           |
| --------------------------------- | ---------------------------------- | ------- | -------------------------------------------------------------- |
| 首页 Home                         | `site/index.html`                  | 1       | 动态装配主权指数榜单                                           |
| 中国专题 China                    | `site/china/index.html`            | 1 + 27  | iframe `analysis/china/html/step*.html`                        |
| 九国分析 Countries                | `site/countries/index.html`        | 1 + 13  | iframe `analysis/countries/html/profile_*.html` + 4 dashboards |
| 复杂网络 Network                  | `site/network/index.html`          | 1 + 13  | `<img>` `analysis/complex_network_images/*.png`                |

## 设计语言 · Design

视觉令牌（暗色、Apple 风）与键盘导航取自
`/Users/mumu/work/wangmm/openintel-dns-analysis/analysis/web/`：

- Background `#000000` + 蓝紫双向径向光晕 · radial dual-glow gradients
- Primary accents `#0071e3` (blue) / `#5856d6` (purple) / `#30d158` (green) / `#ff453a` (red)
- `Inter` + `Noto Sans SC` + `JetBrains Mono` 字体栈
- 18px 圆角卡片 · subtle hover lift
- 键盘操作 · Keyboard: `←` / `→` 翻页, `G` 全局目录, `Esc` 关闭
- 双语：中文主位、英文次位 · bilingual CN primary / EN secondary

## 架构 · Architecture

```
analysis/web/
├── build.py              # Jinja2 orchestrator · python -m analysis.web.build
├── nav.py                # 所有 57 页的元数据（3 tracks × phases × pages）
├── templates/            # 7 Jinja2 模板
│   ├── base.html         # shell + nav + TOC dialog + lightbox
│   ├── home.html         # hero + 3 track cards + 主权榜单
│   ├── track_hub.html    # China + Network hub（phase filter 可切换）
│   ├── countries_hub.html# 九国画像 + 综合仪表板
│   ├── step_plotly.html  # iframe 包装（China + Countries）
│   └── step_png.html     # <img> 包装 + lightbox（Network）
├── static/
│   ├── site.css          # 设计令牌 + 所有组件
│   └── site.js           # 键盘、TOC、iframe autosize、hero 计数
├── site/                 # 生成产物（committed）
│   ├── index.html
│   ├── assets/site.{css,js}
│   ├── china/…
│   ├── countries/…
│   └── network/…
└── build_manifest.json   # 每页产出 + 源文件 sha1
```

## 嵌入策略 · Embedding strategy

- **中国 + 九国（Plotly HTML）**：通过 `<iframe loading="lazy">` 嵌入既有自包含
  HTML；`site.js` 监听 `load` 事件并读取 `contentDocument.body.scrollHeight`
  以自动适配高度（同源免跨域）；每个卡片头保留「独立打开 ↗」逃生出口。
- **复杂网络（PNG）**：`<img data-lightbox>`，点击即进入全屏 `<dialog>`。
- **为什么不重新生成图表**：~48 个分析脚本已经产出 42 个交互式 HTML 和
  13 张 PNG，共 ~500 MB，若重写为 ECharts 需要数周。本站点的价值是
  **呈现层统一**，不触碰分析层。

## 国别快照维度 · Snapshot dimension

国别 profile HTML 表示 `2026-04` 快照；但每国 metrics JSON 两个快照都有
（`2025-04` + `2026-04`）。per-country 页面顶部渲染一条 **delta-strip**：
主权指数 + AS 数 + 快照标签 + ISO 代码，自动计算 Δ vs 去年。

## 校验 · Verification

`build.py` 在写入每个页面之前 **静态校验** 其 iframe src / img src 均在磁盘上存在；
若上游文件被改名将立即大声失败（非 silent 渲染成 404 iframe）。

构建清单 `build_manifest.json` 记录每页的 `src_sha`（前 12 位），可用来 diff
是否有上游数据被重跑。

## 来源 · Credits

设计语言改编自 `openintel-dns-analysis/analysis/web/`
（Astro + Tailwind v4 + ECharts）；本项目用 **Python + Jinja2** 重新实现，
不引入 Node 工具链。

—— generated 2026-04-17
