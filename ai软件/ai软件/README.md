# 线搭子 AI / LineUp AI

线搭子 AI 是一个基于 Streamlit 的制造业产线重配置与机械臂选型工具。它整合产线编辑、节拍与瓶颈查看、机械臂数据库筛选、AI 辅助推荐及无密钥规则兜底，适用于方案评估、演示和研究验证。

LineUp AI is a Streamlit app for production-line reconfiguration and industrial robot selection. It combines line editing, takt-time and bottleneck views, robot filtering, AI-assisted recommendations, and a no-key local fallback for evaluation, demos, and research.

## 功能概览 / Features

- **产线配置 / Production lines:** choose an industry template; add, insert, edit, or remove stations; set takt times and target capacity; import a line structure from CSV and download a template.
- **机械臂数据库 / Robot library:** use the built-in catalog or import robot data from CSV, XLSX, or XLS; review model parameters and compare candidates.
- **拓扑与节拍 / Topology and takt:** visualize the line and inspect station assignments, cycle times, and bottlenecks.
- **AI 辅助 / AI assistance:** parse a natural-language line-change request into a station, requirements, and target capacity; request a robot recommendation with an explanation.

## 三级选型 / Three-level selection

Filter robot candidates progressively:

1. **功能大类 / Functional category:** choose a process such as loading/unloading, assembly, welding, painting, or palletizing.
2. **品牌/产地 / Brand or origin:** narrow by domestic/imported origin or a specific brand.
3. **参数条件 / Technical parameters:** set minimum reach and payload, a precision limit, and whether vision support is required.

Click **筛选候选机械臂 / Filter candidates** to see matching models, review their specifications, and apply a model to the selected station. If the filters produce no matches, the app informs the user and shows a broader candidate set instead of leaving the selection empty.

After filtering, **AI 智能推荐 / AI Recommendation** selects from the candidate list and explains the choice. The AI must not introduce a model that is absent from that list. When AI is unavailable or returns an invalid model, the app uses its local weighted scoring rules.

## AI 与 BYOK / AI and BYOK

**BYOK (Bring Your Own Key)** means users provide their own provider credentials; the repository contains placeholders only, never a real key.

- For the default DeepSeek configuration, a key entered in the sidebar takes precedence over `DEEPSEEK_API_KEY` from Streamlit secrets.
- Robot recommendations call DeepSeek when a key is available. If no key is configured, or the AI service fails, a local weighted rule engine ranks the filtered candidates and provides a reason.
- Natural-language line-change parsing can be configured in the sidebar to use **DeepSeek**, an **OpenAI-compatible endpoint**, or **local Ollama**.
- Missing credentials do not prevent the app from starting. The no-key path uses local rules; it does not return a fabricated AI response.
- Do not commit `secrets.toml`, real API keys, or other credentials.

**BYOK（自带密钥）**表示由使用者提供 AI 服务凭证；仓库中只保留占位符，不包含真实密钥。

- 使用默认 DeepSeek 配置时，侧边栏手动输入的密钥优先于 Streamlit secrets 中的 `DEEPSEEK_API_KEY`。
- 配置密钥后，机械臂推荐会调用 DeepSeek；未配置密钥或 AI 服务失败时，系统使用本地加权规则对已筛选候选进行排序并说明理由。
- 自然语言产线调整解析可在侧边栏选择 **DeepSeek**、**OpenAI 兼容接口**或**本地 Ollama**。
- 缺少密钥不会阻止应用启动；无密钥时使用本地规则，不会伪造 AI 返回结果。
- 不要提交 `secrets.toml`、真实 API Key 或其他凭证。

## 本地运行 / Run locally

Requirements: Python 3.10 or later.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
streamlit run app.py
```

无需配置密钥即可启动。要启用 DeepSeek 服务，可将示例复制为本地配置并填入自己的密钥：

```powershell
Copy-Item .streamlit\secrets.toml.example .streamlit\secrets.toml
```

Then edit `.streamlit/secrets.toml`:

```toml
DEEPSEEK_API_KEY = "paste_your_own_key_here"
```

`.streamlit/secrets.toml` is for local use only. Keep it private and out of version control.

## Streamlit Cloud / 云端部署

Deploy the app with `app.py` as the entry point, install dependencies from `requirements.txt`, and add `DEEPSEEK_API_KEY` in the deployment platform's Secrets settings if you want DeepSeek recommendations. Without it, local rule-based recommendation remains available.

以 `app.py` 为入口部署，并从 `requirements.txt` 安装依赖。若要使用 DeepSeek 推荐，在部署平台的 Secrets 设置中添加 `DEEPSEEK_API_KEY`；不添加时仍可使用本地规则推荐。

## Dependencies / 依赖

- Streamlit — web UI / Web 界面
- pandas — tabular data processing / 表格数据处理
- Plotly — charts and line visualization / 图表与产线可视化
- OpenAI Python SDK — DeepSeek and OpenAI-compatible API calls / DeepSeek 与 OpenAI 兼容接口
- openpyxl, xlrd — XLSX and XLS import support / XLSX、XLS 导入支持

Install all dependencies with `pip install -r requirements.txt`.

## Project files / 项目文件

- `app.py` — Streamlit application / 主程序
- `requirements.txt` — Python dependencies / Python 依赖
- `.streamlit/secrets.toml.example` — safe credential template / 安全的密钥配置示例

## Usage note / 使用须知

Robot specifications and recommendations are decision-support information, not an engineering safety certification. Verify the actual payload, reach, cycle time, fixtures, safety requirements, and vendor specifications before deployment.

机械臂参数与推荐结果仅供方案辅助，不构成工程安全认证。实际部署前请核验负载、臂展、节拍、工装、安全要求及供应商资料。
