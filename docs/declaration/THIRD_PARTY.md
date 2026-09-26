# Third-party dependency register

| Name | Version/Commit | URL | License | Used for | Modified |
|---|---|---|---|---|---|
| Inter | 未固定版本（见下「Provenance」）；文件 `sha256:3100e775e8616cd2` | https://github.com/rsms/inter | SIL OFL 1.1 | 前端正文字体（latin 子集，自托管，现场离线） | 否 |
| JetBrains Mono | 未固定版本（见下「Provenance」）；文件 `sha256:83c005d49d8a6a50` | https://github.com/JetBrains/JetBrainsMono | SIL OFL 1.1 | 前端数值 / 代码等宽字体（latin 子集，自托管） | 否 |
| Press Start 2P | 未固定版本（见下「Provenance」）；文件 `sha256:afec86997fdaf54a` | https://fonts.google.com/specimen/Press+Start+2P | SIL OFL 1.1 | 前端英文标签/标题像素字体（latin 子集，自托管） | 否 |

正式仓库加入任何第三方源码、模型、素材、字体或数据时在此登记。

## 落地方式（`assets` 路线）

三个字体为 **latin 子集 `woff2`**，落地于 `frontend/public/fonts/`，由
`frontend/scripts/fetch-fonts.mjs` 下载并生成 `frontend/src/design/fonts.css`（`@font-face`）：

| 文件 | 大小 |
|---|---|
| `frontend/public/fonts/inter-latin.woff2` | 48256 B |
| `frontend/public/fonts/jetbrains-mono-latin.woff2` | 31432 B |
| `frontend/public/fonts/press-start-2p-latin.woff2` | 12512 B |

中文不打包（像素字体不覆盖 CJK），一律走系统字体；因此以上三个文件对该字体许可的
**再分发**不涉及 CJK 子集。

## Provenance（已知弱点，待收口）

`fetch-fonts.mjs` 经 **Google Fonts CSS2 API**（`https://fonts.googleapis.com/css2?family=…`）
下载「最新版」，**该 API 不返回版本号**，故 `Version/Commit` 无法填语义版本。当前以
**文件内容 `sha256` 前缀**锁定可复核的身份（完整值见上表来源；复算：
`sha256sum frontend/public/fonts/*.woff2`）。

收口方式（脚本层面，尚未实施）：改为从各字体 GitHub Release 的**固定 tag** 下载，
使 `Version/Commit` 可填 tag/commit。此改动归 `frontend/scripts/fetch-fonts.mjs`（李辰钊 lane），
已在 `frontend/交接-给池伟豪-前端分工与开工包.md` §7.1 记录。

许可判断依据：三字体各自官方仓库/Google Fonts 页面均声明 **SIL OFL 1.1**；本表按登记时的
公开声明填写，未逐条比对 `OFL.txt` 全文。
