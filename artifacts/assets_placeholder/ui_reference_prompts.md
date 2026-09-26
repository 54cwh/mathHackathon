# UI 视觉参考图提示词（ChatGPT 内置生图用）

> 用途：为 `frontend/交互与可视化.md` §1 那句「最终视觉主题等待参考图后冻结」提供可执行的参考图生成方案。
> 生成工具：ChatGPT 内置生图。
> 书写依据：**`gpt-image-prompt` skill**（本机 `~/.claude/skills/gpt-image-prompt/SKILL.md`）。
> 该 skill 的硬规则已逐条落到本文件：**提示词用英文**（图像模型对英文更可靠）、**固定标签化结构**、
> **比例只用网页版认的三种**、**颜色写 hex 不写色名**、**AS-IS 行阻止 ChatGPT 自行加戏**。

## 快速开始（4 步 —— 这 3 条提示词是全流程最高优先）

```text
1. 跑提示词 1 / 3 / 4（每条新开一次对话）→ 得 3 张参考图
2. 挑 1 张 —— 怎么挑见 §选型对照表；取色板以「提示词 3」为准
3. 把选定的图交给 ChatGPT，用 §步骤 2 的「取色板提示词」让它吐 hex
4. 把 hex 回填 §候选色板，并填进 asset_prompts.md 的 {色板}
```

**跑哪 3 条**（Q7 = 跑 1 + 3；Q8(a) 让 Dashboard 住进 `Evolution` 视图，故再 +1 条）：

| 跑 | 得到什么 |
|---|---|
| 提示词 **1** | 「极限观感」—— 纯像素外壳的观感上限，用来判断颜色能推到多艳 |
| 提示词 **3** | 「可交付折中」—— 像素 Arena + 精密数据区；**色板以它为准** |
| 提示词 **4** | `Evolution` 视图（9 项 Dashboard）—— 同时是**「精密面板」的样板** |

提示词 **2**（sprite sheet）本轮**不必跑**，已降级为风格对照图（见该节内的 skill 警告）。

**这 3 条为什么最重要**：它们冻结的是**整套视觉系统的上游** —— 配色、密度、层级、质感，
以及「哪些地方像素、哪些地方精密」这条边界。色板从它们身上取，之后 20 张素材全部依赖这个色板。
**这几个没定，后面全是白做。**

粘贴注意：每条是一个完整的 `text` 代码块，**整块复制**，不要只挑几句；
**首行 `Use this prompt AS-IS.` 不要删**。
## 决定记录（2026-09-26 第二轮：grill → 拍板）

> 来源：辰钊对 10 题的回答「**都按照推荐**」，及第二轮 5 条由 Q1/Q2 **推论**出的决定。
> 全部决定在此登记，**不留沉默假设**。

| # | 决定 | 理由（非显然的才写） |
|---|---|---|
| Q1 | **结构像素化 + 文字层清晰**：边框/按钮/图标/分割线/Arena 走像素；**数值与长标签走等宽清晰字体** | 全局像素化与已装 ECharts/Cytoscape 正面冲突（不原生支持像素渲染），且 13 字段读不动 |
| Q2 | **双调性**：亮外壳 + 暗 Arena（`#0B1220` 系） | 水越深越暗是物理直觉；A8 海洋背景已按暗调写 |
| Q3 | **三栏严格等宽**；若要 Arena 更宽，**先改 `App.tsx` 再让参考图跟随** | 在参考图里画代码没打算实现的布局，是「像真界面」最容易骗到自己的地方 |
| Q4 | 顶栏数据项**抽象占位**；**但 `Env` 显示 `Food Rich`** | `Food Rich` 是 `App.tsx` 里的硬编码字符串，不是跑出来的数据 → 显示它不触红线 |
| Q5 | **像素徽标 + 字标并排**（徽标此刻只是占位块） | 顶栏左端宽度预算取决于有没有图形；定下来 C1 生成时才知道该做多大 |
| Q6 | 可进 PPT 但**必须标注「视觉方向参考」**；不进论文正文；**另补视觉冻结判据 + 冻结时点** | 它看起来像真界面，进论文正文会被读作伪 data |
| Q7 | 跑**提示词 1 + 3**，另加**新第 4 条（Evolution 视图）** | 1 给「极限观感」（颜色上限），3 给「可交付折中」；色板以 3 为准 |
| Q8 | **Fish Card = Arena 栏内就地浮层**（挂已实现的 `selectedFishId`）；**Dashboard = 底栏三词改成真视图 tab**，住进 `Evolution` 视图 | 不引入新容器；底栏那三词在代码里现在只是灰色文字，本来就是留给视图切换的 |
| Q9 | 中栏 Brain Forge 改**抽象连接占位** | §12 逐字把 `network graphs` 列进「禁止用于伪造」；「稀疏→密集的发展序列」正是 §8 真实数据的形态，最容易被读作结果 |
| Q10 | **Arena 5:3 写进提示词** | `frontend/README.md:127` 明令「不得非等比拉伸，否则鱼会被纵向压扁」 |
| R2-1 | **交界**＝硬 1–2px 深色分割线，两区共用同色同粗细；**禁渐隐/模糊/发光** | 渐隐属于平滑渐变，违反像素原则 |
| R2-2 | **精密区**＝浅色面板 + 等宽数值 + 1px 锐边、**无圆角** | Q1(b) 与 Q2(a) 的直接推论 |
| R2-3 | **双主题不做**，只做明亮单主题 | 双主题会让 20 张素材、`index.css`、验收全部翻倍，时间不允许 |
| R2-4 | **面板外壳去圆角**，改像素斜角边框；标题栏图标改像素图标 | 代码现在是 `rounded-lg` + lucide 图标，与 Q1(b) 冲突 |
| R2-5 | **Fish Card 不单独出参考图** | 它是密集数据表，样式由第 4 条「精密面板」直接派生 |

**由此产生的一条硬约束**（写进提示词 1 / 3）：**三栏严格等宽 + Arena 5:3 ⟹ Arena 的高度被它的宽度锁死。**
参考图里 Arena 若画得比 5:3 高，你按它取比例，实现时鱼就会被纵向压扁。


## 变更记录

- **2026-09-26（第二次修订）**：按 `gpt-image-prompt` skill 重写三条提示词，改动逐条列在
  §「本次按 skill 改了什么」。**最重要的一条：「分辨率 16:9」是错的**——见 §比例。
- **2026-09-26 修订**：视觉方向改为**像素质感**（16 位农场 / 沙盒游戏一类气质）。此前暗色系三变体按辰钊要求作废，已移除。
- 同时修正两处路径引用：`docs/design/08_交互与可视化.md` → `frontend/交互与可视化.md`；`docs/design/17_验收清单.md` → `docs/验收清单.md`（`docs/design/` 已于 `a8ded6d` 归位，原路径不再存在）。

## 使用前提（红线不变）

依据本项目 `frontend/交互与可视化.md` §12 与 `artifacts/assets_placeholder/image_prompt_template.md`：

- 生成的图**只能当作视觉方向参考**，用于确定配色、密度、层级、质感。
- **不得**作为界面截图放入答辩稿或论文——它看起来像真实界面，会被读作伪 data。
- 提示词中所有图表区一律要求「抽象占位、无可读数值」。
- **不得复制任何商业游戏的角色、道具、场景或界面元素**（`image_prompt_template.md` 明写「不复制商业游戏角色」）。下述提示词只借用像素美术的**通用质感语言**，不指向任何具体作品资产。

---

## 本次按 skill 改了什么（可审计）

| # | 原写法 | 改后 | 依据 |
|---|---|---|---|
| 1 | 提示词正文为**中文** | **英文**，中文只留标题与「要点」行 | skill：`Write the prompt in English`；图像模型对英文更可靠 |
| 2 | 段落式散文，风格在前 | **固定标签序列**：Background → Subject → Key details → Style → Composition → Lighting → Text → Constraints → Avoid | skill：`Prompt structure (fixed order)`；复杂需求用短标签行 |
| 3 | `分辨率 16:9` | **`Landscape 3:2 composition.`** + 后处理裁到 16:9 | skill：网页版只认 `square 1:1 / landscape 3:2 / portrait 2:3`，**16:9 不被认** → 见 §比例 |
| 4 | 色名「草绿、木棕、天空蓝…」 | **逐个 hex**（见 §候选色板） | skill：`give hex codes inline … far more reliable than color names` |
| 5 | 一图要求 **12 处英文文字** | 压到 **7 处**，并给出**占位回退**规则 | skill：每图不超过 3-4 个短标签；文字是最易出错的部分 |
| 6 | 无 | 首行加 **`Use this prompt AS-IS. Do not add or embellish any details.`** | skill：`Stop prompt rewriting`——ChatGPT 爱给提示词加戏 |
| 7 | 无 | **一条提示词 = 一次新对话** | skill：`Same-chat memory`——同对话元素会渗进下一张 |
| 8 | 「高清」类词 | 删掉，只留具体比例与硬边要求 | skill：`Anti-tacky`——不写 8K / 高清 / cinematic 一类空泛词 |
| 9 | 无 | 明确 **`no checkerboard pattern`** | 模型画「透明」时常画**假棋盘格图案**（见 `asset_prompts.md` §2） |

## 比例：为什么 16:9 要改成 3:2，以及怎么补回来

skill 明确：**ChatGPT 网页版只认三种比例**——`square 1:1` / `landscape 3:2` / `portrait 2:3`，
并要求在提示词**开头用文字声明**。所以把 `16:9` 写进提示词是无效的，改为：

- 提示词里声明 **`Landscape 3:2 composition.`**；
- 出图后**裁到 16:9**：3:2 → 16:9 需**裁掉高度约 15.6%（上下各约 7.8%）**，宽度不变。
  这就是提示词里反复要求 **`even margin on all sides`** 的原因——留边距给裁切。
- 裁切归 `asset_prompts.md` §6 的后处理流水线。

## 候选色板（**唯一定义处**）

> 这一节是候选色板的**唯一 owner**（`asset_prompts.md` 只引用，不另立一版）。
> 它不是最终色板：**最终色板 = 你选定的那张参考图取色结果**，取完写进 `frontend/src/index.css`
> （届时 owner 移交 `index.css`），再把 hex 填进 `asset_prompts.md` 的 `{色板}`。
> 这里的 24 色只是**为了能把参考图生出来**而给的起步候选，全部避开键控色 `#FF00FF`。

| 用途 | 色名 | hex | 用途 | 色名 | hex |
|---|---|---|---|---|---|
| 描边 | ink | `1A1C2C` | 木土 | bark dark | `5A3A22` |
| 暗部 | slate shadow | `333C57` | 木土 | wood brown | `8A5A33` |
| 冷灰 | blue grey | `566C86` | 木土 | sand warm | `C6854A` |
| 深水 | deep water | `1E6F9F` | 木土 | sand light | `E8C179` |
| 中水 | mid water | `2E9BC7` | 点缀 | amber | `F2A93B` |
| 浅水 | shallow water | `6FD3E8` | 点缀 | coral orange | `F08A5D` |
| 反光 | foam | `B6F0F5` | 点缀 | danger red | `E4595C` |
| 深草 | deep grass | `2F6B3A` | 点缀 | mutation violet | `9B5DE5` |
| 草绿 | grass green | `4C9A3F` | 中性 | white | `FFFFFF` |
| 亮草 | light grass | `8ED14B` | 中性 | bone | `D9E0E8` |
| 鱼体深 | fish navy | `2B3A67` | 中性 | stone grey | `7A8A99` |
| 鱼体浅 | fish blue | `5C7CB8` | 中性 | stone shadow | `4A4A5A` |

**Arena 面板与 UI 外壳是两个调性，这是有意的**：UI 外壳走**明亮自然调**（本表主色群）；
Danio Arena 是**水下俯视**，自然偏暗——它沿用画布底色 `#0B1220` 系（`DanioArenaPanel.tsx` 现值），
素材只需「在 `#0B1220` 上可辨」。**不要**为了统一把 Arena 也提亮：水下场景提亮会失去纵深。

---

## 选型对照表（1 / 3 / 4 各给你什么）

| 你若最看重 | 选 | 理由 |
|---|---|---|
| 路演 / 答辩第一眼的冲击力 | **提示词 1** | 纯像素外壳，观感最强；代价是数据区不实用（9 项指标、13 字段塞不进这种密度） |
| 工程上真能落地 | **提示词 3** | 像素 Arena + 精密数据区，唯一不牺牲数据可读性的折中 |
| 看 Dashboard 与「精密面板」的样子 | **提示词 4** | `Evolution` 视图；同时是 Fish Card 与指标卡的样式模板（R2-5） |
| 看全套素材风格是否统一 | 提示词 2（**可选**） | 用途已降级为**风格对照图** |

**色板以提示词 3 的取色结果为准**（不是 1，也不是 4）—— 因为 3 才是要真正搭出来的界面，
它的表面才是 `index.css` 要承载的。1 的色板更艳，直接拿去配 UI 会压不住小字号文本。

**Q1(b) 的边界在这里兑现**：边框/按钮/图标/分割线走像素，**数值与长标签走等宽清晰字体** ——
所以取色时**别只取像素区的高饱和色**，要**单独取一对文本色**（正文色 + 次文字色），
否则 `index.css` 里那 19 个 token 有三分之一没着落。

**Arena 面板的水下暗调不参与取色**：它沿用画布底色 `#0B1220` 系（见 §候选色板 末段）。
## 提示词 1 —— 整台界面像素质感（主诉求 · 风格定调图）

**定调理由**：直接对应「像素风实验台」。明亮、饱和、有限调色板，俯视视角，接近 16 位农场模拟游戏的暖色自然调。
**定位说明**：这一条是**风格定调图**，目标是定颜色/密度/层级/质感，**不是**可交付界面
（skill 的 `ui-mockup` 类目要求 realistic product UI, shippable look，本图不追求那个；追求可交付的是提示词 3）。

**要点**：本轮按 Q1(b)/Q2(a)/Q3/Q4/Q5/Q8/Q9/Q10 全部改写 —— 三栏**严格等宽**、Arena **5:3**、底栏三词改**真视图 tab**（`Experiment` 激活）、中栏改**抽象连接占位**（不触 §12）、`Env` 显 `Food Rich` 而其余 5 项为占位块、徽标+字标并排、**全图去圆角**。本条所有数据值都是占位块，因此 Q1(b)「数值走等宽」在本条**无适用对象**（等宽字体在第 3、4 条才登场）。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Landscape 3:2 composition.

Background: a bright, saturated 16-bit pixel-art scene acting as the app's own backdrop - grass green and warm earth tones, with thin dark pixel outlines as the only dark elements.

Subject: a complete desktop web application screen for a life-evolution lab named "EvoGenesis", drawn entirely in 16-bit pixel art: a top status bar, a three-column main area of exactly equal width, and a bottom control bar. Do not draw any page title, heading or caption beyond the labels listed below.

Key details:
Top status bar: one pixel-art horizontal strip with a beveled pixel frame, light on the top-left edges and dark on the bottom-right, built from square pixel steps with NO rounded corners. The left end shows a small pixel emblem, a simple abstract mark containing no letters, followed by the product name "EvoGenesis" in a dot-matrix pixel font. The right end has six status items in a row, each one small pixel icon plus one short label: first "Env", whose value reads "Food Rich"; then "Gen", "Fish", "Prey", "Step", "Seed", whose values are each a plain uniform pixel block of placeholder width rather than any readable number.
Main area: three columns of exactly equal width, separated by 2-pixel pixel divider lines. Each column is headed by a small pixel icon plus a pixel-font title.
Left column "DNA2Brain Lab": the upper half is a three-dimensional-looking pixel DNA double helix built from bright candy-colored pixel blocks, with the chunky feel of a retro game power-up; the lower half is a flat sequence strip of the letters "A" "C" "G" "T" in a dot-matrix pixel font, with one letter highlighted by a pixel selection box and a small pixel triangle marker.
Middle column "Brain Forge": an abstract pixel connection pattern - geometric pixel nodes joined by 1-pixel lines, evenly distributed, deliberately NOT readable as a network topology: no legible node or edge counts, no labels, no axes, no progression from sparse to dense, and nothing that reads as a measured quantity. It is decorative texture only. Three cell types are marked by three clearly different pixel colors.
Right column "Danio Arena": a top-down pixel pool arena in a panel whose width-to-height ratio is exactly 5 to 3. Water surface in blue-green pixel blocks with dithered ripples; the bank is grass and stone pixel tiles; in the water swim several slender pixel zebrafish, dark body with light horizontal stripes, a few much smaller prey dots, one clearly larger predator silhouette, and several square pixel obstacle blocks. The panel edge is a beveled pixel frame with no rounded corners.
Bottom control bar: one thin pixel strip. The left end has two pixel buttons with beveled edges and a pressed feel - the primary button labeled "Pause" and a secondary button labeled "Reset". The right end has three small pixel buttons reading "Evolution", "Experiment", "Playback", forming view tabs; the "Experiment" tab is the active one and is drawn pressed or highlighted.

Style: 16-bit pixel art, hand-placed square pixels, hard pixel edges, no antialiasing and no smoothing anywhere. No rounded corners anywhere - every frame, panel and button is built from square pixel steps. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8. Do not introduce any color outside this list. All line weights are exactly 1 or 2 pixels. Use dithering patterns for all transitions.

Composition: the full app screen fills the frame with an even margin on all sides; the three columns are exactly equal in width; hierarchy is carried by size and color, never by drop shadows.

Lighting: flat and even, no light source - hand-placed highlight and shadow pixels only.

Text: the only text in the image is the set of labels listed above. Render each one verbatim in a dot-matrix pixel font with correct spelling and no extra characters. Values other than "Food Rich" must NOT be rendered as numbers. If any label cannot be rendered legibly, replace it with a clean uniform pixel block of the same size - never invent letters and never render garbled or blurry text.

Constraints: this is a UI mockup, not a poster and not concept art; keep the layout tidy and grid-aligned; no readable data values anywhere - every data area is an abstract placeholder.

Avoid: antialiasing, soft or blurred edges, smooth gradients, soft shadows, rounded corners, glassmorphism, modern flat UI, 3D rendering, photorealistic textures, a dark moody palette, cyberpunk neon, any readable numbers or statistics, any fake charts or graphs, watermark; do not copy any specific existing game's characters or interface.
```

---

## 提示词 2 —— 素材包：像素 sprite sheet

**定调理由**：这是**最容易落地、风险最低**的一档，且与项目 `image_prompt_template.md` 预留的三类素材（Fish sprite / Predator / DNA）精确对接。UI 框架不动，只把游戏内对象像素化。

**但有一条 skill 警告必须写在前面**：本条「一张大表里塞 7 类素材」**违反 skill 的已知限制**
（`many distinct subjects in one image is hard -> keep one focal subject or split into multiple images`）。
所以：

- 若你要**逐张精修**，请用 `asset_prompts.md` 的 A/B/C 逐图提示词，**不要用本条**；
- 本条保留的用途是**一次看到全套素材的相对关系**（尺寸层级、风格是否统一），当作**风格对照图**，
  不作为最终切图来源。真要用它切图，前提是你接受风格不一致与切分成本。

**要点**：这一条**故意不拆**，因为它的价值就在「一次看全」；其余同提示词 1（英文、标签结构、hex、AS-IS）。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Landscape 3:2 composition.

Background: a solid flat magenta #FF00FF covering the whole image. No gradient, no texture, no checkerboard pattern.

Subject: one 16-bit pixel-art sprite sheet, all assets laid out in a neat evenly spaced grid with a clear magenta gutter between every item, no labels and no text anywhere.

Key details, seven families:
1) zebrafish sprite, viewed from directly above, long slender streamlined body, dark body with lighter horizontal stripes, in five separate orientations (up, down, left, right, diagonal) - five sprites.
2) juvenile zebrafish sprite, same design language but clearly shorter and simpler, three orientations - three sprites.
3) prey sprite, a small round bright warm-colored creature, two orientations, visually much lighter in weight than the fish.
4) predator sprite, clearly much larger and more imposing than the fish, dark with a sharp aggressive silhouette, two orientations - its danger tier must read instantly.
5) a short DNA double helix of candy-colored pixel blocks, three different rotation phases.
6) four base icons for "A" "C" "G" "T", small pixel symbols in four clearly distinct colors.
7) environmental tiles: water surface, deep water, grass, stone, sand - one each, identical size, seamless edges.

Style: 16-bit pixel art, hand-placed square pixels, hard pixel edges, no antialiasing, no smoothing. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8, plus magenta FF00FF used only as the flat background. Do not introduce any color outside this list. Use dithering patterns for all transitions.

Composition: one grid, all items in the same visual scale family, evenly spaced, none touching the image edge; the full set visible with an even margin on all sides.

Lighting: flat and even, no light source - hand-placed highlight and shadow pixels only.

Text: none. No letters, no numbers, no labels, no watermark.

Constraints: every item must read clearly at very small size; the whole sheet must look like one consistent set drawn by one artist.

Avoid: antialiasing, gradients, soft shadows, 3D rendering, photorealism, any text or watermark, any scene background other than the flat magenta; do not copy any specific existing game's characters or props.
```

---

## 提示词 3 —— 分区混合（工程上最稳）

**定调理由**：竞技场拿像素游戏感，数据区保持专业可读。这是像素风与「9 项指标的 Dashboard、13 字段的 Fish Card、精确的 ACGT 序列」共存时唯一不牺牲功能的做法。
**定位说明**：这一条是三条里**最接近可交付界面**的一档，也是 skill `ui-mockup` 类目真正对应的那条。

**要点**：同上，另加一节 **`Junction:`** —— 双调性的唯一接缝，也是全图最难调的地方（硬 1–2px 分割线、两区共用同色同粗细、**禁渐隐**）；数值明确走**等宽字体**；浅色精密区**无圆角**。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Landscape 3:2 composition.

Background: split by region - the right column sits on a dark deep-water arena palette, while the left column, the middle column and both horizontal bars sit on a clean light panel surface. The regions meet along a hard dark divider, never a soft fade.

Subject: a complete desktop web application screen for a life-evolution lab named "EvoGenesis", in a deliberately hybrid style: the game-like region is 16-bit pixel art, the data-dense regions are precise modern scientific software, unified by a single shared palette. Do not draw any page title, heading or caption beyond the labels listed below.

Key details:
Top status bar and bottom control bar: pixel-art beveled frames and pixel buttons built from square pixel steps with NO rounded corners. Every numeric readout inside them is set in a clean monospace font, not a pixel font.
Top bar left end: a small pixel emblem, a simple abstract mark containing no letters, followed by "EvoGenesis" in a dot-matrix pixel font.
Top bar right end: six status items - first "Env", whose value reads "Food Rich"; then "Gen", "Fish", "Prey", "Step", "Seed", whose values are each a plain uniform placeholder block rather than any readable number.
Bottom bar left end: a primary pixel button labeled "Pause" and a secondary pixel button labeled "Reset".
Bottom bar right end: three pixel buttons reading "Evolution", "Experiment", "Playback", forming view tabs, with "Experiment" drawn as the active tab.
Right column "Danio Arena": entirely 16-bit pixel art - a top-down pool arena in a panel whose width-to-height ratio is exactly 5 to 3. Blue-green water with dithered ripples, grass and stone pixel tiles at the bank, slender pixel zebrafish with dark bodies and light stripes, a few much smaller prey dots, one clearly larger predator silhouette, and several square pixel obstacle blocks. Beveled pixel frame, no rounded corners.
Left column "DNA2Brain Lab" and middle column "Brain Forge": clean, precise modern scientific software on a light panel - no pixel font, crisp 1-pixel edges, no rounded corners. The left column's upper half is a sharply drawn 3D DNA double helix; its lower half is a monospace sequence strip of the letters "A" "C" "G" "T" with one letter inside a crisp selection box. The middle column is an abstract connection pattern of small nodes and thin lines, evenly distributed, deliberately NOT readable as a network topology - no legible node or edge counts, no labels, no axes, no sparse-to-dense progression, and nothing that reads as a measured quantity. Decorative texture only. Three cell types appear in three distinct flat accent colors.
The top and bottom bars span the full width; the three columns are exactly equal in width.

Junction: where the dark pixel arena meets the light precise panels, the boundary is a single hard dark divider line of 1 to 2 pixels, shared by both sides and using the same colour and the same weight as the top and bottom bar frames. Do not fade, blur, glow or gradient across this boundary. Because both regions draw from one palette, the join must read as intentional rather than pasted.

Style: hybrid - the pixel region follows 16-bit pixel art with hand-placed square pixels, hard edges and no antialiasing; the precise regions follow clean vector-drawn UI with sharp 1-pixel edges. Neither region uses rounded corners. Both regions share one palette. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8. Do not introduce any color outside this list.

Composition: the full app screen fills the frame with an even margin on all sides; the three columns are exactly equal in width; the join between the pixel and precise regions must feel intentional - same divider weight, same corner treatment, same palette.

Lighting: even and flat in both regions; no drop shadows, no glass effects.

Text: the only text in the image is the set of labels listed above. Render each one verbatim with correct spelling and no extra characters; labels in the bars use a dot-matrix pixel font, and numeric readouts use a clean monospace font. Values other than "Food Rich" must NOT be rendered as numbers. If any label cannot be rendered legibly, replace it with a clean uniform block of the same size - never invent letters and never render garbled or blurry text.

Constraints: this must read as one coherent product interface, not a collage; no readable data values anywhere - every data area is an abstract placeholder.

Avoid: a dark moody background for the whole app, antialiased fake-pixel edges, gradients, rounded corners, glassmorphism, 3D rendering, any readable numbers or statistics, any fake charts or graphs, watermark; do not copy any specific existing game's characters or interface.
```

---

## 提示词 4（新）—— Evolution 视图（Dashboard 9 项 · 「精密面板」的样板）

**要点**：本条是 Q8(a) 的产物 —— Dashboard 住进 `Evolution` 视图，底栏 `Evolution` tab 激活。**它同时定义「精密面板」的模板**：Fish Card 的 13 字段与将来的指标卡都照它搭，所以 R2-5 不再单独出图。9 个卡名取自 `frontend/交互与可视化.md:110-118` 的**真实指标名**（不是编的）；但**所有数值/坐标/刻度/图例一律占位块**（红线：不得出现可读数值）。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Landscape 3:2 composition.

Background: a clean light panel surface covering the whole frame. The only pixel-art elements are thin beveled pixel frames and pixel buttons. There is no dark region anywhere in this image.

Subject: the "Evolution" view of the same application - a data dashboard for a life-evolution lab named "EvoGenesis". Do not draw any page title, heading or caption beyond the labels listed below.

Key details:
Top status bar: identical in style and content to the other views of this app - a pixel-art beveled strip built from square pixel steps with no rounded corners. The left end shows a small pixel emblem, a simple abstract mark containing no letters, followed by "EvoGenesis" in a dot-matrix pixel font. The right end has six status items: first "Env", whose value reads "Food Rich"; then "Gen", "Fish", "Prey", "Step", "Seed", whose values are each a plain uniform placeholder block rather than any readable number.
Main area: a neat grid of nine equal cards, three columns by three rows, evenly spaced, separated by thin crisp 1-pixel lines, with no rounded corners. Each card has a short label set in a clean monospace font, and below it one abstract placeholder visual - alternating simple bar clusters, simple line shapes and simple block rows, drawn in flat accent colours. Every number, axis value, tick, unit and legend entry is replaced by a plain uniform placeholder block, so that no quantity can be read from the image.
The nine card labels, in reading order, left to right then top to bottom: "generation", "p(A) p(B)", "genotype freq", "fitness dist", "viability", "mean neurons", "mean edges", "mean tau", "env change".
Bottom control bar: same as the other views - a primary pixel button labeled "Pause", a secondary pixel button labeled "Reset", and three pixel buttons reading "Evolution", "Experiment", "Playback" forming view tabs, with "Evolution" drawn as the active tab.

Style: precise modern scientific software on a light panel with crisp 1-pixel edges and no rounded corners, combined with pixel-art beveled frames and buttons. No pixel font is used for the data itself. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8. Do not introduce any color outside this list.

Composition: the nine cards form a regular 3-by-3 grid filling the main area evenly; the whole app screen fills the frame with an even margin on all sides.

Lighting: even and flat, no light source, no drop shadows.

Text: the only text in the image is the set of labels listed above. Render the bar labels in a dot-matrix pixel font and the nine card labels in a clean monospace font, each one verbatim with correct spelling and no extra characters. No numbers, no units, no axis values, no legend entries and no captions may appear anywhere. If any label cannot be rendered legibly, replace it with a clean uniform block of the same size - never invent letters and never render garbled or blurry text.

Constraints: no readable data values anywhere - every data area is an abstract placeholder; this is a UI mockup, not a poster.

Avoid: a dark background, antialiasing, gradients, rounded corners, glassmorphism, 3D rendering, any readable numbers or statistics, any axis or legend values, any fake chart presented as a real result, watermark; do not copy any specific existing game's characters or interface.
```

---

## 步骤 2 —— 取色板提示词（在**同一对话**里追问，交给 ChatGPT）

**为什么要 ChatGPT 做而不是我做**：取色板本质是**看图**判断——哪些色是主色群、哪些是同一色的明暗档、
哪些该合并。视觉模型看得到图，我看不到，所以**这一步归 ChatGPT**，我只负责把你拿回来的 hex 记下来。

**在生成那张图的同一个对话里**接着贴这段（同对话它才看得见那张图）：

**要点**：要的是「能复现这张图观感的一套调色板」，**不是像素直方图**——后者会吐出几百种近似色。
另外顺手要回「像素刻度 + 描边粗细 + 分割线粗细」，这是重写 `index.css` 时要用的规格（见 §选定后的下一步）。
**本轮补的一条**：另要「面板底色 + 正文色 + 次文字色」这三个 —— Q1(b) 让数值走等宽字体，而 9 项 Dashboard 与 Fish Card 都是**浅底小字**，可读性全押在这一对文本色上；原来的 `neutrals and highlights` 分组**不保证**覆盖到它们（多半只给白色高光）。

```text
I want the exact colour palette from the image you just generated, to use as a fixed asset palette.

Analyse that image and return a palette of at most 32 colours that would be sufficient to REPRODUCE its look. This is a deliberate palette, not a histogram: choose the minimum set that covers every distinct hue and value step actually used, and merge near-duplicates.

Rules:
- Give every colour as a 6-digit uppercase hex code with no leading # and no other punctuation, in the form "name HEX".
- Group them by role, in this order: outlines and darkest values; shadow tones; main material families (water, vegetation, wood and earth); accents; neutrals and highlights.
- Order each group from darkest to lightest.
- Do NOT include pure magenta FF00FF - it is reserved as a key colour for cutouts and must never appear in the palette.
- Then list separately, as its own short block, the three colours a UI needs for readable text on a light panel: the panel background, the primary text colour, and the muted secondary text colour. Choose these so small monospace numerals stay comfortable to read - pick them for legibility, not for decoration.
- If the image uses fewer than 32 colours, return exactly the colours it uses. If it uses more, merge the closest ones so the total is 32 or under.

After the grouped list, output one final line containing only the comma-separated "name HEX" pairs on a single line, so I can paste it directly.

Then report, in three short lines:
1. Pixel scale: how many device pixels wide one logical pixel block is, measured on the largest flat square block.
2. Outline weight: the typical outline thickness in logical pixels.
3. Divider weight: the typical thickness of a panel divider or border, in logical pixels.

Be approximate and honest. If you cannot determine a value, say so instead of giving a precise-looking wrong number.
```

**拿到什么算合格**：

- [ ] 总数 **≤ 32**，且**不含 `FF00FF`**
- [ ] 最后那一行**单行逗号列表**存在（直接可粘进 `{色板}`）
- [ ] 分组顺序是「描边/暗部 → 影调 → 主材 → 点缀 → 中性/高光」
- [ ] 它**没**声称能精确到像素级——若它给了「精确」的刻度数字，追问一句「你实际是怎么测的」

## 步骤 3 —— 不满意时怎么追问（贴着同一张图迭代）

skill 的 `Failure-mode troubleshooting`，按本项目的实际症状改写。
**每次只改一处**，并在追问里重复**不变量**（skill：改图必须声明「只改 X，其它不动」）。

```text
Change only what I describe below. Keep everything else exactly unchanged - layout, framing, lighting, palette, and all text you already rendered correctly.
```

按症状挑对应的一句接在上面后面：

| 你会看到 | 接这一句 |
|---|---|
| 三栏宽度不均 / 布局歪 | `Make the three columns exactly equal in width and keep every element on a strict grid.` |
| 像素边缘发虚、像假像素 | `Make every edge hard-edged square pixels. No antialiasing, no blur, no smoothing. Redraw the whole image on a coarser pixel grid.` |
| 出现了具体数值 / 曲线 / 图表（红线） | `Remove all numbers, axes, curves and charts. Replace every data area with an abstract placeholder of the same size.` |
| 某个英文标签乱码 / 拼错 | `Replace any label that is not perfectly legible with a clean uniform pixel block of the same size. Do not invent letters and do not add characters.` |
| 颜色跑出候选色板 | `Restrict every colour to the palette I gave. Do not introduce any colour outside that list.` |
| 多出了没要的元素（水波、光晕、道具） | `The image contains only the elements I listed. Remove everything else. No added decoration, no watermark.` |
| 比例被忽略（不是 3:2） | **不要在同一对话里继续改**——skill：网页版只认它认的比例，连续忽略就**新开对话**重新粘贴完整提示词，并重申 `Landscape 3:2 composition` |
| 改了 3 次越改越歪 | skill：多轮迭代会漂移 → 把最终所有要求**汇总成一份完整 prompt，新开对话**重生成 |

**一个调试法**（skill 直接给的）：结果一直不对，就直接问它
`show the exact prompt you used for the last image` —— 能看到它擅自改了什么，改完**换新对话**重来。

## 生成后自检清单

**判据来源**：`frontend/交互与可视化.md` §12（生成式视觉素材边界，逐字引用见 §使用前提）
与本文件 §决定记录。

**⚠️ 更正一处假引用**：本节此前写「对照 `docs/验收清单.md` 的 Demo 部分」—— 那 6 条里
**没有一条是视觉判据**（唯一沾 UI 的是 `reset`），**已删**。视觉冻结的判据与时点改由
`frontend/交互与可视化.md` 的「视觉冻结判据」一节承载（2026-09-26 新增）。

- [ ] **比例是 landscape 3:2**（不是 16:9 —— 网页版不认；也不是正方形）
- [ ] **三栏严格等宽**，且左中右内容对得上 DNA2Brain / Brain Forge / Danio Arena
- [ ] **Arena 是 5:3**（不是高瘦的竞技场 —— 否则实现时鱼会被纵向压扁）
- [ ] 顶部六项齐全，且 **`Env` 的值是 `Food Rich`**、**其余 5 项是占位块**（不是数字）
- [ ] 底栏：主按钮 + `Reset`，且 **`Evolution` / `Experiment` / `Playback` 是按钮或 tab 形态**
      （不是灰色小字 —— 这是 Q8(a) 要改代码去对齐的一处）
- [ ] 中栏 Brain Forge 是**抽象连接占位**（无可读节点数、无坐标、无「稀疏→密集」序列）
- [ ] 像素是**方形硬边**（不是被抗锯齿柔化过的「伪像素」）
- [ ] **全图无圆角**（面板外壳已按 R2-4 改像素斜角边框）
- [ ] **数值与长标签走等宽清晰字体**；点阵像素字体只用于标签（Q1(b)）
- [ ] 双调性时：**交界是硬 1–2px 深色分割线**，无渐隐 / 模糊 / 发光
- [ ] 颜色**落在候选色板内**，没有跑出表外的颜色
- [ ] **没有**出现具体数值、曲线或统计图（红线）
- [ ] **没有**与任何现有游戏资产雷同的角色或界面（红线）
- [ ] 主体四周**留了边距**（3:2 → 16:9 要裁掉上下各约 7.8%）
- [ ] 若跑的是提示词 3，像素区与精密区的衔接是否自然
## 两条操作纪律（skill 直接要求，不做就会踩坑）

1. **一条提示词 = 一次新对话。** skill 的 `Same-chat memory`：ChatGPT 记得同一对话里先前生成的图，
   **前面那些元素会渗进新图**。想生成一个真正独立的新主体，**新开对话**再粘贴。
2. **首行 `Use this prompt AS-IS.` 不要删。** skill 的 `Stop prompt rewriting`：ChatGPT 爱给提示词
   「锦上添花」，加进你没要的东西（水波、光晕、额外道具）。删掉这一行它就自由发挥。
   附一个调试法：结果不对时，直接问它 **"show the exact prompt you used for the last image"**，
   就能看到它擅自改了什么，改完**换新对话**重来。

## 三个必须先解决的工程约束（像素风落地时的真实障碍）

1. **Cytoscape 与 ECharts 不原生支持像素风。** 前者画 Brain Forge 的神经网络，后者画 Evolution Dashboard 的 9 项指标。它们输出标准矢量 / Canvas 图表，要像素化只能靠改配置（限定色板、关闭抗锯齿、方形端点）或改用手绘 Canvas，成本不低。
2. **点阵像素字体在中文与小字号下可读性差。** `frontend/交互与可视化.md` 要求 Dashboard 有 9 项指标、Fish Card 有 13 个字段。像素字体适合英文标签，不适合承载密集数据。建议像素字体只用于导航与标签，数值一律走等宽字体。
3. **现有 token 需要整体重做。** `frontend/src/index.css` 目前是一套暗色 HSL 变量，改像素风且指明快配色，等于配色系统推倒重来，不是增量修改。

## 选定后的下一步

1. 从选定图提取色板（限定不超过 32 色）、像素刻度与边框规格，重写 `frontend/src/index.css`；
2. 把「候选色板 → 实际取色」的差异回写到 §候选色板（它是色板的定义处，须与 `index.css` 同步）；
3. 为 ECharts 补序列色板、为 Cytoscape 补网络图配色，并决定是否接受其非像素渲染；
4. 把风格词回填进 `artifacts/assets_placeholder/image_prompt_template.md` 的三类素材。

## 六处与代码对齐的校正（2026-09-26 第二次修订）

事实来源：`frontend/src/App.tsx` 与 `frontend/src/components/panel.tsx` 的**实际渲染**。
`frontend/交互与可视化.md:6-15` 的 ASCII 草图与代码有**六处**不一致：前两处此前已记，
本轮补出另外四处。**提示词一律以代码为准。**

| # | 项 | 草图 | 代码 | 本文件怎么处理 |
|---|---|---|---|---|
| 1 | 顶栏状态项 | `Env / Generation / Population / Seed`（4 项，竖线分隔） | `Env / Generation / Fish / Prey / Step / Seed`（6 项，间距分隔） | 用 6 项；`Generation` 缩写为 `Gen` 以压文字量 |
| 2 | 底栏内容 | 只有一行文字 | **两个按钮**：主按钮（`Pause` / `Release` 切换）+ `Reset` | 已按代码加按钮（文案：运行中 `Pause`、停止态 `Release`） |
| 3 | 底栏末词 | `... Playback Controls` | `... Playback`（**无 `Controls`**） | 用代码版 |
| 4 | 顶栏分隔 | 用竖线 | 用**间距**，无竖线 | 提示词不画竖线 |
| 5 | 窄屏 | 恒三栏 | `grid-cols-1`，仅 `lg` 以上才 `lg:grid-cols-3` | 只画桌面三栏（`lg` 态） |
| 6 | 面板外壳 | 共享边框的表格状三栏，栏内无图标 | 每栏是**独立圆角卡片** + 图标 + 标题栏（`rounded-lg border`，圆角 `0.625rem`） | **按 R2-4 走第三方**：去圆角、改像素斜角边框；标题栏图标保留但改像素图标 |

**另有一条方向相反的差异，必须记住**：底栏 `Evolution / Experiment / Playback` 在代码里
**只是灰色文字**（`App.tsx:64-66`），**不是按钮**。Q8(a) 决定把它们改成**真的视图 tab** ——
所以这一处是**要改代码去对齐提示词**，方向与前五处相反。**改完 `App.tsx` 才算真正对齐。**

**还有一条数据不一致**：Arena 画布底色 `#0B1220`（`DanioArenaPanel.tsx:113`），
而主题 token 的 `bg` 是 `#0B0F14`（`frontend/README.md:143`）—— **两个数不一样**。
`{画布色}` 引用的是前者；重写 `index.css` 时要把这个差对齐。
## ⚠️ 一处必须知道的口径：DNA 面板的参考图是「目标观感」，不是「要切的素材」

3D DNA 已于 2026-09-26 定为 **three.js / @react-three/fiber 程序化渲染**（见 `frontend/README.md` 技术栈），
**不是**一张贴图。所以：

- 提示词 1 / 3 里那条「立体的像素双螺旋」是**目标观感**（用于定配色、密度、层次），
  **不要**把它当成 sprite 去切图使用；
- 真正要生成给 3D 用的是**可平铺的 DNA 纹理 / 碱基符号条**（见 `asset_prompts.md` B1a / B1b），
  它们会被贴在程序化几何体上。
- 同理，中栏 Brain Forge 的神经网络也是**数据驱动渲染**（Cytoscape，库已装），
  参考图里的网络只是观感参考，不是素材。

## 待办（跨 lane 与后续）

1. **`App.tsx` 底栏三词要改成真 tab**（Q8(a)）—— `frontend/` 是我自己的 lane，可直接改；
   这是**唯一一处「改代码去对齐提示词」**（其余五处都是提示词跟随代码）。
2. **`docs/验收清单.md` 的 Demo 节若要引用视觉判据** —— `docs/` 为**只读 lane**，
   需由池伟豪补（Demo 节现 6 条无一条视觉判据；视觉判据现落在 `frontend/交互与可视化.md`）。
3. **提示词 2 的降级已在 `README.md` 写明** —— 原「待同步」待办**已闭合**。
4. **`#0B1220` 与 `#0B0F14` 的差**（见上节末）在重写 `index.css` 时一并对齐。