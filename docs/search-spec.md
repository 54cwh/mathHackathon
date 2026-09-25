# 子代理搜索资料规范

## 基本原则

- 每个子代理搜索任务必须有明确的输出文件路径和格式
- 搜索结果必须持久化到文件系统，不依赖对话上下文

## 任务下发模板

下发子代理任务时，必须明确以下要素：

1. **搜索目标**：要搜索什么，解决什么问题
2. **输出文件路径**：保存到 `./research/reference/` 下，文件名要有意义
3. **输出格式**：必须使用 JSON 格式，需要定义清晰的 JSON Schema
4. **字段定义**：每个字段要标注 `required`（必须返回）或 `optional`（如无法找到可留空）
5. **数据来源**：每个数据点必须附带来源 URL 或出处
6. **缺失处理**：某个字段找不到时的处理方式（标注 `null` / 留空 / 提供近似值并说明）
7. **质量要求**：数据需要核实交叉验证；优先采用权威来源（论文出版方、项目官方仓库、官方统计）

## JSON 输出模板示例

```json
{
  "meta": {
    "search_time": "YYYY-MM-DD",
    "topic": "<检索主题>",
    "scope": "<检索范围与约束>",
    "sources_summary": "<使用的来源概述>"
  },
  "items": [
    {
      "name": "<名称或标题>",
      "type": "paper | repo | dataset | other",
      "url": "<主链接>",
      "source": "<来源：arXiv / GitHub / OpenAlex / 官网...>",
      "source_url": "<来源页链接>",
      "date": "<发布日期或最近更新>",
      "metrics": "<star / 引用数等，找不到置 null>",
      "license": "<许可证>",
      "summary": "<一句话作用>",
      "relevance": 3,
      "notes": "<备注；required 字段缺失时说明原因>"
    }
  ],
  "conclusions": ["<推荐直接用 / 仅作参考 / 不建议 三级结论与下一步>"]
}
```

> 模板里的 `<...>` 是占位符，使用时替换为实际值；`relevance` 填 number。模板本身是合法 JSON，可直接校验。

## 字段标注示例

在下发任务时用 markdown 表格说明字段要求：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| name | string | required | 名称或标题 |
| type | string | required | paper / repo / dataset / other |
| url | string | required | 主链接 |
| source | string | required | 来源（arXiv / GitHub / OpenAlex / 官网） |
| source_url | string | required | 来源页链接 |
| summary | string | required | 一句话作用 |
| date | string | optional | 发布日期或最近更新 |
| metrics | string | optional | star / 引用数等 |
| license | string | optional | 许可证 |
| relevance | number | optional | 适配度 1-5 |
| notes | string | optional | 备注/异常说明 |

## 缺失数据处理

- 无法找到的数据：值设为 `null`，在 `notes` 中注明原因（如“该信息未公开 / 来源无此字段”）
- 近似数据：提供近似值并在 `notes` 中注明偏差（如“口径不同，与标准定义差 X%”）

## 重复搜索规则

- 搜索前先检查 `./research/reference/` 下是否有同类文件
- 若已有同类文件，优先更新而非新增
- 每次搜索完成后在文件头部追加搜索时间标记
