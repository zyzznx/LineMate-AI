# 线搭子 AI / LineUp AI

LineUp AI（线搭子 AI）是一个面向制造业产线重配置的 Streamlit 应用，帮助用户在产线结构变更、机型替换、节拍评估和 AI 解析场景中快速完成决策。该项目支持行业模板、CSV 导入、工位编辑、机械臂筛选和产线拓扑可视化，适合用于生产线重构方案评估与演示。

## Project Overview / 项目简介

This project helps manufacturers and production planners redesign and optimize production lines by:

- managing workflow stations and takt times
- replacing robot arm models by station
- evaluating bottleneck lines and cycle-time balance
- importing line structure data from CSV
- using AI-assisted analysis when an API key is available
- falling back to a local rule engine when no key is configured

本项目主要帮助制造业生产规划人员和方案设计人员完成：

- 产线工位结构管理
- 节拍与瓶颈分析
- 机械臂机型筛选与替换
- CSV 导入与模板导出
- AI 辅助方案分析
- 无密钥环境下的稳定规则兜底

## Core Features / 核心功能

### 1. Production line configuration / 产线配置
- Industry template switching / 行业模板切换
- Add / remove / insert workstations / 工位增删改
- Import existing line structure CSV / 导入现有产线结构 CSV
- Update station takt and model dynamically / 动态更新工位节拍与机型

### 2. Robot arm selection and replacement / 机械臂筛选与更换
- Filter candidates by station / 按工位筛选候选机械臂
- Support domestic / imported filters / 支持国产/进口筛选
- Filter by precision, price, maintenance response, and takt / 支持精度、价格、维保响应、节拍筛选
- Click on a topology node and directly replace the robot arm / 点击拓扑图节点即可更换机械臂

### 3. AI parsing / AI 解析
- Natural-language request parsing / 自然语言产线调整解析
- Extract target station, requirements, and target capacity / 自动提取工位、要求和目标产能
- Use OpenAI-compatible or DeepSeek API when credentials are available / 有密钥时可调取 AI 模型

### 4. Rule fallback mode / 规则兜底模式
- If no API key is configured, the app automatically uses a local rules engine / 未配置 API Key 时，自动启用本地规则引擎
- Keeps the app running without crashing in demo or deployment scenarios / 适用于演示、评审、离线或无密钥场景

## Security and fallback mechanism / 安全机制与兜底机制

This application follows a BYOK (Bring Your Own Key) design:

- Users can manually enter a DeepSeek API key in the sidebar
- If manual input is empty, the app checks Streamlit secrets
- If neither is available, the app does not crash
- It automatically switches to the built-in rule-based engine

本项目采用 BYOK（Bring Your Own Key，自带密钥）机制：

1. 用户可在侧边栏手动输入 DeepSeek API Key
2. 若未手动填写，则尝试读取本地 Streamlit secrets
3. 若两者都没有配置，程序不会崩溃
4. 系统自动切换到本地规则引擎进行解析
5. 不写死真实密钥，不将真实密钥提交到公开代码仓库

This ensures the app remains usable in:

- local demos
- offline environments
- classroom or competition environments
- Streamlit Cloud deployments without secrets

这保证了程序在以下场景中依然可用：

- 本地演示
- 无网络或离线环境
- 评审现场演示
- 未配置密钥的 Streamlit Cloud 部署环境

> Important: No real API key is included in this repository. / 重要：本仓库不包含任何真实 API Key。

## Local Run Guide / 本地运行指南

### 1. Clone the repository / 克隆仓库
```bash
git clone <your_repository_url>
cd <project_folder>
```

### 2. Create a virtual environment / 创建虚拟环境
```bash
python -m venv .venv
```

Windows:
```bash
.venv\Scripts\activate
```

Linux / macOS:
```bash
source .venv/bin/activate
```

### 3. Install dependencies / 安装依赖
```bash
pip install -r requirements.txt
```

### 4. Launch the app / 启动应用
```bash
streamlit run app.py
```

### 5. Optional: configure local secrets / 可选：配置本地 secrets
If you want to use DeepSeek API locally, create `.streamlit/secrets.toml`:

```toml
DEEPSEEK_API_KEY = "your_api_key_here"
```

If you do not provide the key, the app will still run normally using the fallback rules engine.

如果你想在本地使用 DeepSeek API，可以创建 `.streamlit/secrets.toml`：

```toml
DEEPSEEK_API_KEY = "your_api_key_here"
```

如果不填密钥，应用仍将正常运行，并自动启用规则兜底模式。

## Deployment Notes / 部署说明

For Streamlit Cloud deployment, configure the secret via the platform's secret management interface:

```toml
DEEPSEEK_API_KEY = "your_api_key_here"
```

If the secret is absent, the app will continue to work without crashing.

对于 Streamlit Cloud 部署，可在平台的 Secret 管理页面中配置：

```toml
DEEPSEEK_API_KEY = "your_api_key_here"
```

如果没有配置密钥，应用仍然可以稳定运行，不会因为缺失密钥而崩溃。

## Files / 文件说明

- `app.py` — main application logic / 主程序
- `requirements.txt` — dependencies / 依赖列表
- `README.md` — project documentation / 项目说明
- `.streamlit/secrets.toml.example` — example secret template / 密钥模板示例

## License / 许可证

This project is intended for demonstration, evaluation, and research use in line optimization workflows. Please confirm local compliance with any organizational requirements before public deployment.

本项目适用于产线优化方案演示、评审展示和研究验证。公开部署前，请确认是否符合贵组织或团队的相关合规要求。
