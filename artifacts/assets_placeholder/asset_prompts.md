# 素材提示词（一图一素材 · 逐张生成）

> 用法：**一次生成一张**。每节就是一条可粘贴的提示词，产出一个素材或一个紧密成套的小家族
> （如同一条鱼的 4 帧摆尾——同图生成才能保证风格一致）。
> 工具：ChatGPT 内置生图。风格基调：**16 位像素质感**（`ui_reference_prompts.md` 已冻结方向）。
> 书写依据：**`gpt-image-prompt` skill**（本机 `~/.claude/skills/gpt-image-prompt/SKILL.md`）。要点沿用
> `ui_reference_prompts.md` §「本次按 skill 改了什么」那一张表，此处只列与本文件相关的部分：
> 提示词用**英文**、固定**标签化结构**、**比例只用网页版认的三种**、颜色写 **hex** 不写色名、
> 首行 **AS-IS** 阻止 ChatGPT 加戏、**一条提示词 = 一次新对话**。
> 配套：`ui_reference_prompts.md`（3 张 UI 参考图 + 候选色板**唯一定义处**）、`README.md`（清单与决策记录）。

## §0 三条铁律（先读这个，不然一定白做）

**1. 一条提示词 = 一次新对话。**
skill 的 `Same-chat memory`：ChatGPT 记得同一对话里先前生成的图，**前面的元素会渗进新图**。
所以生成每一张之前**新开对话**。本文件有 15 条提示词 / 约 20 张图——同一条对话里连做两张，
第二张就会带上前一张的影子。

**2. 先锚定风格，再批量（风格锚协议）。**
**A1（成鱼）是本套素材的风格锚**。它一旦合格，之后每一条提示词都：

- **新开对话**；
- 把 **A1 那张图一起附上**；
- 在提示词**第一行**（AS-IS 行之后）加这一句：
  `Image 1 is a style reference only: copy its exact pixel size, outline weight, palette and shading technique exactly. Do NOT copy its subject.`

这是 skill 的 `style-transfer` + `Multi-image` 规则：**按序号和角色引用参考图**。
没有这一步，20 张图会长成 20 个风格。

**3. 先验证一张，再批量（抠图链路 + 色板冻结）。**
色板未冻结（见 §1）不要批量；色板冻结后**先只生成 A1 一张**，验证
「洋红底 → 抠图 → 最近邻缩小 → 贴到 `#0B1220` 上」这条链路走得通，再按 A→B→C 铺开。

## §1 每次生成前必须替换的占位

| 占位 | 填什么 |
|---|---|
| `{色板}` | **由 ChatGPT 取色**（它是视觉模型，看图判断归它；提示词见 `ui_reference_prompts.md` §步骤 2），不超过 32 色，**以提示词 3 的取色结果为准**。写法照 skill 要求：**每个颜色给「色名 + hex」**，逗号分隔，例如 `ink 1A1C2C, grass green 4C9A3F, sand warm C6854A`。色名不要单独出现（skill：色名远不如 hex 可靠） |
| `{键控色}` | 抠图用的纯色背景 `#FF00FF`（洋红）。**`{色板}` 必须不含该色**，否则抠图会挖掉素材本身 |
| `{画布色}` | Arena 画布底色 `#0B1220`，用于确认素材在深色上可辨 |

**色板未冻结前不要批量生成** —— 色板一变，全部作废。
色板的**定义处**是 `ui_reference_prompts.md` §候选色板（含 24 色起步候选 + ChatGPT 取回的最终结果）；
本文件只引用，不另立一版。

## §2 通用规格（已内嵌进每条提示词，不必重复写）

**英文骨架（skill 的固定顺序）**：`Background → Subject → Key details → Style → Composition → Lighting → Text → Constraints → Avoid`。
每条提示词都是一个 `text` 代码块，直接整块复制，不要只挑几句。

### 四条现实约束（不先知道会白做）

**1. 生图模型的「透明背景」不可信。** 它通常输出**不含 alpha** 的图片；要「透明背景」时，
经常画成**假透明棋盘格图案**——那是画上去的花纹，不是真透明。所以本文件的提示词一律要求
**纯 `{键控色}` 平涂**（并在提示词里明确 `no checkerboard pattern`），由后处理（§6）把它抠掉。
同时要求 `crisp silhouette, no halo, no glow, no color fringe`——边缘发光会让抠图留下彩色残留。

**2. 模型默认输出「伪像素」。** 它常给出**被抗锯齿柔化过的**像素风（边缘发虚、有渐变）。
后处理必须做 **最近邻（nearest-neighbor）缩小**——不能用双线性，否则等于再糊一次。
生成时给足尺寸也是为此：让模型画细节，缩小后边缘变硬。

**3. 尺寸与「各种大小的鱼」——不要按大小生成多套。**
Arena 里鱼的体型 `size` 是**连续变量**，绘图代码按它**实时缩放**
（`DanioArenaPanel.tsx` 的 `len = max(8, sr(f.size) * 10)`，`sr` 把世界单位映射到画布）。
因此**只需两套：成鱼 + 幼鱼**（幼鱼另行生成是因为小尺寸下需要更简化的形体，不是单纯缩小）。
不要生成「小/中/大/特大」四套，那既没必要也不一致。

**4. 比例只用网页版认的三种。** skill 明确 ChatGPT 网页版只认
`square 1:1` / `landscape 3:2` / `portrait 2:3`，且要在提示词**开头用文字声明**。
本文件已逐条声明：单个素材（鱼/猎物/捕食者/瓦片/纹理/logo）用 **square 1:1**；
一排多枚（水草×3、岩石×3、辉光×3、特效×3、碱基条）用 **landscape 3:2**；
PPT 封面用 **landscape 3:2 出图后裁到 16:9**（C2 有说明）。
**`1024×1024` 这类写法不要出现在提示词里**——网页版没有分辨率参数，写了是空话。

### 通用负面（每条已各自内嵌）

不要抗锯齿；不要平滑渐变；不要柔和阴影；不要玻璃拟态；不要写实三维渲染；不要文字/水印；
不要场景背景；**不要复制任何现有游戏的具体角色/道具/界面**；
**不要任何可读数值、曲线或统计图**（红线）；**不要假棋盘格图案**。

---

## §3 Arena 内素材（透明化后使用，须在 `{画布色}` 上可辨）

### A1 成鱼（斑马鱼，朝右，4 帧摆尾）—— **本清单最重要的一张 · 风格锚**
**要点**：4 帧从「横向并排」改为 **2×2 网格**——skill 明确「一图多主体难做」，并给出 3×3 表情包网格
作为可行范式；横向并排 4 帧在正方形画布里每格会被压成 1:4 的细长条，鱼根本画不下。
**本条通过后它就是 §0 铁律 2 的「风格锚」。**

```text
Use this prompt AS-IS. Do not add or embellish any details.

Square 1:1 composition.

Background: solid flat magenta #FF00FF covering the whole image, including the space between the four fish. No gradient, no texture, no checkerboard pattern, no drop shadow, no border.

Subject: one 16-bit pixel-art zebrafish seen from directly above (top-down), drawn four times in a 2x2 grid. Each copy is one frame of a swimming loop, differing ONLY in the tail's bend phase: frame 1 tail bent up, frame 2 tail centered, frame 3 tail bent down, frame 4 tail centered again. The head and body must be pixel-identical in all four frames - identical position inside its own cell, identical size, identical orientation.

Key details: long slender streamlined body; head facing right in every frame; dark body with lighter horizontal stripes; a clearly readable dorsal fin and a fan-shaped tail fin; a crisp 1-pixel dark outline around the whole silhouette.

Style: 16-bit pixel art, hand-placed square pixels, hard pixel edges, no antialiasing, no smoothing, no blending. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8, plus magenta FF00FF used only as the flat background.

Composition: the 2x2 grid is centered and evenly spaced; all four cells are the same size; the four fish never touch each other or the image edge; a clear magenta gutter separates them; the whole grid fills about 70% of the frame. Full subject visible, centered, with an even margin on all sides.

Lighting: flat and even, no light source - hand-placed highlight and shadow pixels only.

Text: none. No letters, no numbers, no watermark.

Constraints: the four frames must read as one single fish; crisp silhouette with no halo, no glow and no color fringe around the subject, so the magenta can be removed cleanly; flat 2D sprite only - do not draw a scene, water, plants, bubbles or shadows.

Avoid: antialiasing, blurred or soft edges, gradients, soft shadows, 3D rendering, photorealistic scales, water, scene background, text, numbers, watermark; do not copy any existing game's character.
```

### A2 幼鱼（更小、更简化）
**要点**：单主体、正方。**不是**把成鱼缩小，而是**减少细节**（skill：小尺寸下要能认出来）；
形体描述逐字沿用 A1 的造型词，保证是同族。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Square 1:1 composition.

Background: solid flat magenta #FF00FF covering the whole image. No gradient, no texture, no checkerboard pattern.

Subject: one 16-bit pixel-art juvenile zebrafish seen from directly above, a single static pose, head facing right.

Key details: same design language as an adult zebrafish - long slender streamlined body, dark body with lighter horizontal stripes - but clearly shorter and simpler: fewer stripes, fewer fin details, a chunkier and rounder body. The goal is a shape that is still instantly readable as a fish at a very tiny size, not a shapeless blob.

Style: 16-bit pixel art, hand-placed square pixels, hard pixel edges, no antialiasing, no smoothing. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8, plus magenta FF00FF used only as the flat background.

Composition: single subject, centered, full subject visible with an even margin on all sides; the subject fills about 65% of the frame.

Lighting: flat and even, no light source - hand-placed highlight and shadow pixels only.

Text: none.

Constraints: crisp silhouette with no halo, no glow and no color fringe around the subject, so the magenta can be removed cleanly; flat 2D sprite only.

Avoid: antialiasing, gradients, soft shadows, 3D rendering, an over-detailed realistic fish, scene background, water, text, watermark.
```

### A3 猎物（prey）
**要点**：核心竞争力是**视觉重量低于鱼**（尺寸层级），所以提示词里显式写「lightest visual weight」，
并要暖色以区别于冷色的鱼。单主体、正方。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Square 1:1 composition.

Background: solid flat magenta #FF00FF covering the whole image. No gradient, no texture, no checkerboard pattern.

Subject: one 16-bit pixel-art tiny creature seen from directly above, a single static pose, representing the small prey that the fish hunt in the arena.

Key details: small, round and plump; bright warm color, clearly warmer in hue than the cool-toned fish; a simple full silhouette with the least amount of internal detail of any object in the scene - it must be the lightest visual weight of all arena objects while still reading clearly at a very small size.

Style: 16-bit pixel art, hand-placed square pixels, hard pixel edges, no antialiasing, no smoothing. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8, plus magenta FF00FF used only as the flat background.

Composition: single subject, centered, full subject visible with an even margin on all sides.

Lighting: flat and even, no light source - hand-placed highlight and shadow pixels only.

Text: none.

Constraints: crisp silhouette with no halo, no glow and no color fringe; flat 2D sprite only.

Avoid: antialiasing, gradients, soft shadows, 3D rendering, a realistic insect specimen with legs and antennae, scene background, text, watermark.
```

### A4 捕食者
**要点**：层级靠**尺寸 + 轮廓 + 明度**三条同时拉（不只是「大一点」），并显式要求原创。
单主体、正方。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Square 1:1 composition.

Background: solid flat magenta #FF00FF covering the whole image. No gradient, no texture, no checkerboard pattern.

Subject: one 16-bit pixel-art large aquatic predator seen from directly above, a single static pose, representing the creature that threatens the fish in the arena.

Key details: its threat tier must read instantly, from three cues at once - clearly much larger than a fish, dark and low in value, and a sharp angular silhouette with pointed protrusions or a wide open jaw. It must be an original design, not resembling any existing game character.

Style: 16-bit pixel art, hand-placed square pixels, hard pixel edges, no antialiasing, no smoothing. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8, plus magenta FF00FF used only as the flat background.

Composition: single subject, centered, full subject visible with an even margin on all sides; the subject fills about 70% of the frame.

Lighting: flat and even, no light source - hand-placed highlight and shadow pixels only. Keep the overall value dark.

Text: none.

Constraints: crisp silhouette with no halo, no glow and no color fringe; flat 2D sprite only.

Avoid: antialiasing, gradients, soft shadows, 3D rendering, gore or realistic anatomy, scene background, text, watermark; do not copy any existing game's character.
```

### A5 水草（3 个变体，一张图）
**要点**：skill 的多主体范式用在这里——**一行 3 枚、等距、不重叠**，并声明 `landscape 3:2`；
3:2 的横条给每枚留出「宽 1 : 高 2」的槽位，恰好装得下细高的水草。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Landscape 3:2 composition.

Background: solid flat magenta #FF00FF covering the whole image. No gradient, no texture, no checkerboard pattern.

Subject: three different 16-bit pixel-art underwater plants seen from directly above, arranged in a single horizontal row.

Key details, three distinct kinds: 1) a short dense clump; 2) several tall thin shoots; 3) a plant with rounded leaves. Use grass green as the base with a darker green outline and one lighter green for the lit edge. All three stand on a common baseline, evenly spaced, clearly different in height and silhouette, and never overlapping each other.

Style: 16-bit pixel art, hand-placed square pixels, hard pixel edges, no antialiasing, no smoothing. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8, plus magenta FF00FF used only as the flat background.

Composition: the row is centered, each plant roughly twice as tall as it is wide, a clear magenta gutter between them, none touching the image edge; full subjects visible with an even margin on all sides.

Lighting: flat and even, no light source - hand-placed highlight and shadow pixels only.

Text: none.

Constraints: crisp silhouettes with no halo, no glow and no color fringe, so each can be cut out separately; flat 2D sprites only.

Avoid: antialiasing, gradients, soft shadows, 3D rendering, photorealistic plant photography, water, ripples, scene background, text, watermark.
```

### A6 岩石与沉木（3 个变体，一张图）
**要点**：与 A5 同范式（一行 3 枚、`landscape 3:2`）。三者的**受光方向必须一致**，
否则贴进同一场景会像来自三个光源。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Landscape 3:2 composition.

Background: solid flat magenta #FF00FF covering the whole image. No gradient, no texture, no checkerboard pattern.

Subject: three different 16-bit pixel-art underwater obstacles seen from directly above, arranged in a single horizontal row.

Key details, three distinct kinds: 1) a single angular rock; 2) a small pile of two or three broken stones; 3) a piece of sunken driftwood with lengthwise grain, slightly tapered at both ends. All three use stone grey and wood brown with darker outlines. Every one of them must be lit from the same direction - the highlight pixels on the top-left of each edge, the shadow pixels on the bottom-right - so they look like they belong to one scene. Slightly larger than a fish, evenly spaced, never overlapping.

Style: 16-bit pixel art, hand-placed square pixels, hard pixel edges, no antialiasing, no smoothing. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8, plus magenta FF00FF used only as the flat background.

Composition: the row is centered, a clear magenta gutter between items, none touching the image edge; full subjects visible with an even margin on all sides.

Lighting: flat and even, no light source - hand-placed highlight and shadow pixels only, consistent across all three.

Text: none.

Constraints: crisp silhouettes with no halo, no glow and no color fringe; flat 2D sprites only.

Avoid: antialiasing, gradients, soft shadows, 3D rendering, photorealistic rock photography, moss buildup, scene background, text, watermark.
```

### A7 水底瓦片（可无缝拼接）
**要点**：**四张各生成一次**——浅水面 / 深水面 / 草地 / 沙地。
无缝拼接是本条唯一的技术难点，所以提示词里把「左边缘接右边缘、上边缘接下边缘」写成可见的事实，
并要求**均匀无焦点**（有中心构图就一定接不上）。正方；瓦片**不抠图**，所以**没有**键控色。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Square 1:1 composition.

Background: the tile itself fills the entire image edge to edge. Do NOT add a magenta border or any frame - this asset is not cut out.

Subject: one seamless tileable 16-bit pixel-art ground texture seen from directly above: {瓦片类型}.

Key details: for shallow water, blue-green pixel blocks with dithered ripples; for deep water, the same family but clearly darker; for grass, green pixel blocks with a few lighter and darker speckles; for sand, warm yellow pixel blocks with fine grain.

Style: 16-bit pixel art, hand-placed square pixels, hard pixel edges, no antialiasing, no smoothing. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8. Use dithering patterns for all grain and transition.

Composition: evenly distributed with NO focal point and no centre composition. The left edge must match the right edge and the top edge must match the bottom edge, so that tiling this image against itself produces no seam, no break and no visible repetition boundary.

Lighting: flat and even, no light source.

Text: none.

Constraints: this is a texture, not a picture - no object may be recognisable as a thing.

Avoid: antialiasing, gradients, soft shadows, photorealistic material, any outline or border, any decorative object, text, watermark.
```

**四种取值（各生成一次，其余文字完全不动）**：
`浅水面` / `深水面` / `草地` / `沙地`。

### A8 海洋背景（低对比、可平铺）
**要点**：它的功能是**长时间铺底不抢主体**，所以提示词把「低对比、低信息量」写在 Subject 里而不是
Constraints 里（skill：最重要的放最前）。向 `{画布色}` 收暗，与 Arena 面板的暗调一致。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Square 1:1 composition.

Background: the background itself fills the entire image edge to edge, as a seamless tileable texture. Do NOT add a magenta border or any frame - this asset is not cut out.

Subject: a low-contrast, low-information 16-bit pixel-art underwater backdrop seen from directly above, to be tiled behind the whole arena. It must stay quiet for a long time on screen without competing with the moving subjects.

Key details: a deep blue-green base that darkens toward 0B1220, with sparse dithering and pixel speckles suggesting depth and fine suspended particles. Gentle, evenly spread value changes only. No recognisable object of any kind.

Style: 16-bit pixel art, hand-placed square pixels, hard pixel edges, no antialiasing, no smoothing. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8, with the main mass in the deep blue-green range and the darkest areas approaching 0B1220.

Composition: no focal point; the left edge must match the right edge and the top edge must match the bottom edge, so tiling produces no seam.

Lighting: flat and even, dim overall, no light source, no bright shafts.

Text: none.

Constraints: low contrast by design - this is a floor, not a picture.

Avoid: antialiasing, smooth gradients, soft shadows, high-contrast noise, light shafts or bands, any creature or prop, photorealistic water photography, text, watermark.
```

---

## §4 面板视觉

### B1a DNA 纹理（给 three.js 用，**不是**螺旋成品图）
**要点**：原 B1 把「纹理」和「碱基条」塞进一张图，违反 skill 的「一图多主体难做」——**已拆成 B1a / B1b**。
B1a **故意不含可读字母**：碱基做成**抽象符号块**，这样把「图内文字」这个最易失败的点从纹理上彻底移走。
它是**可平铺纹理**，会被贴在程序化几何体上，不是一张螺旋成品图。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Square 1:1 composition.

Background: the texture itself fills the entire image edge to edge. Do NOT add a magenta border or any frame - this asset is not cut out.

Subject: one seamless tileable 16-bit pixel-art texture of DNA base pairs, evenly distributed across the whole image, for wrapping onto procedural 3D geometry. It is a material texture, NOT a picture of a double helix.

Key details: interlocking abstract base-pair glyph blocks in four clearly distinguishable colors, joined by thin sugar-phosphate backbone links, interleaved to cover the entire surface at uniform density. The glyphs are abstract geometric marks only - they must NOT be readable letters, digits or any alphabet. No centre, no focal point, no gradient across the image.

Style: 16-bit pixel art, hand-placed square pixels, hard pixel edges, no antialiasing, no smoothing. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8. Use dithering for all transitions.

Composition: uniform density everywhere; the left edge must match the right edge and the top edge must match the bottom edge, so tiling this texture in any direction produces no seam and no obvious repetition.

Lighting: flat and even, no light source, no shading gradient across the image.

Text: none. No readable letters, no digits, no labels - only abstract glyph marks.

Constraints: this is a wrapping texture, so it must tile seamlessly and must have no single dominant feature.

Avoid: antialiasing, gradients, soft shadows, 3D rendering, a finished double-helix illustration, any readable letter or number, any label or caption, scene background, watermark.
```

### B1b 碱基符号条（2D 编辑条用，**这是唯一允许出现字母的一张**）
**要点**：**全文件唯一故意出文字的一张**，所以按 skill 把文字规则写足：加引号、全大写、逐字母、
要求 verbatim、不要多余字符、并给「渲不清就用色块占位」的回退——宁可占位，不要乱码。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Landscape 3:2 composition.

Background: solid flat magenta #FF00FF covering the whole image. No gradient, no texture, no checkerboard pattern.

Subject: one horizontal strip of 16-bit pixel-art base letters for a sequence editor, arranged in a single row in the centre of the frame.

Key details: exactly four characters in the row, in this order: "A", "C", "G", "T". Each character sits on its own small pixel cell with a clear empty gutter between cells. Each base has its own clearly distinct color so they are never confused. A dot-matrix pixel font, bold and chunky, large enough to read at a glance.

Style: 16-bit pixel art, hand-placed square pixels, hard pixel edges, no antialiasing, no smoothing. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8, plus magenta FF00FF used only as the flat background.

Composition: the row is centred horizontally, occupying a narrow horizontal band with generous empty magenta above and below; the whole strip fills about 70% of the frame width. Full subject visible with an even margin on all sides.

Lighting: flat and even, no light source.

Text: render the four letters "A" "C" "G" "T" verbatim, each one exactly once, in that order, correct and complete, in a dot-matrix pixel font, with NO extra characters, no extra letters, no numbers, no captions, no watermark. If a letter cannot be rendered legibly, replace that letter with a clean uniform pixel block of the same size - never render a garbled, duplicated or blurry character.

Constraints: only these four characters may appear anywhere in the image; crisp edges with no halo, no glow and no color fringe, so the magenta can be removed cleanly.

Avoid: antialiasing, gradients, soft shadows, 3D rendering, any letter other than A C G T, any word, any number, any caption, scene background, watermark.
```

### B2 细胞类型图标（6 枚，**3×2 网格一张图**）
**要点**：原为「6 枚，一次一张」（6 张图）。skill 的 Q版表情包范式正是
`3x3 grid of 9 expressions ... uniform style ... prefer NO text`——同族小图标本就该**一张网格图**出，
既省 5 张图，又保证 6 枚同风格。**已改为一张 3×2 网格**（6 枚正好 3 列 × 2 行）。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Square 1:1 composition.

Background: solid flat magenta #FF00FF covering the whole image, including the space between icons. No gradient, no texture, no checkerboard pattern.

Subject: six 16-bit pixel-art cell-type icons for a neural development diagram, laid out in a neat grid of three columns and two rows.

Key details: the six shapes are, in reading order: a circle with a nucleus, a square with cut corners, a diamond, a star, a ring, a teardrop. Every icon uses a 1-to-2-pixel dark outline around a fill of one or two flat colours, and every icon is a different shape - they must never be distinguishable by colour alone. All six use the same outline weight, the same optical size and the same level of internal detail, so they read as one icon set. Geometric and simple, still instantly recognisable when shrunk to 16-24 pixels.

Style: 16-bit pixel art, hand-placed square pixels, hard pixel edges, no antialiasing, no smoothing. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8, plus magenta FF00FF used only as the flat background.

Composition: a regular 3-by-2 grid, evenly spaced, equal cell size, a clear magenta gutter between icons, none touching the image edge; full set visible with an even margin on all sides.

Lighting: flat and even, no light source - hand-placed highlight and shadow pixels only.

Text: none. No letters, no numbers, no labels.

Constraints: crisp silhouettes with no halo, no glow and no color fringe, so each icon can be cut out separately; six icons only, all identical in weight.

Avoid: antialiasing, gradients, soft shadows, realistic biological drawing or microscope slides, text, numbers, watermark, scene background.
```

### B3 神经辉光（三类，**一行三枚 · 一张图**）
**要点**：原为「一次一张」（3 张）。三类辉光同族，改**一行 3 枚**（skill 的多主体范式），省 2 张图。
关键约束不变：**衰减必须靠抖动点阵**，不能用平滑径向渐变——否则它和项目里其它像素元素不在一个体系。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Landscape 3:2 composition.

Background: solid flat magenta #FF00FF covering the whole image. No gradient, no texture, no checkerboard pattern.

Subject: three 16-bit pixel-art neural-activity glow elements in a single horizontal row, evenly spaced.

Key details, three distinct kinds: 1) a node activation - one bright core with a square halo whose brightness falls off outward; 2) an edge pulse - a short string of bright dots running along one axis, as if travelling along a connection; 3) a synapse hit flash - a short four-point star burst. All brightness falloff must be built from dithering patterns and stepped pixel values, never from a smooth radial gradient. Each element has a single brightest core.

Style: 16-bit pixel art, hand-placed square pixels, hard pixel edges, no antialiasing, no smoothing. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8, plus magenta FF00FF used only as the flat background, with the glow built from the brightest entries.

Composition: the three elements are centred in a row with a clear magenta gutter between them, none touching the image edge; full subjects visible with an even margin on all sides.

Lighting: these elements are the light source - bright enough to read clearly when composited over a dark neural network diagram, but never blown out to flat pure white.

Text: none.

Constraints: crisp silhouettes with no halo bleed into the background, no glow and no color fringe, so each can be cut out separately; the elements will be overlaid on a dark background, so they must be bright but not over-exposed.

Avoid: antialiasing, smooth radial gradients, soft blur, lens flare, bloom, text, scene background, watermark.
```

### B4 UI 状态特效（三组，**一次一组**）
**要点**：三组各生成一次（危险 / 饥饿 / 变异），每组一图内含**三档强度**。
最重要的功能约束是「**中央必须通透**」——它是叠加在边框上的警示层，不是整屏遮罩；
所以这条写在 Constraints 里并重复一次。三组主色必须互不混淆。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Landscape 3:2 composition.

Background: solid flat magenta #FF00FF covering the whole image. No gradient, no texture, no checkerboard pattern.

Subject: one set of 16-bit pixel-art UI status effects: {组别：危险 / 饥饿 / 变异}. Show three intensity levels side by side in a single row, from faintest on the left to strongest on the right.

Key details: danger uses red warning chevrons and sharp spikes closing inward from the edges; hunger uses warm yellow-to-orange pulsing rings; mutation uses violet spiral fragments and shattered pixel specks. Across the three levels the elements become denser, thicker and brighter, in that order. The three levels are clearly different in strength but obviously the same effect.

Style: 16-bit pixel art, hand-placed square pixels, hard pixel edges, no antialiasing, no smoothing. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8, plus magenta FF00FF used only as the flat background.

Composition: the three levels are evenly spaced in one row; within each level the elements cluster near the outer edge of that cell, leaving the centre clear.

Lighting: these are emissive warning effects - flat, bright, no light source.

Text: none. No letters, no numbers.

Constraints: this overlays as a border warning layer, so the elements must stay near an outer frame with the centre left transparent - never fill the frame with solid color blocks. The three groups must use clearly different dominant hues so they are never confused with each other.

Avoid: antialiasing, gradients, soft glow, text or numbers, a solid full-screen color block, watermark; do not copy any existing game's HUD.
```

---

## §5 品牌与演示

### C1 logo（只用图形，不含文字）
**要点**：skill 的 `logo-brand` 类目要求 `strong silhouette, balanced negative space`——
补进提示词；并给出**最小可用尺寸判据**（缩到 32 px 仍可辨），否则像素 logo 很容易做成一团噪点。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Square 1:1 composition.

Background: solid flat magenta #FF00FF covering the whole image. No gradient, no texture, no checkerboard pattern.

Subject: the EvoGenesis brand mark - a square icon containing NO text of any kind.

Key details: a simplified zebrafish silhouette and a segment of DNA double helix interlocking into a single ring, each motif taking about half of the shape. Built from flat high-saturation color blocks with a strong outer silhouette and well-balanced negative space, geometric and clean, with no volumetric lighting and no fine detail. It must still be recognisable when shrunk to 32 pixels.

Style: 16-bit pixel art for the interior detail, but with a poster-like flat vector clarity in the overall silhouette. Hard pixel edges, no antialiasing. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8, plus magenta FF00FF used only as the flat background.

Composition: a square composition, the mark centred, occupying about 70% of the frame, full subject visible with an even margin on all sides.

Lighting: flat, no light source, no soft shading.

Text: none. No letters, no wordmark, no initials - the wordmark is set separately in a real font later.

Constraints: crisp silhouette with no halo, no glow and no color fringe, so the magenta can be removed cleanly.

Avoid: antialiasing, gradients, soft shadows, 3D rendering, any letter or word, ornamental flourishes, watermark; do not copy any existing brand or game logo.
```

### C2 PPT 封面视觉
**要点**：**比例是本条最大的坑**——skill 明确网页版不认 16:9，所以提示词声明 `landscape 3:2`，
出图后在 §6 裁到 16:9（裁掉高度约 15.6%）。**因此提示词里刻意要求四周留边距**。
红线照旧：**不出现任何数值、坐标轴、曲线或统计图**。

```text
Use this prompt AS-IS. Do not add or embellish any details.

Landscape 3:2 composition.

Background: the composition itself fills the frame - a split scene where the left part is a bright pixel-art environment and the right part is a clean light panel surface, joined by a soft transition band.

Subject: an academic presentation cover visual for the EvoGenesis project. The left two thirds is a top-down 16-bit pixel-art pool arena: water, grass and stone pixel tiles, slender pixel zebrafish, much smaller prey dots, and one larger predator silhouette. The right third is a precisely drawn DNA double helix together with a neuron network diagram of nodes and thin clean lines, in a crisp vector-like rendering.

Style: the pixel region keeps 16-bit hard edges and dithering; the precise region keeps clean vector sharpness; both regions share one bright palette and must not look pasted together. Limited palette, use only these hex colors: ink 1A1C2C, slate shadow 333C57, blue grey 566C86, deep water 1E6F9F, mid water 2E9BC7, shallow water 6FD3E8, foam B6F0F5, deep grass 2F6B3A, grass green 4C9A3F, light grass 8ED14B, bark dark 5A3A22, wood brown 8A5A33, sand warm C6854A, sand light E8C179, amber F2A93B, coral orange F08A5D, danger red E4595C, mutation violet 9B5DE5, white FFFFFF, bone D9E0E8, stone grey 7A8A99, stone shadow 4A4A5A, fish navy 2B3A67, fish blue 5C7CB8.

Composition: the two regions meet along a soft gradient band about one fifth of the width; the whole image is evenly weighted with generous empty margin on all four sides so it can be cropped later; bright, saturated and clearly layered so it reads well when projected large.

Lighting: bright and even overall, no dark heavy mood.

Text: none. No title, no caption - the title is set later in a real font.

Constraints: no readable data of any kind may appear.

Avoid: antialiased fake-pixel edges, a dark oppressive palette, glassmorphism, 3D photorealistic materials, any number, axis, chart or data visualization, watermark; do not copy any existing game's characters or interface.
```

---

## §6 后处理与落地（生成之后）

**为什么必须后处理**：模型给的是大图 + 伪像素边缘 + 键控色底，**不能直接喂给 Canvas**。
建议流水线（**可按此写成脚本，我可以做**）：

1. **抠图**：按 `{键控色}` 去背景（洋红 `#FF00FF` 与调色板不重叠，因此可无损扣）。
   注意：**要按「与洋红的色彩距离」做阈值**，不要按「非白即透明」，否则会误伤浅色高光。
2. **切分**：多枚/多帧的图**优先按网格等分**切开（提示词已要求等距网格：A1 是 2×2、A5/A6/B3/B4 是一行 3 枚、
   B2 是 3×2），切完再把每一格 `trim` 到内容边框。**不要**用连通域切分——相邻两格的像素可能连在一起。
3. **裁到 16:9（仅 C2 与三张 UI 参考图）**：3:2 出图 → 16:9 需**裁掉高度约 15.6%（上下各约 7.8%）**，宽度不变。
4. **最近邻缩小**：用 `nearest` 缩放到目标尺寸（**禁止双线性**，否则再度糊化）。
5. **调色板量化**：把颜色吸附到冻结的不超过 32 色，消除模型带进来的杂色。
6. **落位**：写入 `frontend/public/assets/`。

**目标尺寸（@2x，运行时按 `size` 再缩放）**

| 素材 | @2x 目标 | 仓内路径 |
|---|---|---|
| 成鱼 4 帧（A1 网格切出） | 64×64 每帧 | `frontend/public/assets/arena/fish_adult_f1..4.png` |
| 幼鱼（A2） | 32×32 | `frontend/public/assets/arena/fish_juvenile.png` |
| 猎物（A3） | 16×16 | `frontend/public/assets/arena/prey.png` |
| 捕食者（A4） | 96×96 | `frontend/public/assets/arena/predator.png` |
| 水草 / 岩石 / 沉木（A5 / A6） | 各 64×64 | `frontend/public/assets/arena/prop_*.png` |
| 地表瓦片（A7 ×4） | 各 64×64 | `frontend/public/assets/arena/tile_*.png` |
| 海洋背景（A8） | 512×512 | `frontend/public/assets/arena/bg_ocean.png` |
| DNA 纹理 / 碱基条（B1a / B1b） | 512×512 / 512×64 | `frontend/public/assets/panels/dna_*.png` |
| 细胞图标（B2 网格切出） | 32×32 每枚 | `frontend/public/assets/ui/cell_*.png` |
| 辉光（B3） | 64×64 每枚 | `frontend/public/assets/ui/glow_*.png` |
| UI 特效（B4） | 128×128 每档 | `frontend/public/assets/ui/fx_*.png` |
| logo（C1） | 512×512 | `frontend/public/assets/brand/logo.png` |

`frontend/public/` 的内容会**原样**进入构建产物、不经哈希改名，因此适合被 Canvas 用 URL 加载；
也符合仓库约定「**不引 CDN，素材全部本地打包**」（`frontend/README.md` 防坑约定 2）。

## §7 每张生成后的自检

- [ ] **比例对**：单素材是 square 1:1；一行多枚是 landscape 3:2（不是 16:9——网页版不认）
- [ ] 像素是**方形硬边**（不是被抗锯齿柔化的伪像素）
- [ ] 背景是**纯 `{键控色}`**（不是棋盘格图案、不是渐变、不是白色）
- [ ] 色板落在 `{色板}` 内，**且不含 `{键控色}`**
- [ ] 边缘**没有光晕/彩色描边残留**（`no halo / no fringe`，否则抠图会留彩色边）
- [ ] 素材居中、留边距（便于裁切与缩放）
- [ ] 多枚/多帧的那几张：**尺寸与风格完全统一**、互不重叠、等距
- [ ] 瓦片/背景/纹理类：**真的能无缝平铺**（左右上下边缘相接无断层）
- [ ] 在 `{画布色}` 上仍然可辨（Arena 素材）
- [ ] **没有**任何可读数值、曲线、统计图（**红线**）
- [ ] **没有**与任何现有游戏资产雷同（**红线**）

## §8 出问题时怎么改（症状 → 修正）

skill 的 `Failure-mode troubleshooting`，按本项目（像素 + 抠图）的实际症状改写。
**每次只改一处**，改完**新开对话**重生成（多轮迭代会漂移）。

| 你会看到 | 往提示词里加 / 改什么 |
|---|---|
| 边缘发虚、像被磨过的假像素 | 强化 `hard-edged square pixels, no antialiasing, no blur, no smoothing`；并加 `draw on a coarse pixel grid` |
| 背景不是纯洋红（出现棋盘格 / 渐变 / 白底） | 改成 `solid flat magenta #FF00FF, no checkerboard pattern, no gradient, no white background` |
| 主体被裁切 | 加 `Full subject visible, centered, with an even margin on all sides.` |
| 多出不要的元素（水波、气泡、影子、额外道具） | 加 `The image contains only: (逐条列举). No extra elements, no added text, no watermark.` |
| 颜色跑出调色板 | 把 `{色板}` 写成**每个颜色「色名 + hex」**，并加 `do not introduce any color outside this list` |
| 四帧 / 多枚的风格或尺寸不一致 | 把**固定描述块**逐字重复（skill：系列不一致 → 定义固定块，每张一字不改）；或在**同一对话内**迭代以利用其记忆 |
| 瓦片 / 背景拼接有缝 | 加 `seamless tileable: the left edge must match the right edge and the top edge must match the bottom edge` |
| 纹理出现中心焦点 | 加 `no centre, no focal point, uniform density everywhere` |
| 文字乱码 / 少字 / 多字 | 文字加引号、全大写、要求 `verbatim, no extra characters`、字数压到最少；**或放弃图内文字**，后期用真实字体叠 |
| 改了三次越改越歪 | skill：多轮迭代会漂移 → 把最终要求**汇总成一份完整 prompt，新开对话**重生成 |
| 被拒绝生成 | 去掉任何真实作品/品牌指涉，改中性描述 |
| 想确认模型实际收到了什么 | skill 的调试法：问它 `show the exact prompt you used for the last image` |

## §9 清单自查：本文件覆盖了 README 的 10 项

| README 清单项 | 对应本节 | 出图数 |
|---|---|---|
| EvoGenesis logo | C1 | 1 |
| zebrafish swim sprites | A1（摆尾 4 帧）、A2（幼鱼） | 2 |
| prey / predator | A3、A4 | 2 |
| obstacles / plants / rocks | A5（水草）、A6（岩石/沉木） | 2 |
| water background | A8（海洋背景）、A7（地表瓦片） | 5 |
| DNA texture | B1a（纹理）、B1b（碱基条） | 2 |
| cell-type icons | B2（3×2 网格一张） | 1 |
| neural glow | B3（一行 3 枚一张） | 1 |
| danger/hunger/mutation UI effect | B4（一组一张） | 3 |
| PPT cover visual | C2 | 1 |

**合计 15 条提示词 / 20 张图**（原先 14 条 / 26 张——省在「同族合成网格」与「B1 拆分」：
网格化省 7 张，B1 拆分多 1 张）。

**未列入**：无。README 的 10 项全部有对应提示词；另按实际需要补了 A7 地表瓦片
（README 只笼统写 obstacles/plants/rocks，未含地表）。

## §10 一处需要同步的定位问题

`ui_reference_prompts.md` 的**提示词 2（sprite sheet）**已被 skill 判为
「违反一图多主体限制、不适合作为最终切图来源」，只保留作**风格对照图**。
`README.md` 的文件索引里若仍把它写作素材来源，需要同步更正——本文件的 A/B/C 才是素材来源。
