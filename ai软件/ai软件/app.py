import html
import io
import json
import re
import textwrap

import pandas as pd
import plotly.graph_objects as go
import streamlit as st


def parse_first_number(val):
    if pd.isna(val):
        return None
    match = re.search(r"[-+]?\d*\.\d+|\d+", str(val))
    return float(match.group()) if match else None


st.set_page_config(
    page_title="线搭子 AI · 产线方案重配置搭子",
    page_icon="🏭",
    layout="wide",
)

st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        background-color: var(--secondary-background-color) !important;
    }

    /* 仅在亮色模式下，将 Plotly 图表内的文字强制变为纯黑 */
    [data-theme="light"] .js-plotly-plot .main-svg text {
        fill: #000000 !important;
        font-weight: 500 !important;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

INDUSTRY_TEMPLATES = {
    "新能源汽车总装": {
        "production_line": [
            {"name": "电池合装", "model": "未配置", "takt": 26},
            {"name": "电池包热管理", "model": "未配置", "takt": 22},
            {"name": "底盘总装", "model": "未配置", "takt": 28},
            {"name": "整车检测", "model": "未配置", "takt": 20},
            {"name": "成品下线", "model": "未配置", "takt": 18},
        ],
        "database": [
            {
                "工位": "电池合装", "机型": "新松 SR5A", "产地": "中国", "品牌产地": "国产", "品牌名称": "新松",
                "工序类型": "上下料", "臂展半径": 900, "承重(kg)": 20, "精度": "±0.02 mm", "精度(mm)": 0.02,
                "是否支持视觉": True, "价格": 120000, "维保响应": "24小时", "节拍秒数": 20,
            },
            {
                "工位": "电池合装", "机型": "ABB IRB 1200", "产地": "瑞典", "品牌产地": "进口", "品牌名称": "ABB",
                "工序类型": "上下料", "臂展半径": 700, "承重(kg)": 3, "精度": "±0.01 mm", "精度(mm)": 0.01,
                "是否支持视觉": True, "价格": 180000, "维保响应": "24小时", "节拍秒数": 18,
            },
            {
                "工位": "电池包热管理", "机型": "埃斯顿 JAKA", "产地": "中国", "品牌产地": "国产", "品牌名称": "埃斯顿",
                "工序类型": "装配", "臂展半径": 800, "承重(kg)": 10, "精度": "±0.03 mm", "精度(mm)": 0.03,
                "是否支持视觉": True, "价格": 98000, "维保响应": "48小时", "节拍秒数": 24,
            },
            {
                "工位": "底盘总装", "机型": "KUKA KR 6 R900", "产地": "德国", "品牌产地": "进口", "品牌名称": "KUKA",
                "工序类型": "装配", "臂展半径": 900, "承重(kg)": 6, "精度": "±0.02 mm", "精度(mm)": 0.02,
                "是否支持视觉": True, "价格": 200000, "维保响应": "24小时", "节拍秒数": 22,
            },
            {
                "工位": "整车检测", "机型": "安川 GP12", "产地": "日本", "品牌产地": "进口", "品牌名称": "安川",
                "工序类型": "装配", "臂展半径": 1200, "承重(kg)": 12, "精度": "±0.01 mm", "精度(mm)": 0.01,
                "是否支持视觉": True, "价格": 150000, "维保响应": "12小时", "节拍秒数": 17,
            },
            {
                "工位": "成品下线", "机型": "新松 SR7A", "产地": "中国", "品牌产地": "国产", "品牌名称": "新松",
                "工序类型": "码垛", "臂展半径": 1300, "承重(kg)": 30, "精度": "±0.03 mm", "精度(mm)": 0.03,
                "是否支持视觉": True, "价格": 150000, "维保响应": "24小时", "节拍秒数": 16,
            },
        ],
    },
    "传统零件机加工": {
        "production_line": [
            {"name": "CNC粗车", "model": "未配置", "takt": 32},
            {"name": "CNC精加工", "model": "未配置", "takt": 28},
            {"name": "铣削加工", "model": "未配置", "takt": 30},
            {"name": "热处理", "model": "未配置", "takt": 24},
            {"name": "质检入库", "model": "未配置", "takt": 20},
        ],
        "database": [
            {
                "工位": "CNC粗车", "机型": "新松 SR4A", "产地": "中国", "品牌产地": "国产", "品牌名称": "新松",
                "工序类型": "上下料", "臂展半径": 700, "承重(kg)": 8, "精度": "±0.02 mm", "精度(mm)": 0.02,
                "是否支持视觉": False, "价格": 98000, "维保响应": "24小时", "节拍秒数": 30,
            },
            {
                "工位": "CNC粗车", "机型": "DMG-1500", "产地": "德国", "品牌产地": "进口", "品牌名称": "DMG",
                "工序类型": "装配", "臂展半径": 800, "承重(kg)": 12, "精度": "±0.01 mm", "精度(mm)": 0.01,
                "是否支持视觉": True, "价格": 260000, "维保响应": "24小时", "节拍秒数": 26,
            },
            {
                "工位": "CNC精加工", "机型": "发那科 M-20iA", "产地": "日本", "品牌产地": "进口", "品牌名称": "发那科",
                "工序类型": "装配", "臂展半径": 1000, "承重(kg)": 20, "精度": "±0.015 mm", "精度(mm)": 0.015,
                "是否支持视觉": True, "价格": 210000, "维保响应": "24小时", "节拍秒数": 27,
            },
            {
                "工位": "铣削加工", "机型": "埃斯顿 JAKA", "产地": "中国", "品牌产地": "国产", "品牌名称": "埃斯顿",
                "工序类型": "装配", "臂展半径": 850, "承重(kg)": 15, "精度": "±0.03 mm", "精度(mm)": 0.03,
                "是否支持视觉": True, "价格": 87000, "维保响应": "48小时", "节拍秒数": 28,
            },
            {
                "工位": "热处理", "机型": "ABB IRB 2600", "产地": "瑞典", "品牌产地": "进口", "品牌名称": "ABB",
                "工序类型": "焊接", "臂展半径": 1800, "承重(kg)": 30, "精度": "±0.04 mm", "精度(mm)": 0.04,
                "是否支持视觉": True, "价格": 180000, "维保响应": "72小时", "节拍秒数": 23,
            },
            {
                "工位": "质检入库", "机型": "库卡 KR 8 R2100", "产地": "德国", "品牌产地": "进口", "品牌名称": "库卡",
                "工序类型": "装配", "臂展半径": 2100, "承重(kg)": 8, "精度": "±0.01 mm", "精度(mm)": 0.01,
                "是否支持视觉": True, "价格": 180000, "维保响应": "12小时", "节拍秒数": 18,
            },
        ],
    },
}

ARM_PROCESS_TYPES = ["上下料", "装配", "焊接", "喷漆", "码垛"]


def infer_arm_process_type(station_name):
    station_text = str(station_name or "").strip().lower()
    if any(keyword in station_text for keyword in ["上料", "下料", "搬运", "输送", "料"]):
        return "上下料"
    if any(keyword in station_text for keyword in ["装配", "组装", "装配线", "精装", "焊接", "总装"]):
        return "装配"
    if any(keyword in station_text for keyword in ["焊", "焊接", "点焊", "缝焊"]):
        return "焊接"
    if any(keyword in station_text for keyword in ["喷", "涂", "喷涂", "喷漆"]):
        return "喷漆"
    if any(keyword in station_text for keyword in ["码垛", "堆垛", "立体库", "出库"]):
        return "码垛"
    return "装配"


def normalize_bool(value):
    if isinstance(value, bool):
        return value
    if value is None or pd.isna(value):
        return False
    text = str(value).strip().lower()
    if text in {"1", "true", "yes", "y", "支持", "支持视觉", "有", "on"}:
        return True
    if text in {"0", "false", "no", "n", "不支持", "无", "off"}:
        return False
    return False


def normalize_numeric(value, default=0.0):
    if value is None or pd.isna(value):
        return float(default)
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).replace(",", "").strip()
    match = re.search(r"[-+]?\d*\.?\d+(?:[eE][-+]?\d+)?", text)
    if match:
        return float(match.group(0))
    return float(default)


def ensure_arm_database_columns(database):
    if database is None:
        return pd.DataFrame(columns=["工位", "机型", "产地", "品牌产地", "品牌名称", "工序类型", "臂展半径", "承重(kg)", "精度", "精度(mm)", "是否支持视觉", "IP防护", "运行速度", "通讯接口", "耐用性", "核心特点", "瓶颈局限性", "Pros", "Cons", "价格", "维保响应", "节拍秒数"])

    database = database.copy()
    database.columns = [str(column).strip() for column in database.columns]
    if "工位" not in database.columns:
        database["工位"] = "未知工位"
    if "机型" not in database.columns:
        database["机型"] = database.get("品牌名称", "未知机型")
    if "产地" not in database.columns:
        database["产地"] = database.get("品牌产地", "未知")
    if "品牌产地" not in database.columns:
        database["品牌产地"] = database["产地"].fillna("未知")
    if "品牌名称" not in database.columns:
        database["品牌名称"] = database["机型"].fillna("未知机型")
    if "工序类型" not in database.columns:
        database["工序类型"] = database["工位"].map(infer_arm_process_type)
    if "臂展半径" not in database.columns:
        database["臂展半径"] = 800.0
    if "承重(kg)" not in database.columns:
        database["承重(kg)"] = 10.0
    if "精度(mm)" not in database.columns:
        database["精度(mm)"] = database["精度"].map(parse_first_number).fillna(0.05)
    if "是否支持视觉" not in database.columns:
        database["是否支持视觉"] = False
    if "IP防护" not in database.columns:
        database["IP防护"] = None
    if "运行速度" not in database.columns:
        database["运行速度"] = None
    if "通讯接口" not in database.columns:
        database["通讯接口"] = None
    if "耐用性" not in database.columns:
        database["耐用性"] = None
    if "核心特点" not in database.columns:
        database["核心特点"] = None
    if "瓶颈局限性" not in database.columns:
        database["瓶颈局限性"] = None
    if "Pros" not in database.columns:
        database["Pros"] = None
    if "Cons" not in database.columns:
        database["Cons"] = None

    database["工位"] = database["工位"].fillna("未知工位").astype(str).str.strip()
    database["机型"] = database["机型"].fillna("未知机型").astype(str).str.strip()
    database["品牌名称"] = database["品牌名称"].fillna(database["机型"]).astype(str).str.strip()
    database["品牌产地"] = database["品牌产地"].fillna(database["产地"]).astype(str).str.strip()
    database["产地"] = database["产地"].fillna(database["品牌产地"]).astype(str).str.strip()
    database["工序类型"] = database["工序类型"].fillna("装配").astype(str).str.strip()
    database["臂展半径"] = pd.to_numeric(database["臂展半径"], errors="coerce").fillna(800.0)
    database["承重(kg)"] = pd.to_numeric(database["承重(kg)"], errors="coerce").fillna(10.0)
    database["精度(mm)"] = pd.to_numeric(database["精度(mm)"], errors="coerce").fillna(
        pd.to_numeric(database["精度"].map(parse_first_number), errors="coerce").fillna(0.05)
    )
    database["是否支持视觉"] = database["是否支持视觉"].map(normalize_bool).fillna(False)
    database["IP防护"] = database["IP防护"].fillna("IP65").astype(str)
    database["运行速度"] = pd.to_numeric(database["运行速度"].map(normalize_numeric), errors="coerce").fillna(
        database["承重(kg)"].map(lambda load: 180 if load <= 10 else 120)
    )
    database["通讯接口"] = database["通讯接口"].fillna("EtherNet/IP、Profinet").astype(str)
    database["耐用性"] = database["耐用性"].fillna("MTBF 80,000小时").astype(str)
    database["核心特点"] = database["核心特点"].fillna("").astype(str)
    database["瓶颈局限性"] = database["瓶颈局限性"].fillna("").astype(str)

    def describe_features(row):
        characteristics = []
        if row["承重(kg)"] >= 20:
            characteristics.append("高刚性，适合重载搬运")
        elif row["承重(kg)"] <= 5:
            characteristics.append("轻量灵活，适合小型精密作业")
        else:
            characteristics.append("负载与作业范围均衡")
        if row["精度(mm)"] <= 0.02:
            characteristics.append("重复定位精度较高")
        if row["运行速度"] >= 160:
            characteristics.append("运行速度快，适合高节拍")
        if row["IP防护"].upper().replace(" ", "") >= "IP67":
            characteristics.append("防护能力较强")
        return "；".join(characteristics)

    def describe_limitations(row):
        limitations = []
        if not row["是否支持视觉"]:
            limitations.append("本机型无视觉接口")
        if row["运行速度"] < 120:
            limitations.append("运行速度较慢，不适合极高节拍")
        if row["承重(kg)"] <= 5:
            limitations.append("负载较小，不适合重载工件")
        if not limitations:
            limitations.append("需结合现场工装、节拍及安全围栏进行最终校核")
        return "；".join(limitations)

    database.loc[database["核心特点"].str.strip().eq(""), "核心特点"] = database.loc[
        database["核心特点"].str.strip().eq("")
    ].apply(describe_features, axis=1)
    database.loc[database["瓶颈局限性"].str.strip().eq(""), "瓶颈局限性"] = database.loc[
        database["瓶颈局限性"].str.strip().eq("")
    ].apply(describe_limitations, axis=1)
    if "价格" not in database.columns:
        database["价格"] = 0
    if "维保响应" not in database.columns:
        database["维保响应"] = "24小时"
    if "节拍秒数" not in database.columns:
        database["节拍秒数"] = 20
    database["节拍秒数"] = pd.to_numeric(database["节拍秒数"], errors="coerce").fillna(20)

    database["Pros"] = database["Pros"].fillna("").astype(str)
    database["Cons"] = database["Cons"].fillna("").astype(str)

    def describe_pros(row):
        advantages = [item.strip() for item in str(row["核心特点"]).split("；") if item.strip()]
        if parse_first_number(row["IP防护"]) >= 67:
            advantages.append("防护等级高")
        if row["精度(mm)"] <= 0.02:
            advantages.append("精度表现优秀")
        if row["承重(kg)"] >= 20:
            advantages.append("适合重载")
        return "；".join(dict.fromkeys(advantages)) or "参数配置均衡，适用于常规工业工位"

    def describe_cons(row):
        limitations = [item.strip() for item in str(row["瓶颈局限性"]).split("；") if item.strip()]
        if not normalize_bool(row["是否支持视觉"]):
            limitations.append("无视觉接口")
        if normalize_numeric(row["运行速度"]) < 120:
            limitations.append("运行速度一般")
        if normalize_numeric(row["价格"]) >= 200000:
            limitations.append("采购成本较高")
        return "；".join(dict.fromkeys(limitations)) or "需结合现场工装和节拍要求进行校核"

    missing_pros = database["Pros"].str.strip().eq("")
    missing_cons = database["Cons"].str.strip().eq("")
    database.loc[missing_pros, "Pros"] = database.loc[missing_pros].apply(describe_pros, axis=1)
    database.loc[missing_cons, "Cons"] = database.loc[missing_cons].apply(describe_cons, axis=1)
    return database


def build_arm_brand_options(database, process_type="全部"):
    if database is None or database.empty:
        return ["全部", "国产", "进口"]
    filtered = database.copy()
    if process_type != "全部":
        filtered = filtered[filtered["工序类型"].fillna("").astype(str).str.contains(process_type, na=False)]
    if filtered.empty:
        return ["全部", "国产", "进口"]
    brands = sorted({str(value).strip() for value in filtered["品牌名称"].fillna(filtered["机型"]).astype(str).dropna() if str(value).strip()})
    options = ["全部", "国产", "进口"] + brands
    return options


def filter_arm_candidates(database, process_type="全部", brand_scope="全部", radius_min=0, payload_min=0, precision_limit=5.0, require_vision=False):
    if database is None or database.empty:
        return pd.DataFrame(columns=["工位", "机型", "产地", "品牌产地", "品牌名称", "工序类型", "臂展半径", "承重(kg)", "精度", "精度(mm)", "是否支持视觉", "价格", "维保响应", "节拍秒数"])

    candidates = ensure_arm_database_columns(database).copy()
    if process_type != "全部":
        candidates = candidates[candidates["工序类型"].fillna("").astype(str).str.contains(process_type, na=False)]

    if candidates.empty:
        base_pool = ensure_arm_database_columns(database).copy()
        if process_type != "全部":
            base_pool = base_pool[base_pool["工序类型"].fillna("").astype(str).str.contains(process_type, na=False)]
        if base_pool.empty:
            base_pool = ensure_arm_database_columns(database).copy()
        return base_pool.reset_index(drop=True)

    if brand_scope == "国产":
        candidates = candidates[candidates["品牌产地"].fillna(candidates["产地"]).astype(str).map(is_domestic)]
    elif brand_scope == "进口":
        candidates = candidates[~candidates["品牌产地"].fillna(candidates["产地"]).astype(str).map(is_domestic)]
    elif brand_scope not in {"", "全部", None}:
        brand_key = brand_scope.strip()
        candidates = candidates[
            candidates["品牌名称"].fillna(candidates["机型"]).astype(str).str.contains(brand_key, na=False)
            | candidates["品牌产地"].fillna(candidates["产地"]).astype(str).str.contains(brand_key, na=False)
        ]

    if radius_min > 0:
        candidates = candidates[pd.to_numeric(candidates["臂展半径"], errors="coerce").fillna(0) >= radius_min]
    if payload_min > 0:
        candidates = candidates[pd.to_numeric(candidates["承重(kg)"], errors="coerce").fillna(0) >= payload_min]
    if precision_limit is not None:
        candidates = candidates[pd.to_numeric(candidates["精度(mm)"], errors="coerce").fillna(99) <= precision_limit]
    if require_vision:
        candidates = candidates[candidates["是否支持视觉"].map(normalize_bool)]

    if candidates.empty:
        fallback = ensure_arm_database_columns(database).copy()
        if process_type != "全部":
            fallback = fallback[fallback["工序类型"].fillna("").astype(str).str.contains(process_type, na=False)]
        if fallback.empty:
            fallback = ensure_arm_database_columns(database).copy()
        return fallback.reset_index(drop=True)

    return candidates.reset_index(drop=True)


def apply_model_to_station(model_row, station_name):
    if not station_name:
        return False
    station_item = next(
        (item for item in st.session_state["production_line"] if item["name"] == station_name),
        None,
    )
    if station_item is None:
        return False
    model_name = str(model_row.get("机型", model_row.get("品牌名称", "未知机型")))
    takt_value = float(model_row.get("节拍秒数", 20))
    if takt_value.is_integer():
        takt_value = int(takt_value)
    station_item["model"] = model_name
    station_item["takt"] = takt_value
    sync_line_state()
    return True


def recommend_arm_model(candidates, scenario, station_name, requirements, api_key):
    if candidates is None or candidates.empty:
        return None, "当前没有可供推荐的候选机型。", "本地规则"

    candidates = ensure_arm_database_columns(candidates).reset_index(drop=True)
    numeric_scores = pd.DataFrame(index=candidates.index)
    for column, score_name, ascending in [
        ("承重(kg)", "payload", True),
        ("臂展半径", "radius", True),
        ("精度(mm)", "precision", False),
        ("运行速度", "speed", True),
        ("耐用性", "durability", True),
        ("价格", "price", False),
    ]:
        values = candidates[column].map(normalize_numeric)
        numeric_scores[score_name] = values.rank(pct=True, ascending=ascending).fillna(0.5)
    numeric_scores["total"] = (
        numeric_scores["payload"] * 0.22
        + numeric_scores["radius"] * 0.16
        + numeric_scores["precision"] * 0.18
        + numeric_scores["speed"] * 0.16
        + numeric_scores["durability"] * 0.12
        + numeric_scores["price"] * 0.16
    )
    local_index = int(numeric_scores["total"].idxmax())
    local_model = candidates.iloc[local_index]
    local_reason = (
        f"该机型在当前候选中综合兼顾了承重、工作半径、重复定位精度、速度和耐用性，"
        f"且价格表现相对均衡，适用于“{scenario or '当前产线场景'}”的“{station_name}”工位。"
    )

    if not api_key:
        return local_model.to_dict(), local_reason, "本地规则（未配置 API Key）"

    try:
        from openai import OpenAI

        model_records = candidates[
            [
                "机型", "品牌名称", "品牌产地", "工序类型", "承重(kg)", "臂展半径", "精度(mm)",
                "IP防护", "运行速度", "通讯接口", "耐用性", "是否支持视觉", "核心特点", "瓶颈局限性", "价格",
            ]
        ].to_dict(orient="records")
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com", timeout=25)
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "你是工业机器人选型专家。只能从候选列表中选择一款，综合应用场景和工位参数，"
                        "不得虚构候选数据。只返回 JSON：{\"model\":\"候选机型的机型字段\",\"reason\":\"说明理由和适用边界\"}。"
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "应用场景": scenario,
                            "目标工位": station_name,
                            "用户参数要求": requirements,
                            "候选机型": model_records,
                        },
                        ensure_ascii=False,
                        default=str,
                    ),
                },
            ],
            response_format={"type": "json_object"},
        )
        result = json.loads(response.choices[0].message.content)
        model_name = str(result.get("model", "")).strip()
        matched = candidates[candidates["机型"].astype(str) == model_name]
        reason = str(result.get("reason", "根据场景与参数匹配结果推荐该机型。" )).strip()
        if matched.empty:
            return local_model.to_dict(), local_reason, "本地规则（AI 返回了候选库外机型）"
        return matched.iloc[0].to_dict(), reason, "DeepSeek AI"
    except Exception:
        return local_model.to_dict(), local_reason, "本地规则（AI 服务暂不可用）"


def sync_line_state():
    st.session_state["current_station_takts"] = {
        item["name"]: item["takt"] for item in st.session_state["production_line"]
    }
    st.session_state["current_station_models"] = {
        item["name"]: item["model"] for item in st.session_state["production_line"]
    }


def normalize_station_label(value):
    return re.sub(r"[\s_\-]+", "", str(value).strip().lower())


def get_station_candidate_models(model_library, selected_station):
    if model_library is None or model_library.empty:
        return pd.DataFrame(columns=["工位", "机型", "产地", "精度", "价格", "维保响应", "节拍秒数"])

    target = str(selected_station).strip()
    normalized_target = normalize_station_label(target)
    generic_values = {
        "通用",
        "全部",
        "全厂通用",
        "全线通用",
        "总装通用",
        "通用机型",
        "all",
        "general",
        "universal",
    }

    exact_candidates = model_library[
        model_library["工位"].astype(str).map(lambda label: normalize_station_label(label) == normalized_target)
    ].copy()
    if not exact_candidates.empty:
        return exact_candidates

    partial_candidates = model_library[
        model_library["工位"].astype(str).map(
            lambda label: normalized_target in normalize_station_label(label)
            or normalize_station_label(label) in normalized_target
        )
    ].copy()
    if not partial_candidates.empty:
        return partial_candidates

    generic_candidates = model_library[
        model_library["工位"].astype(str).map(
            lambda label: normalize_station_label(label) in generic_values
        )
    ].copy()
    if not generic_candidates.empty:
        return generic_candidates

    return model_library.copy()


def extract_selected_station_from_event(event):
    if not isinstance(event, dict):
        return None

    for key in ("selection", "selected", "points", "selected_points", "point_indices"):
        if key in event and event[key] is not None:
            found = extract_selected_station_from_event(event[key])
            if found:
                return found

    for key in ("customdata", "text", "name", "station", "label", "x"):
        if key in event and event[key] not in (None, "", [], {}):
            value = event[key]
            if isinstance(value, (list, tuple)):
                value = value[0] if value else None
            if isinstance(value, str):
                cleaned = value.strip()
                if cleaned:
                    return cleaned

    if "points" in event and isinstance(event["points"], list):
        for point in event["points"]:
            found = extract_selected_station_from_event(point)
            if found:
                return found

    return None


def build_production_line_template_csv():
    template_df = pd.DataFrame(
        [
            {"工位顺序(数字)": 1, "工位名称": "电池合装", "当前机型": "BMS-A1", "节拍秒数": 20},
            {"工位顺序(数字)": 2, "工位名称": "电池包热管理", "当前机型": "Thermo-90", "节拍秒数": 24},
            {"工位顺序(数字)": 3, "工位名称": "底盘总装", "当前机型": "Chassis-RT", "节拍秒数": 22},
            {"工位顺序(数字)": 4, "工位名称": "整车检测", "当前机型": "VisionCheck", "节拍秒数": 17},
            {"工位顺序(数字)": 5, "工位名称": "成品下线", "当前机型": "LineExit-4", "节拍秒数": 16},
        ]
    )
    output = io.StringIO()
    template_df.to_csv(output, index=False, encoding="utf-8-sig")
    return output.getvalue()


def normalize_column_name(value):
    return str(value).strip().lower().replace("（", "(").replace("）", ")").replace(" ", "")


def load_existing_production_line(uploaded_file):
    uploaded_file.seek(0)
    database = pd.read_csv(uploaded_file, encoding="utf-8-sig")
    if database.empty:
        raise ValueError("上传的产线结构 CSV 为空。")

    available_cols = {normalize_column_name(col): col for col in database.columns}

    def resolve_column(*candidates):
        for candidate in candidates:
            normalized = normalize_column_name(candidate)
            if normalized in available_cols:
                return available_cols[normalized]
        return None

    order_col = resolve_column("工位顺序(数字)", "工位顺序", "工位顺序（数字）", "工位序号")
    name_col = resolve_column("工位名称", "工位名", "工位")
    model_col = resolve_column("当前机型", "机型")
    takt_col = resolve_column("节拍秒数", "节拍", "节拍(秒)", "节拍秒")

    if not all([order_col, name_col, model_col, takt_col]):
        required_columns = ["工位顺序(数字)", "工位名称", "当前机型", "节拍秒数"]
        raise ValueError(f"CSV 必须包含以下列：{', '.join(required_columns)}")

    cleaned = database[[order_col, name_col, model_col, takt_col]].copy()
    cleaned[order_col] = pd.to_numeric(cleaned[order_col], errors="coerce")
    cleaned[takt_col] = pd.to_numeric(cleaned[takt_col], errors="coerce")
    cleaned = cleaned.dropna(subset=[order_col, name_col, takt_col]).copy()
    cleaned[name_col] = cleaned[name_col].astype(str).str.strip()
    cleaned = cleaned[cleaned[name_col] != ""].copy()
    cleaned = cleaned.sort_values(order_col, ascending=True, kind="mergesort").reset_index(drop=True)

    if cleaned.empty:
        raise ValueError("CSV 中没有有效的工位结构数据。")

    if cleaned[order_col].duplicated().any():
        raise ValueError("工位顺序列中不能重复。")

    production_line = []
    for _, row in cleaned.iterrows():
        model_value = row[model_col]
        takt_value = float(row[takt_col])
        if pd.isna(takt_value) or takt_value <= 0:
            raise ValueError("节拍秒数必须是大于 0 的数字。")

        production_line.append(
            {
                "name": str(row[name_col]).strip(),
                "model": "未配置" if pd.isna(model_value) or str(model_value).strip() == "" else str(model_value).strip(),
                "takt": int(takt_value) if float(takt_value).is_integer() else float(takt_value),
            }
        )

    if len({item["name"] for item in production_line}) != len(production_line):
        raise ValueError("产线结构中不能出现重复工位名称。")

    st.session_state["production_line"] = production_line
    sync_line_state()
    return production_line


# 初始化各工位的占位节拍和已采用机型
initial_station_takts = {"上料": 18, "A装配": 25, "B精装": 32, "检测": 15, "下料": 12}
st.session_state.setdefault("current_station_takts", initial_station_takts.copy())
st.session_state.setdefault(
    "current_station_models",
    {station: "未配置" for station in initial_station_takts},
)


def apply_industry_template(template_name):
    template = INDUSTRY_TEMPLATES[template_name]
    st.session_state["industry_template"] = template_name
    st.session_state["production_line"] = [
        {"name": item["name"], "model": item.get("model", "未配置"), "takt": item["takt"]}
        for item in template["production_line"]
    ]
    st.session_state["arm_database"] = pd.DataFrame(template["database"])
    st.session_state["arm_database_name"] = f"{template_name}默认机型库"
    st.session_state["arm_database_is_builtin"] = True
    sync_line_state()
    st.session_state.setdefault("arm_filter_submitted", False)
    st.session_state.setdefault("arm_filter_conditions", None)


def handle_industry_template_change():
    selected_template = st.session_state.get("industry_template_selection")
    if not selected_template:
        return
    if selected_template != st.session_state.get("industry_template"):
        st.session_state["industry_template"] = selected_template
        apply_industry_template(selected_template)


st.session_state.setdefault("industry_template", "新能源汽车总装")
st.session_state.setdefault("industry_template_selection", st.session_state["industry_template"])
if "production_line" not in st.session_state:
    apply_industry_template(st.session_state["industry_template"])

sync_line_state()
st.session_state.setdefault("target_capacity", 100)
st.session_state.setdefault("ai_parsed_result", None)
st.session_state.setdefault("ai_parse_mode", None)

# 在下一轮渲染、创建输入控件前提交产线变更，避免动态选项造成 Key 冲突
pending_station_add = st.session_state.pop("line_pending_add", None)
if pending_station_add is not None:
    existing_names = {item["name"] for item in st.session_state["production_line"]}
    if pending_station_add["name"] not in existing_names:
        insert_index = max(
            0,
            min(pending_station_add.get("index", len(st.session_state["production_line"])),
                len(st.session_state["production_line"])),
        )
        station_record = {
            "name": pending_station_add["name"],
            "model": pending_station_add["model"],
            "takt": pending_station_add["takt"],
        }
        st.session_state["production_line"].insert(insert_index, station_record)
        st.session_state["line_edit_notice"] = f"已添加工位：{pending_station_add['name']}"
        st.session_state["new_station_name"] = ""
    else:
        st.session_state["line_edit_notice"] = f"工位“{pending_station_add['name']}”已存在"
    sync_line_state()

pending_station_delete = st.session_state.pop("line_pending_delete", None)
if pending_station_delete is not None:
    before_count = len(st.session_state["production_line"])
    st.session_state["production_line"] = [
        item for item in st.session_state["production_line"]
        if item["name"] != pending_station_delete
    ]
    if len(st.session_state["production_line"]) < before_count:
        st.session_state["line_edit_notice"] = f"已删除工位：{pending_station_delete}"
    sync_line_state()

line_station_names = list(st.session_state["current_station_takts"])
insert_position_indices = {"添加到最前面": 0}
insert_position_indices.update(
    {
        f"插入到 {item['name']} 之后": index + 1
        for index, item in enumerate(st.session_state["production_line"])
    }
)
insert_position_indices["添加到最末尾"] = len(st.session_state["production_line"])
if st.session_state.get("new_station_position") not in insert_position_indices:
    st.session_state["new_station_position"] = "添加到最末尾"

if line_station_names:
    if st.session_state.get("filter_station") not in line_station_names:
        st.session_state["filter_station"] = line_station_names[0]
    if st.session_state.get("delete_station") not in line_station_names:
        st.session_state["delete_station"] = line_station_names[0]
    if (
        st.session_state.get("arm_filter_conditions")
        and st.session_state["arm_filter_conditions"].get("station") not in line_station_names
    ):
        st.session_state["arm_filter_submitted"] = False
else:
    st.session_state.pop("filter_station", None)
    st.session_state.pop("delete_station", None)
    st.session_state["arm_filter_submitted"] = False

# 确认 AI 方案后更新对应的有序工位记录
pending_ai_apply = st.session_state.pop("ai_pending_apply", None)
if pending_ai_apply is not None:
    station = pending_ai_apply["station"]
    station_item = next(
        (item for item in st.session_state["production_line"] if item["name"] == station),
        None,
    )
    if station_item is not None:
        station_item["model"] = pending_ai_apply["model"]
        station_item["takt"] = pending_ai_apply["takt"]
        st.session_state["target_capacity"] = pending_ai_apply["target_capacity"]
        st.session_state["ai_apply_notice"] = (
            f"已更新 {station}：采用 {pending_ai_apply['model']}，"
            f"目标产能 {pending_ai_apply['target_capacity']:g} 件/小时。"
        )
        sync_line_state()

# 内置机械臂数据：保留兼容旧字段，并补齐最终要求的三级联动字段
required_arm_columns = [
    "工位",
    "机型",
    "产地",
    "品牌产地",
    "品牌名称",
    "工序类型",
    "臂展半径",
    "承重(kg)",
    "精度",
    "精度(mm)",
    "是否支持视觉",
    "IP防护",
    "运行速度",
    "通讯接口",
    "耐用性",
    "核心特点",
    "瓶颈局限性",
    "价格",
    "维保响应",
    "节拍秒数",
]
default_arm_rows = [
    {
        "工位": "电池合装", "机型": "新松 SR5A", "产地": "中国", "品牌产地": "国产", "品牌名称": "新松",
        "工序类型": "上下料", "臂展半径": 900, "承重(kg)": 20, "精度": "±0.02 mm", "精度(mm)": 0.02,
        "是否支持视觉": True, "价格": 120000, "维保响应": "24小时", "节拍秒数": 20,
    },
    {
        "工位": "电池合装", "机型": "ABB IRB 1200", "产地": "瑞典", "品牌产地": "进口", "品牌名称": "ABB",
        "工序类型": "上下料", "臂展半径": 700, "承重(kg)": 3, "精度": "±0.01 mm", "精度(mm)": 0.01,
        "是否支持视觉": True, "价格": 180000, "维保响应": "24小时", "节拍秒数": 18,
    },
    {
        "工位": "底盘总装", "机型": "KUKA KR 6 R900", "产地": "德国", "品牌产地": "进口", "品牌名称": "KUKA",
        "工序类型": "装配", "臂展半径": 900, "承重(kg)": 6, "精度": "±0.02 mm", "精度(mm)": 0.02,
        "是否支持视觉": True, "价格": 200000, "维保响应": "24小时", "节拍秒数": 22,
    },
    {
        "工位": "底盘总装", "机型": "埃斯顿 JAKA", "产地": "中国", "品牌产地": "国产", "品牌名称": "埃斯顿",
        "工序类型": "装配", "臂展半径": 800, "承重(kg)": 10, "精度": "±0.03 mm", "精度(mm)": 0.03,
        "是否支持视觉": True, "价格": 98000, "维保响应": "48小时", "节拍秒数": 24,
    },
    {
        "工位": "整车检测", "机型": "安川 GP12", "产地": "日本", "品牌产地": "进口", "品牌名称": "安川",
        "工序类型": "装配", "臂展半径": 1200, "承重(kg)": 12, "精度": "±0.01 mm", "精度(mm)": 0.01,
        "是否支持视觉": True, "价格": 150000, "维保响应": "12小时", "节拍秒数": 17,
    },
    {
        "工位": "成品下线", "机型": "新松 SR7A", "产地": "中国", "品牌产地": "国产", "品牌名称": "新松",
        "工序类型": "码垛", "臂展半径": 1300, "承重(kg)": 30, "精度": "±0.03 mm", "精度(mm)": 0.03,
        "是否支持视觉": True, "价格": 150000, "维保响应": "24小时", "节拍秒数": 16,
    },
    {
        "工位": "成品下线", "机型": "ABB IRB 6700", "产地": "瑞典", "品牌产地": "进口", "品牌名称": "ABB",
        "工序类型": "码垛", "臂展半径": 1500, "承重(kg)": 45, "精度": "±0.04 mm", "精度(mm)": 0.04,
        "是否支持视觉": True, "价格": 220000, "维保响应": "24小时", "节拍秒数": 14,
    },
    {
        "工位": "电池包热管理", "机型": "发那科 M-20iA", "产地": "日本", "品牌产地": "进口", "品牌名称": "发那科",
        "工序类型": "装配", "臂展半径": 1000, "承重(kg)": 20, "精度": "±0.015 mm", "精度(mm)": 0.015,
        "是否支持视觉": True, "价格": 210000, "维保响应": "24小时", "节拍秒数": 21,
    },
    {
        "工位": "电池包热管理", "机型": "库卡 KR 8 R2100", "产地": "德国", "品牌产地": "进口", "品牌名称": "库卡",
        "工序类型": "焊接", "臂展半径": 2100, "承重(kg)": 8, "精度": "±0.01 mm", "精度(mm)": 0.01,
        "是否支持视觉": True, "价格": 180000, "维保响应": "12小时", "节拍秒数": 18,
    },
    {
        "工位": "电池包热管理", "机型": "新松 SR7A", "产地": "中国", "品牌产地": "国产", "品牌名称": "新松",
        "工序类型": "焊接", "臂展半径": 1300, "承重(kg)": 25, "精度": "±0.03 mm", "精度(mm)": 0.03,
        "是否支持视觉": True, "价格": 140000, "维保响应": "24小时", "节拍秒数": 19,
    },
]
st.session_state.setdefault("arm_database_name", "内置机械臂数据")
st.session_state.setdefault(
    "arm_database_is_builtin",
    st.session_state["arm_database_name"] == "内置机械臂数据",
)
if st.session_state["arm_database_is_builtin"]:
    st.session_state["arm_database"] = ensure_arm_database_columns(pd.DataFrame(default_arm_rows))
else:
    st.session_state.setdefault("arm_database", ensure_arm_database_columns(pd.DataFrame(default_arm_rows)))
st.session_state.setdefault("arm_filter_submitted", False)
st.session_state.setdefault("arm_filter_conditions", None)


# 读取并校验用户上传的 CSV 或 Excel 机械臂数据库
def load_arm_database(uploaded_file):
    file_extension = uploaded_file.name.rsplit(".", 1)[-1].lower()
    uploaded_file.seek(0)
    if file_extension == "csv":
        try:
            database = pd.read_csv(uploaded_file, encoding="utf-8-sig")
        except UnicodeDecodeError:
            uploaded_file.seek(0)
            database = pd.read_csv(uploaded_file, encoding="gb18030")
    else:
        uploaded_file.seek(0)
        database = pd.read_excel(uploaded_file)

    if database.empty:
        raise ValueError("文件中没有机械臂数据")

    database = ensure_arm_database_columns(database)
    invalid_rows = (
        database["工位"].eq("未知工位")
        | database["机型"].eq("未知机型")
        | database["节拍秒数"].isna()
        | database["节拍秒数"].le(0)
    )
    if invalid_rows.any():
        raise ValueError("工位、机型不能为空，节拍秒数必须是大于 0 的数字")
    return database


# 计算当前节拍最长的工位
def calc_line_takt(station_takts):
    if not station_takts:
        return None, None
    bottleneck_station = max(station_takts, key=station_takts.get)
    return bottleneck_station, station_takts[bottleneck_station]


def parse_price_yuan(value):
    amount = parse_first_number(value)
    if amount is None:
        return None
    if "万" in str(value):
        amount *= 10000
    return amount


def parse_maintenance_hours(value):
    hours = parse_first_number(value)
    if hours is None:
        return None
    unit = str(value).lower()
    if "天" in unit or "日" in unit or "day" in unit:
        return hours * 24
    if "分钟" in unit or "min" in unit:
        return hours / 60
    return hours


def is_domestic(origin):
    origin_text = str(origin).strip().lower()
    return "中国" in origin_text or "国产" in origin_text or origin_text in {"china", "cn", "prc"}


def resolve_line_station(requested_station, station_options):
    requested = str(requested_station).strip().lower()
    for station in station_options:
        station_text = str(station).strip()
        if requested == station_text.lower() or station_text.startswith(str(requested_station).strip()):
            return station
        station_prefix = re.match(r"[A-Za-z]+", station_text)
        if station_prefix and requested == station_prefix.group().lower():
            return station
    raise ValueError("AI 返回的工位不在当前产线中")


def rule_based_parse(text):
    requirements = []
    if "国产" in text:
        requirements.append("国产")
    elif "进口" in text:
        requirements.append("进口")
    if "高精度" in text:
        requirements.append("高精度")

    for origin in ("日本", "德国", "中国", "美国", "韩国", "法国"):
        if origin in text and origin not in requirements:
            requirements.append(origin)

    station_options = list(
        st.session_state.get("current_station_takts", initial_station_takts)
    )
    if not station_options:
        raise ValueError("当前产线没有可用工位")

    station = next(
        (name for name in station_options if str(name).lower() in text.lower()),
        None,
    )
    if station is None:
        station_match = re.search(r"([A-Za-z])\s*(?:工位|工序)", text)
        if station_match:
            try:
                station = resolve_line_station(station_match.group(1), station_options)
            except ValueError:
                station = None
    if station is None:
        selected_station = st.session_state.get("filter_station")
        station = selected_station if selected_station in station_options else station_options[0]

    capacity_match = re.search(
        r"(?:目标)?产能\s*(?:调整到|提高到|设为|为|[:：=])?\s*(\d+(?:\.\d+)?)",
        text,
    )
    if capacity_match is None:
        capacity_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:件\s*/\s*小时|件每小时)",
            text,
        )
    if capacity_match is None:
        capacity_match = re.search(r"\d+(?:\.\d+)?", text)

    if capacity_match is not None:
        target_capacity = float(capacity_match.group(1) if capacity_match.lastindex else capacity_match.group())
    else:
        target_capacity = float(st.session_state.get("target_capacity", 100))
    if target_capacity <= 0:
        target_capacity = float(st.session_state.get("target_capacity", 100))

    return {
        "工位": station,
        "要求": requirements,
        "目标产能": target_capacity,
    }


def choose_model_for_ai(database, ai_result, station_options):
    station = resolve_line_station(ai_result["工位"], station_options)
    target_capacity = float(ai_result["目标产能"])
    if target_capacity <= 0:
        raise ValueError("目标产能必须大于 0")

    candidates = database[database["工位"] == station].copy()
    requirements = [str(requirement).strip() for requirement in ai_result["要求"]]
    for requirement in requirements:
        if "国产" in requirement:
            candidates = candidates[candidates["产地"].map(is_domestic)]
        elif "进口" in requirement:
            candidates = candidates[~candidates["产地"].map(is_domestic)]
        elif "高精度" in requirement or "精度高" in requirement:
            precision = candidates["精度"].map(parse_first_number)
            candidates = candidates[precision.notna() & (precision <= 0.02)]
        elif "精度" in requirement:
            precision_limit = parse_first_number(requirement)
            if precision_limit is None:
                raise ValueError(f"无法识别精度要求：{requirement}")
            precision = candidates["精度"].map(parse_first_number)
            candidates = candidates[precision.notna() & (precision <= precision_limit)]
        elif "维保" in requirement or "响应" in requirement:
            maintenance_limit = parse_maintenance_hours(requirement)
            if maintenance_limit is None:
                raise ValueError(f"无法识别维保要求：{requirement}")
            maintenance = candidates["维保响应"].map(parse_maintenance_hours)
            candidates = candidates[maintenance.notna() & (maintenance <= maintenance_limit)]
        elif "价格" in requirement or "预算" in requirement:
            price_limit = parse_first_number(requirement)
            if price_limit is None:
                raise ValueError(f"无法识别价格要求：{requirement}")
            prices = pd.to_numeric(candidates["价格"], errors="coerce")
            candidates = candidates[prices.notna() & (prices <= price_limit)]
        else:
            origins = candidates["产地"].fillna("").astype(str)
            candidates = candidates[
                origins.str.contains(re.escape(requirement), case=False, regex=True)
            ]

        if candidates.empty:
            raise ValueError(f"未找到符合“{requirement}”要求的机械臂")

    max_station_takt = 3600 / target_capacity
    candidates = candidates[candidates["节拍秒数"] <= max_station_takt]
    if candidates.empty:
        if requirements:
            raise ValueError(
                f"未找到符合“{requirements[-1]}”要求及目标产能的机械臂"
            )
        raise ValueError("未找到符合目标产能要求的机械臂")

    selected_model = candidates.sort_values("节拍秒数", kind="stable").iloc[0]
    return station, selected_model, target_capacity


# AI 提供方配置放在侧边栏，并统一写入会话状态
st.session_state.setdefault("openai_compatible_base_url", "https://api.openai.com/v1")
st.session_state.setdefault("openai_compatible_api_key", "")
st.session_state.setdefault("openai_compatible_model", "")
st.session_state.setdefault("ollama_base_url", "http://localhost:11434/v1")
st.session_state.setdefault("ollama_api_key", "ollama")
st.session_state.setdefault("ollama_model", "")
st.session_state.setdefault("manual_api_key", "")


def safe_get_secret(secret_name):
    try:
        secrets = st.secrets
        if hasattr(secrets, "get"):
            value = secrets.get(secret_name, "")
        elif hasattr(secrets, secret_name):
            value = getattr(secrets, secret_name)
        else:
            value = ""
    except Exception:
        return ""
    if value is None:
        return ""
    return str(value).strip()


with st.sidebar:
    st.header("行业场景")
    template_options = list(INDUSTRY_TEMPLATES.keys())
    st.selectbox(
        "选择行业模板",
        template_options,
        index=template_options.index(st.session_state.get("industry_template", "新能源汽车总装")),
        key="industry_template_selection",
        on_change=handle_industry_template_change,
    )

    st.subheader("产线结构导入")
    uploaded_line_structure = st.file_uploader(
        "导入已有产线结构（CSV）",
        type=["csv"],
        key="uploaded_production_structure",
    )
    if uploaded_line_structure is not None:
        try:
            imported_line = load_existing_production_line(uploaded_line_structure)
            st.success(f"已导入现有产线结构，更新了 {len(imported_line)} 个工位。")
        except ValueError as error:
            st.error(f"产线结构导入失败：{error}")
    st.download_button(
        label="下载产线结构模板",
        data=build_production_line_template_csv(),
        file_name="产线结构模板.csv",
        mime="text/csv",
        key="download_production_template",
    )

    st.header("AI 设置区")
    ai_provider = st.selectbox(
        "AI 提供方",
        ["默认 DeepSeek", "OpenAI 兼容接口", "本地 Ollama"],
        key="ai_provider_selection",
    )

    if ai_provider == "默认 DeepSeek":
        manual_api_key = st.text_input(
            "请输入 DeepSeek API Key",
            type="password",
            key="manual_api_key",
            help="如不填写，将使用系统内置或自动降级为规则模式",
        )
        secret_api_key = safe_get_secret("DEEPSEEK_API_KEY")
        provider_api_key = (manual_api_key or secret_api_key).strip()
        ai_provider_config = {
            "provider": ai_provider,
            "base_url": "https://api.deepseek.com",
            "api_key": provider_api_key,
            "model": "deepseek-flash",
        }
        if provider_api_key:
            st.caption("已读取可用 DeepSeek Key，当前将优先使用此凭证。")
        else:
            st.warning("未配置 DeepSeek Key。当前版本未配置密钥时，将自动启用本地规则引擎进行解析。")
    elif ai_provider == "OpenAI 兼容接口":
        st.text_input("base_url", key="openai_compatible_base_url")
        st.text_input("api_key", type="password", key="openai_compatible_api_key")
        st.text_input("model", key="openai_compatible_model")
        ai_provider_config = {
            "provider": ai_provider,
            "base_url": st.session_state["openai_compatible_base_url"].strip(),
            "api_key": st.session_state["openai_compatible_api_key"].strip(),
            "model": st.session_state["openai_compatible_model"].strip(),
        }
    else:
        st.text_input("base_url", key="ollama_base_url")
        st.text_input("api_key", type="password", key="ollama_api_key")
        st.text_input("model", key="ollama_model")
        ai_provider_config = {
            "provider": ai_provider,
            "base_url": st.session_state["ollama_base_url"].strip(),
            "api_key": st.session_state["ollama_api_key"].strip(),
            "model": st.session_state["ollama_model"].strip(),
        }

    st.session_state["ai_provider_config"] = ai_provider_config

# 页面标题
st.title("线搭子 AI · 产线方案重配置搭子")

# 顶部输入区
upload_col, capacity_col, ai_col = st.columns([1.5, 1.2, 1])
with upload_col:
    uploaded_database = st.file_uploader(
        "导入机械臂数据库（CSV / Excel）",
        type=["csv", "xlsx", "xls"],
        key="arm_database_upload",
    )
with capacity_col:
    st.number_input(
        "目标产能（件/小时）",
        min_value=0,
        step=10,
        key="target_capacity",
    )
with ai_col:
    ai_enabled = st.toggle("AI 辅助", value=False, key="ai_enabled")

if ai_enabled:
    ai_description = st.text_area("用自然语言描述改动", key="ai_change_description")
    if st.button("AI 解析", key="parse_ai_change"):
        if not ai_description.strip():
            st.warning("请先描述希望调整的产线条件。")
        else:
            st.session_state["ai_parsed_result"] = None
            st.session_state["ai_parse_mode"] = None
            api_key = ""
            try:
                from openai import OpenAI

                provider_config = st.session_state.get("ai_provider_config", {})
                api_key = str(provider_config.get("api_key", "") or "").strip()
                base_url = str(provider_config.get("base_url", "") or "").strip()
                model_name = str(provider_config.get("model", "") or "").strip()
                provider_name = str(provider_config.get("provider", "") or "")

                if not api_key and provider_name != "本地 Ollama":
                    st.session_state["ai_parsed_result"] = rule_based_parse(ai_description)
                    st.session_state["ai_parse_mode"] = "规则兜底模式"
                    st.warning("未配置密钥，已自动启用本地规则引擎进行解析。")
                    raise RuntimeError("NO_API_KEY_FALLBACK")

                if not base_url or not model_name:
                    raise ValueError("请在 AI 设置区填写 base_url 和 model")

                station_options = list(st.session_state.get("current_station_takts", {}))
                client = OpenAI(
                    api_key=api_key or "ollama",
                    base_url=base_url,
                    timeout=30,
                )
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "你是产线重配置助手。根据用户描述，只返回一个合法 JSON 对象，"
                                '字段必须是 {"工位":"B精装","要求":["国产","高精度"],"目标产能":120}。'
                                "工位必须来自给定列表；若用户使用 A、B 等简称，映射到对应工位。"
                                "要求必须是字符串数组；高精度表示精度误差不大于 0.02 mm。"
                                "目标产能必须是大于 0 的数字，不要输出 Markdown 或额外说明。"
                            ),
                        },
                        {
                            "role": "user",
                            "content": (
                                f"当前产线工位：{json.dumps(station_options, ensure_ascii=False)}\n"
                                f"用户描述：{ai_description}"
                            ),
                        },
                    ],
                    response_format={"type": "json_object"},
                )
                parsed_result = json.loads(response.choices[0].message.content)
                if not isinstance(parsed_result, dict):
                    raise ValueError("AI 返回内容不是 JSON 对象")
                if not all(key in parsed_result for key in ("工位", "要求", "目标产能")):
                    raise ValueError("AI 返回结果缺少必需字段")
                if not isinstance(parsed_result["要求"], list) or not all(
                    isinstance(item, str) for item in parsed_result["要求"]
                ):
                    raise ValueError("AI 返回的要求字段格式不正确")
                parsed_result["工位"] = resolve_line_station(
                    parsed_result["工位"], station_options
                )
                parsed_result["目标产能"] = float(parsed_result["目标产能"])
                if parsed_result["目标产能"] <= 0:
                    raise ValueError("AI 返回的目标产能必须大于 0")
                st.session_state["ai_parsed_result"] = parsed_result
                st.session_state["ai_parse_mode"] = "AI 模式"
            except RuntimeError as error:
                if str(error) == "NO_API_KEY_FALLBACK":
                    pass
                else:
                    raise
            except Exception as error:
                try:
                    st.session_state["ai_parsed_result"] = rule_based_parse(ai_description)
                    st.session_state["ai_parse_mode"] = "规则兜底模式"
                    st.warning("AI 不可用，已自动切换到规则兜底模式。")
                except Exception as fallback_error:
                    st.session_state["ai_parsed_result"] = None
                    st.session_state["ai_parse_mode"] = None
                    st.error("AI 不可用，请关闭开关或稍后重试")
                    error = RuntimeError(f"{error}; 规则兜底失败：{fallback_error}")
                error_details = str(error)
                if api_key:
                    error_details = error_details.replace(api_key, "[API Key 已隐藏]")
                error_details = re.sub(r"sk-[A-Za-z0-9_-]+", "[API Key 已隐藏]", error_details)
                with st.expander("查看错误详情"):
                    st.code(f"{type(error).__name__}: {error_details}")

    parsed_result = st.session_state.get("ai_parsed_result")
    if parsed_result is not None:
        st.info(st.session_state.get("ai_parse_mode", "AI 模式"))
        st.json(parsed_result)
        if st.button("确认执行", key="confirm_ai_change"):
            try:
                station, selected_model, target_capacity = choose_model_for_ai(
                    st.session_state["arm_database"],
                    parsed_result,
                    list(st.session_state["current_station_takts"]),
                )
                takt = float(selected_model["节拍秒数"])
                if takt.is_integer():
                    takt = int(takt)
                st.session_state["ai_pending_apply"] = {
                    "station": station,
                    "model": str(selected_model["机型"]),
                    "takt": takt,
                    "target_capacity": target_capacity,
                }
                st.session_state["ai_parsed_result"] = None
                st.rerun()
            except ValueError as error:
                st.warning(str(error))
            except Exception as error:
                st.error(f"无法执行该方案：{error}")
else:
    st.session_state["ai_parsed_result"] = None
    st.session_state["ai_parse_mode"] = None

if "ai_apply_notice" in st.session_state:
    st.success(st.session_state.pop("ai_apply_notice"))

if uploaded_database is not None:
    try:
        imported_database = load_arm_database(uploaded_database)
        st.session_state["arm_database"] = imported_database
        st.session_state["arm_database_name"] = uploaded_database.name
        st.session_state["arm_database_is_builtin"] = False
        st.success(f"已导入 {len(imported_database)} 条机械臂数据，后续候选机型将使用此数据库。")
    except (ValueError, ImportError) as error:
        st.error(f"机械臂数据库导入失败：{error}")

MODEL_LIBRARY = st.session_state.get("arm_database")
if MODEL_LIBRARY is None or not hasattr(MODEL_LIBRARY, "empty"):
    MODEL_LIBRARY = pd.DataFrame(columns=required_arm_columns)
    st.session_state["arm_database"] = MODEL_LIBRARY
if getattr(MODEL_LIBRARY, "empty", False):
    st.session_state["arm_database"] = MODEL_LIBRARY.copy()

st.caption(
    f"当前机械臂数据：{st.session_state.get('arm_database_name', '未命名')}（{len(MODEL_LIBRARY)} 条）"
)

st.divider()

# 主体分为左侧候选机型和右侧节拍图表
candidate_col, chart_col = st.columns([1, 2.4], gap="large")

with candidate_col:
    st.subheader("候选机械臂")

    if MODEL_LIBRARY.empty:
        st.info("当前机械臂库为空，导入 CSV 或确保默认数据已加载后再继续编辑。")
        model_options = []
    else:
        model_options = MODEL_LIBRARY["机型"].dropna().astype(str).drop_duplicates().tolist()
    if model_options and st.session_state.get("new_station_model") not in model_options:
        st.session_state.pop("new_station_model", None)

    with st.expander("产线结构自定义", expanded=True):
        with st.form("add_station_form"):
            new_station_name = st.text_input("新工位名称", key="new_station_name")
            insert_position = st.selectbox(
                "插入位置",
                list(insert_position_indices),
                key="new_station_position",
            )
            if model_options:
                new_station_model = st.selectbox(
                    "初始机型",
                    model_options,
                    key="new_station_model",
                )
            else:
                new_station_model = None
                st.info("机械臂数据库中暂无可选机型。")
            add_station_submitted = st.form_submit_button(
                "添加工位",
                disabled=not model_options,
            )

        if add_station_submitted:
            name = new_station_name.strip()
            existing_names = {item["name"] for item in st.session_state["production_line"]}
            if not name:
                st.warning("请输入新工位名称。")
            elif name in existing_names:
                st.warning(f"工位“{name}”已存在。")
            else:
                model_rows = MODEL_LIBRARY[MODEL_LIBRARY["机型"].astype(str) == new_station_model]
                initial_model = model_rows.iloc[0]
                initial_takt = float(initial_model["节拍秒数"])
                if initial_takt.is_integer():
                    initial_takt = int(initial_takt)
                st.session_state["line_pending_add"] = {
                    "name": name,
                    "model": new_station_model,
                    "takt": initial_takt,
                    "index": insert_position_indices[insert_position],
                }
                st.rerun()

        if st.session_state["production_line"]:
            with st.form("delete_station_form"):
                station_to_delete = st.selectbox(
                    "选择要删除的工位",
                    [item["name"] for item in st.session_state["production_line"]],
                    key="delete_station",
                )
                delete_station_submitted = st.form_submit_button("删除工位")
            if delete_station_submitted:
                st.session_state["line_pending_delete"] = station_to_delete
                st.rerun()
        else:
            st.info("当前产线没有工位，可先添加一个工位。")

    if "line_edit_notice" in st.session_state:
        st.success(st.session_state.pop("line_edit_notice"))

    if st.session_state["production_line"]:
        selected_ws = st.session_state.get("selected_ws") or next(iter(st.session_state["current_station_takts"]), None)
        st.caption(f"当前待替换工位：{selected_ws or '未选中'}")
        line_station_options = list(st.session_state["current_station_takts"])
        if st.session_state.get("arm_recommend_station") not in line_station_options:
            st.session_state["arm_recommend_station"] = selected_ws

        with st.form("arm_filter_form"):
            target_station = st.selectbox(
                "目标工位",
                line_station_options,
                index=line_station_options.index(selected_ws) if selected_ws in line_station_options else 0,
                key="arm_recommend_station",
            )
            process_type = st.selectbox(
                "第1级：功能大类",
                ["全部", *ARM_PROCESS_TYPES],
                index=0,
                key="arm_filter_process_type",
            )
            available_brands = build_arm_brand_options(MODEL_LIBRARY, process_type)
            brand_scope = st.selectbox(
                "第2级：品牌/产地",
                available_brands,
                index=0,
                key="arm_filter_brand_scope",
            )

            radius_min = st.number_input(
                "臂展半径不低于（mm）",
                min_value=0,
                value=500,
                step=50,
                key="arm_filter_radius_min",
            )
            payload_min = st.number_input(
                "承重不低于（kg）",
                min_value=0,
                value=3,
                step=1,
                key="arm_filter_payload_min",
            )
            precision_limit = st.number_input(
                "精度不低于（mm）",
                min_value=0.0,
                value=0.05,
                step=0.01,
                format="%.3f",
                key="arm_filter_precision_limit",
            )
            require_vision = st.checkbox("需要视觉功能", key="arm_filter_vision")
            scenario = st.text_input(
                "应用场景 / 补充要求（供 AI 推荐参考）",
                placeholder="例如：机加工上下料，工件较重，希望缩短节拍",
                key="arm_recommend_scenario",
            )
            filter_submitted = st.form_submit_button("筛选候选机械臂")
            recommend_submitted = st.form_submit_button("🤖 AI 智能推荐", type="primary")

        if filter_submitted or recommend_submitted:
            st.session_state["arm_filter_conditions"] = {
                "station": target_station,
                "process_type": process_type,
                "brand_scope": brand_scope,
                "radius_min": radius_min,
                "payload_min": payload_min,
                "precision_limit": precision_limit,
                "require_vision": require_vision,
            }
            st.session_state["arm_filter_submitted"] = True
            if filter_submitted:
                st.session_state.pop("arm_recommendation", None)

        if not st.session_state.get("arm_filter_submitted"):
            st.info("按第1级～第3级条件筛选后，点击“筛选候选机械臂”。")
        else:
            conditions = st.session_state["arm_filter_conditions"]
            selected_ws = conditions.get("station", selected_ws)
            filtered_models = filter_arm_candidates(
                MODEL_LIBRARY,
                process_type=conditions.get("process_type", "全部"),
                brand_scope=conditions.get("brand_scope", "全部"),
                radius_min=float(conditions.get("radius_min", 0) or 0),
                payload_min=float(conditions.get("payload_min", 0) or 0),
                precision_limit=float(conditions.get("precision_limit", 5.0) or 5.0),
                require_vision=bool(conditions.get("require_vision", False)),
            )

            if filtered_models.empty:
                st.info("没有符合条件的机械臂，系统已回退到同工序可用候选并继续展示。")
                filtered_models = filter_arm_candidates(
                    MODEL_LIBRARY,
                    process_type="全部",
                    brand_scope="全部",
                    radius_min=0,
                    payload_min=0,
                    precision_limit=99,
                    require_vision=False,
                )

            if recommend_submitted:
                api_key = str(
                    st.session_state.get("manual_api_key") or safe_get_secret("DEEPSEEK_API_KEY") or ""
                ).strip()
                recommended_model, recommendation_reason, recommendation_source = recommend_arm_model(
                    filtered_models,
                    scenario,
                    selected_ws,
                    {
                        **conditions,
                        "补充要求": scenario,
                    },
                    api_key,
                )
                if recommended_model is not None:
                    st.session_state["arm_recommendation"] = {
                        "model": recommended_model,
                        "reason": recommendation_reason,
                        "source": recommendation_source,
                        "station": selected_ws,
                    }

            current_model = st.session_state["current_station_models"].get(selected_ws, "未配置")
            if selected_ws:
                st.caption(f"当前选中工位：{selected_ws} · 当前采用：{current_model}")

            if filtered_models.empty:
                st.warning("当前机械臂库中没有可用候选，建议先增加更宽松的参数或导入更多机型。")
            else:
                with st.container(height=400):
                    for row_index, model in filtered_models.iterrows():
                        model_name = str(model.get("机型", model.get("品牌名称", "未知机型")))
                        brand_name = str(model.get("品牌名称", model.get("机型", "未知机型")))
                        origin_name = str(model.get("品牌产地", model.get("产地", "未知")))
                        process_name = str(model.get("工序类型", "-"))
                        radius_value = normalize_numeric(model.get("臂展半径", 0))
                        payload_value = normalize_numeric(model.get("承重(kg)", 0))
                        precision_value = normalize_numeric(model.get("精度(mm)", model.get("精度", 0)))
                        vision_supported = normalize_bool(model.get("是否支持视觉", False))
                        card_title = model_name if brand_name in model_name else f"{brand_name} {model_name}"
                        with st.expander(card_title, expanded=False):
                            st.caption(f"产地：{origin_name}　|　功能：{process_name}")
                            parameter_col_left, parameter_col_right = st.columns(2)
                            with parameter_col_left:
                                st.write(f"**负载：** {payload_value:g} kg")
                                st.write(f"**工作半径：** {radius_value:g} mm")
                                st.write(f"**重复定位精度：** ±{precision_value:g} mm")
                                st.write(f"**IP 防护：** {model.get('IP防护', 'IP65')}")
                            with parameter_col_right:
                                st.write(f"**运行速度：** {normalize_numeric(model.get('运行速度', 0)):g} °/s")
                                st.write(f"**通讯接口：** {model.get('通讯接口', '未注明')}")
                                st.write(f"**耐用性：** {model.get('耐用性', '未注明')}")
                                st.write(f"**视觉功能：** {'支持' if vision_supported else '不支持'}")
                            st.write(
                                f"节拍：{normalize_numeric(model.get('节拍秒数', 20)):g} 秒　|　"
                                f"维保：{model.get('维保响应', '24小时')}　|　价格：{model.get('价格', '未注明')}"
                            )
                            st.success(f"🟢 优势（Pros）：{model.get('Pros', '参数配置均衡')}")
                            st.error(f"🔴 不足（Cons）：{model.get('Cons', '需结合现场工况校核')}")
                            if st.button(
                                "采用此机型",
                                key=f"use_filtered_{selected_ws}_{row_index}_{model_name}",
                                use_container_width=True,
                            ):
                                if selected_ws and apply_model_to_station(model, selected_ws):
                                    st.rerun()
                                else:
                                    st.warning("当前没有有效的工位可替换，请先在拓扑图中选择工位。")

            recommendation = st.session_state.get("arm_recommendation")
            if recommendation and recommendation.get("station") == selected_ws:
                recommended_model = recommendation["model"]
                st.markdown("#### AI 智能推荐结果")
                st.success(
                    f"{recommendation['source']}：推荐 {recommended_model.get('机型', '未知机型')}"
                )
                st.write(recommendation["reason"])
                st.caption(
                    f"特点：{recommended_model.get('核心特点', '未注明')}　|　"
                    f"局限：{recommended_model.get('瓶颈局限性', '需结合现场工况校核')}"
                )
                if "未配置 API Key" in recommendation["source"]:
                    st.info("已使用本地规则为您推荐。")
                if st.button("采用推荐机型", key=f"apply_ai_recommendation_{selected_ws}", type="primary"):
                    if apply_model_to_station(recommended_model, selected_ws):
                        st.session_state.pop("arm_recommendation", None)
                        st.rerun()

with chart_col:
    cycle_times = st.session_state["current_station_takts"]
    st.subheader("产线拓扑图")
    if not cycle_times:
        st.info("当前产线没有工位，请先添加工位。")
        st.subheader("整线节拍与瓶颈")
        st.info("添加工位后将显示节拍、瓶颈和估算产能。")
    else:
        bottleneck, bottleneck_takt = calc_line_takt(cycle_times)
        if "selected_ws" not in st.session_state or st.session_state["selected_ws"] not in cycle_times:
            st.session_state["selected_ws"] = next(iter(cycle_times), None)

        st.metric("估算整线产能（件/小时）", f"{3600 / bottleneck_takt:.1f}")
        topology_stations = list(cycle_times.items())
        topology_spacing = 2.4
        topology_node_size = 96
        topology_figure = go.Figure()

        for index in range(len(topology_stations) - 1):
            current_x = index * topology_spacing
            next_x = (index + 1) * topology_spacing
            topology_figure.add_annotation(
                x=next_x - 0.9,
                y=0.5,
                ax=current_x + 0.9,
                ay=0.5,
                xref="x",
                yref="y",
                axref="x",
                ayref="y",
                text="",
                showarrow=True,
                arrowhead=2,
                arrowsize=1,
                arrowwidth=2,
            )

        for index, (station, takt) in enumerate(topology_stations):
            center_x = index * topology_spacing
            if takt == bottleneck_takt:
                node_color = "#d95d4f"
            elif takt < bottleneck_takt * 0.8:
                node_color = "#39856a"
            else:
                node_color = "#e8bd45"

            topology_figure.add_trace(
                go.Scatter(
                    x=[center_x],
                    y=[0.5],
                    mode="markers+text",
                    customdata=[str(station)],
                    text=[str(station)],
                    textposition="middle center",
                    textfont={"size": 14, "color": "#000000"},
                    marker={
                        "symbol": "square",
                        "size": topology_node_size,
                        "color": node_color,
                        "line": {"color": "rgba(0,0,0,0.35)", "width": 2},
                    },
                    hovertemplate="%{customdata}<extra></extra>",
                    showlegend=False,
                    cliponaxis=False,
                )
            )

        topology_figure.update_layout(
            height=190,
            margin={"l": 12, "r": 12, "t": 12, "b": 12},
            template="streamlit",
            showlegend=False,
            dragmode=False,
            xaxis={
                "visible": False,
                "range": [-1.1, (len(topology_stations) - 1) * topology_spacing + 1.1],
            },
            yaxis={
                "visible": False,
                "range": [0, 1],
                "fixedrange": True,
                "showgrid": False,
            },
        )
        chart_key = "topology_chart"
        chart_event = st.session_state.get(chart_key)
        if isinstance(chart_event, dict):
            selected_station = extract_selected_station_from_event(chart_event)
            if selected_station and selected_station in cycle_times:
                st.session_state["selected_ws"] = selected_station

        st.plotly_chart(
            topology_figure,
            key=chart_key,
            use_container_width=True,
            on_select="rerun",
            selection_mode="points",
            config={"displayModeBar": False, "scrollZoom": False},
        )

        station_columns = st.columns(min(len(topology_stations), 5))
        for idx, (station, _) in enumerate(topology_stations):
            with station_columns[idx % len(station_columns)]:
                if st.button(station, key=f"station_button_{station}", use_container_width=True):
                    st.session_state["selected_ws"] = station
                    st.rerun()

        selected_ws = st.session_state.get("selected_ws")
        if selected_ws and selected_ws in cycle_times:
            selected_station_models = get_station_candidate_models(MODEL_LIBRARY, selected_ws)
            with st.container():
                st.caption(f"当前选中工位：{selected_ws}")
                if selected_station_models.empty:
                    st.warning(f"当前工位“{selected_ws}”没有可用机械臂数据，已回退到全库候选。")
                    selected_station_models = MODEL_LIBRARY.copy()

                model_options = (
                    selected_station_models["机型"].dropna().astype(str).drop_duplicates().tolist()
                )
                if not model_options:
                    model_options = ["无可用机型"]

                current_model = st.session_state["current_station_models"].get(selected_ws, "未配置")
                default_index = model_options.index(current_model) if current_model in model_options else 0
                with st.form(f"replace_arm_form_{selected_ws}"):
                    replacement_model = st.selectbox(
                        "更换机械臂",
                        model_options,
                        index=default_index,
                        key=f"replacement_model_{selected_ws}",
                    )
                    submitted = st.form_submit_button(
                        "确认替换",
                        disabled=(replacement_model == "无可用机型"),
                    )
                if submitted and replacement_model != "无可用机型":
                    selected_row = selected_station_models[
                        selected_station_models["机型"].astype(str) == replacement_model
                    ].iloc[0]
                    target_station = next(
                        item for item in st.session_state["production_line"]
                        if item["name"] == selected_ws
                    )
                    takt_value = float(selected_row["节拍秒数"])
                    if takt_value.is_integer():
                        takt_value = int(takt_value)
                    target_station["model"] = replacement_model
                    target_station["takt"] = takt_value
                    sync_line_state()
                    calc_line_takt(st.session_state["current_station_takts"])
                    st.rerun()

        st.subheader("整线节拍与瓶颈")

        # 根据当前工位节拍重算瓶颈，并用红色突出显示
        bar_colors = [
            "#d95d4f" if operation == bottleneck else "#39856a"
            for operation in cycle_times
        ]

        figure = go.Figure(
            data=[
                go.Bar(
                    x=list(cycle_times.keys()),
                    y=list(cycle_times.values()),
                    marker_color=bar_colors,
                    text=list(cycle_times.values()),
                    textposition="outside",
                    hovertemplate="%{x}<br>节拍：%{y} 秒<extra></extra>",
                )
            ]
        )
        figure.update_layout(
            height=420,
            margin={"l": 20, "r": 20, "t": 28, "b": 20},
            template="streamlit",
            showlegend=False,
            xaxis={
                "title": {"text": "工序"},
                "showgrid": False,
            },
            yaxis={
                "showgrid": True,
                "gridcolor": "rgba(128,128,128,0.3)",
                "gridwidth": 1,
                "title": {"text": "节拍（秒)"},
            },
        )
        st.plotly_chart(
            figure,
            width="stretch",
            config={"displayModeBar": False, "staticPlot": True, "editable": False, "scrollZoom": False},
        )
        st.warning(f"当前瓶颈：{bottleneck} {bottleneck_takt} 秒")
