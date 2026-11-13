# 线搭子 AI · 产线方案重配置搭子 (中文说明)

## 项目简介

线搭子 AI 是面向制造业方案评估与演示的产线重配置和工业机械臂选型工具。用户可以编辑产线工位、查看节拍与瓶颈，并根据机械臂参数筛选和比较候选型号。

## 核心功能

- **产线配置与可视化：**选择行业预设或自定义模板，新增、插入、编辑和删除工位，查看产线拓扑、工位节拍、瓶颈及估算产能。
- **优化前后价值对比：**采用或推荐新机型后，以分组柱状图对比初始与当前节拍，并展示瓶颈变化及 24 小时理论产能差值；产线结构变化时自动建立新的比较基线。
- **全线语义优化：**AI 或本地规则识别全局提速、降速、提质、降本等请求；每次切换指令都会先恢复产线初始快照再执行，避免参数叠加。相同指令不会重复执行，点击“重置产线”可恢复初始状态并清除指令记录。
- **成本与占地多目标推荐：**按精度、节拍、成本和估算占地的自定义权重排序，支持一键替换，并查看各工位成本/占地分析图。
- **紧凑操作区：**收起低频的产线编辑和手动换型控件；四项推荐权重均可在 1～10 范围内调整。
- **三级联动筛选：**依次按工序类型、品牌或产地、工作半径与负载等参数筛选机械臂，并可要求具备视觉功能。
- **人工智能智能推荐：**结合应用场景和筛选条件，从候选机械臂中给出推荐及理由；推荐结果限制在当前候选范围内。
- **复杂数据清洗与单位保留：**支持导入逗号分隔值文件和电子表格，清理列名中的空格、换行和隐藏字符，对齐常见字段名称，提取精度数值，同时保留原始型号文字及参数单位信息；缺少运行速度单位字段时提供安全默认值。
- **严格的数据校验机制：**校验必需工位、型号和有效节拍；为可选缺失字段提供安全默认值，并在导入失败时给出提示。
- **数据展示与产线导入：**查看当前机械臂数据库，导入产线结构文件，并下载产线模板。

## 自带密钥与规则兜底机制

使用者可自行提供深度求索服务密钥，也可配置兼容接口或本地模型服务。未配置密钥时，应用仍可运行；机械臂推荐将使用本地规则评分。人工智能服务不可用时，系统也会回退到本地规则，不会伪造服务结果。

真实密钥仅用于本地配置或部署平台的密钥设置。不要提交真实密钥，也不要将本地密钥文件上传到代码仓库。

## 本地运行指南

需要 Python 3.10 或更高版本。在 Windows PowerShell 中执行：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

无需配置密钥即可启动。若要启用深度求索服务，将 `.streamlit\secrets.toml.example` 复制为 `.streamlit\secrets.toml`，再填入自己的密钥：

```toml
DEEPSEEK_API_KEY = "your_key_here"
```

不要提交 `.streamlit\secrets.toml` 或任何真实凭证。

---

# LineMate AI (English Description)

## Project Overview

LineMate AI is a production-line reconfiguration and industrial robot selection tool for manufacturing planning and demonstrations. Users can edit stations, inspect takt times and bottlenecks, and filter or compare robot candidates by their specifications.

## Core Features

- **Production-line configuration and visualization:** Select a built-in or custom template, add, insert, edit, or remove stations, and review the line topology, station takt times, bottlenecks, and estimated capacity.
- **Before-and-after value comparison:** After adopting a model, compare initial and current takt times in a grouped bar chart and review bottleneck changes and the estimated 24-hour capacity difference. Structural changes establish a new comparison baseline.
- **Whole-line semantic speed-up:** AI or local rules recognize requests such as speeding up the whole line; after confirmation, reduce every station's takt time by 20% and refresh bottleneck and capacity estimates.
- **Cost-and-footprint multi-objective recommendation:** Rank models using custom weights for precision, takt, cost, and estimated footprint; support one-click replacement and per-station analysis charts.
- **Compact controls:** Collapse infrequent line editing and manual replacement controls; adjust each recommendation weight from 1 to 10.
- **Three-level linked filtering:** Narrow robot candidates by process type, brand or origin, and technical parameters such as reach and payload; optionally require vision support.
- **AI-powered recommendations:** Generate a recommendation and rationale based on the scenario and filters. Recommendations are constrained to the current candidate set.
- **Complex data cleaning with units preserved:** Import CSV and spreadsheet files, clean whitespace and hidden characters in column headers, align common field names, extract precision values, and preserve original model text and parameter-unit information; provide a safe default when a speed-unit field is missing.
- **Strict data validation:** Validate required station and model fields and positive takt times. Apply safe defaults to optional missing fields and report import errors.
- **Data inspection and line import:** View the active robot database, import a production-line structure, and download a line template.

## BYOK & Fallback Mechanism

Users may provide their own DeepSeek API key, configure an OpenAI-compatible endpoint, or use a local model service. The app runs without credentials; robot recommendations then use local rule-based scoring. If an AI service is unavailable, the app falls back to local rules rather than fabricating a response.

Keep real credentials in local configuration or the deployment platform's secret settings. Never commit real keys or upload local secret files to the repository.

## Local Setup Guide

Python 3.10 or later is required. Run these commands in Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

The app starts without an API key. To enable DeepSeek, copy `.streamlit\secrets.toml.example` to `.streamlit\secrets.toml` and enter your own key:

```toml
DEEPSEEK_API_KEY = "your_key_here"
```

Do not commit `.streamlit\secrets.toml` or any real credentials.
