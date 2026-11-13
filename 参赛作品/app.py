import hashlib
import html
import io
import json
import re
import textwrap
import traceback

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from streamlit.errors import StreamlitSecretNotFoundError


def parse_first_number(val):
    if pd.isna(val):
        return None
    match = re.search(r"[-+]?\d*\.?\d+", str(val))
    return float(match.group()) if match else None


def clean_arm_database_column_names(database):
    database = database.copy()
    database.columns = (
        database.columns.astype(str)
        .str.strip()
        .str.replace(r"[\u200b\uFEFF\r\n\t]+", "", regex=True)
        .str.strip()
    )
    return database.loc[:, ~database.columns.duplicated(keep="first")].copy()


def clean_arm_text(value, default=""):
    if value is None or pd.isna(value):
        return default
    return re.sub(r"[\u200b\uFEFF\r\n\t]+", "", str(value)).strip()


st.set_page_config(
    page_title="智能线搭子",
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
CUSTOM_TEMPLATE_OPTION = "➕ 自定义新模板..."


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


def format_display_number(value, digits=1):
    """统一节拍/瓶颈/产能等数值的展示格式，先四舍五入再渲染，避免浮点误差。"""
    number = normalize_numeric(value, default=0.0)
    rounded = round(number, digits)
    if rounded == 0:
        rounded = 0.0  # 把 -0.0 统一为 0
    return f"{rounded:g}"


def _numeric_text(value):
    return "" if value is None else str(value).strip().lower()


def parse_price_to_yuan(value):
    """把“30万 / ¥150,000 / 150000元”等价格统一转换为元。"""
    amount = normalize_numeric(value, default=float("nan"))
    if pd.isna(amount):
        return float("nan")
    text = _numeric_text(value)
    if "万" in text:
        return amount * 10000
    if "千" in text:
        return amount * 1000
    return amount


def parse_precision_to_mm(value):
    """把“±0.02 mm / 0.02um”等精度统一转换为毫米。"""
    amount = normalize_numeric(value, default=float("nan"))
    if pd.isna(amount):
        return float("nan")
    text = _numeric_text(value)
    if "μm" in text or "um" in text or "微米" in text:
        return amount / 1000
    if "cm" in text:
        return amount * 10
    return amount


def parse_reach_to_mm(value):
    """把“1.2m / 900mm”等臂展统一转换为毫米。"""
    amount = normalize_numeric(value, default=float("nan"))
    if pd.isna(amount):
        return float("nan")
    text = _numeric_text(value)
    if re.search(r"\d\s*m(?![m])", text):
        return amount * 1000
    return amount


def parse_takt_to_seconds(value):
    """把“20s / 0.5min”等节拍统一转换为秒。"""
    amount = normalize_numeric(value, default=float("nan"))
    if pd.isna(amount):
        return float("nan")
    text = _numeric_text(value)
    if "min" in text or "分钟" in text:
        return amount * 60
    return amount


def ensure_arm_database_columns(database):
    if database is None:
        return pd.DataFrame(
            columns=[
                "工位", "机型", "产地", "品牌产地", "品牌名称", "工序类型",
                "臂展半径", "承重(kg)", "精度", "精度(mm)", "是否支持视觉",
                "IP防护", "运行速度", "运行速度(m/s)", "通讯接口", "耐用性",
                "核心特点", "瓶颈局限性", "Pros", "Cons", "价格", "维保响应",
                "节拍秒数", "占地估算(㎡)", "成本(万元)",
            ]
        )

    database = clean_arm_database_column_names(database)
    column_aliases = {
        "代表型号": "机型",
        "国家": "产地",
        "系列": "品牌名称",
        "重复定位精度": "精度",
        "负载": "承重(kg)",
        "承重": "承重(kg)",
        "防护等级": "IP防护",
        "运行速度（m/s）": "运行速度(m/s)",
        "运行速度 m/s": "运行速度(m/s)",
        "运行速度（%）": "运行速度(%)",
        "运行速度 %": "运行速度(%)",
    }
    for column in list(database.columns):
        target = column_aliases.get(column)
        if target is None and "精度" in column and column not in {"精度", "精度(mm)"}:
            target = "精度"
        if target is None:
            continue
        if target in database.columns:
            target_values = database[target]
            source_values = database[column]
            missing_values = target_values.isna() | target_values.astype(str).str.strip().eq("")
            database[target] = target_values.where(~missing_values, source_values)
            database = database.drop(columns=column)
        else:
            database = database.rename(columns={column: target})

    if "工位" not in database.columns:
        database["工位"] = "未知工位"
    if "机型" not in database.columns:
        database["机型"] = "未知机型"
    if "产地" not in database.columns:
        database["产地"] = database.get("品牌产地", "未知")
    if "品牌产地" not in database.columns:
        database["品牌产地"] = database["产地"].fillna("未知")
    if "品牌名称" not in database.columns:
        database["品牌名称"] = ""
    if "工序类型" not in database.columns:
        database["工序类型"] = database["工位"].map(infer_arm_process_type)
    if "臂展半径" not in database.columns:
        database["臂展半径"] = 800.0
    if "承重(kg)" not in database.columns:
        database["承重(kg)"] = 10.0
    if "精度" not in database.columns:
        database["精度"] = database.get("精度(mm)", 0.05)
    if "精度(mm)" not in database.columns:
        database["精度(mm)"] = database["精度"].map(parse_first_number).fillna(0.05)
    if "是否支持视觉" not in database.columns:
        database["是否支持视觉"] = False
    if "IP防护" not in database.columns:
        database["IP防护"] = None
    if "运行速度" not in database.columns:
        database["运行速度"] = None
    if "运行速度(m/s)" not in database.columns and "运行速度(%)" not in database.columns:
        database["运行速度(m/s)"] = 1.0
    for column, default_speed in (("运行速度(m/s)", 1.0), ("运行速度(%)", 100.0)):
        if column in database.columns:
            database[column] = pd.to_numeric(
                database[column].map(
                    lambda value: normalize_numeric(value, default=float("nan"))
                ),
                errors="coerce",
            ).fillna(default_speed)
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
    if "价格" not in database.columns:
        database["价格"] = 0
    if "维保响应" not in database.columns:
        database["维保响应"] = "24小时"
    if "节拍秒数" not in database.columns:
        database["节拍秒数"] = 20

    database["工位"] = database["工位"].fillna("").astype(str).str.strip().replace("", "未知工位")
    database["机型"] = database["机型"].map(
        lambda value: clean_arm_text(value, "未知机型") or "未知机型"
    )
    database["品牌名称"] = database["品牌名称"].map(clean_arm_text)
    database["品牌产地"] = database["品牌产地"].map(clean_arm_text)
    database["产地"] = database["产地"].map(clean_arm_text)
    database["品牌产地"] = database["品牌产地"].where(
        database["品牌产地"].ne(""), database["产地"]
    )
    database["产地"] = database["产地"].where(
        database["产地"].ne(""), database["品牌产地"]
    )
    database["工序类型"] = database["工序类型"].fillna("装配").astype(str).str.strip()
    parsed_reach = pd.to_numeric(
        database["臂展半径"].map(parse_reach_to_mm), errors="coerce"
    )
    if "_臂展有效" not in database.columns:
        database["_臂展有效"] = parsed_reach.gt(0).fillna(False)
    database["臂展半径"] = parsed_reach.fillna(800.0)
    database["占地估算(㎡)"] = (database["臂展半径"] / 1000) ** 2 * 3.14
    database["承重(kg)"] = pd.to_numeric(database["承重(kg)"], errors="coerce").fillna(10.0)
    database["精度"] = database["精度"].where(
        database["精度"].notna() & database["精度"].astype(str).str.strip().ne(""),
        database["精度(mm)"],
    )
    parsed_precision = pd.to_numeric(
        database["精度(mm)"].map(parse_precision_to_mm), errors="coerce"
    )
    parsed_precision_fallback = pd.to_numeric(
        database["精度"].map(parse_precision_to_mm), errors="coerce"
    )
    if "_精度有效" not in database.columns:
        database["_精度有效"] = (
            parsed_precision.gt(0).fillna(False)
            | parsed_precision_fallback.gt(0).fillna(False)
        )
    database["精度(mm)"] = parsed_precision.fillna(
        parsed_precision_fallback.fillna(0.05)
    )
    database["是否支持视觉"] = database["是否支持视觉"].map(normalize_bool).fillna(False)
    database["IP防护"] = database["IP防护"].fillna("").astype(str).str.strip().replace("", "IP65")
    database["运行速度"] = pd.to_numeric(database["运行速度"].map(normalize_numeric), errors="coerce").fillna(
        database["承重(kg)"].map(lambda load: 180 if load <= 10 else 120)
    )
    database["通讯接口"] = database["通讯接口"].fillna("").astype(str).str.strip().replace("", "EtherNet/IP、Profinet")
    database["耐用性"] = database["耐用性"].fillna("").astype(str).str.strip().replace("", "MTBF 80,000小时")
    database["核心特点"] = database["核心特点"].fillna("").astype(str)
    database["瓶颈局限性"] = database["瓶颈局限性"].fillna("").astype(str)
    parsed_price = pd.to_numeric(
        database["价格"].map(parse_price_to_yuan), errors="coerce"
    )
    if "_价格有效" not in database.columns:
        database["_价格有效"] = parsed_price.gt(0).fillna(False)
    database["价格"] = parsed_price.fillna(0)
    database["成本(万元)"] = database["价格"] / 10000
    database["维保响应"] = database["维保响应"].where(
        database["维保响应"].notna() & database["维保响应"].astype(str).str.strip().ne(""),
        "24小时",
    ).astype(str)

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
        if normalize_numeric(row["IP防护"]) >= 67:
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
    parsed_takt = pd.to_numeric(
        database["节拍秒数"].map(parse_takt_to_seconds), errors="coerce"
    )
    if "_节拍有效" not in database.columns:
        database["_节拍有效"] = parsed_takt.gt(0).fillna(False)
    database["节拍秒数"] = parsed_takt.where(parsed_takt > 0).fillna(20)

    database["Pros"] = database["Pros"].fillna("").astype(str)
    database["Cons"] = database["Cons"].fillna("").astype(str)

    def describe_pros(row):
        advantages = [item.strip() for item in str(row["核心特点"]).split("；") if item.strip()]
        if normalize_numeric(row["IP防护"]) >= 67:
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
    filtered = ensure_arm_database_columns(database)
    if process_type != "全部":
        filtered = filtered[filtered["工序类型"].fillna("").astype(str).str.contains(process_type, na=False)]
    if filtered.empty:
        return ["全部", "国产", "进口"]
    brands = sorted(
        {
            clean_arm_text(value)
            for value in filtered["品牌名称"]
            if clean_arm_text(value)
        }
    )
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
            candidates["品牌名称"].astype(str).str.contains(brand_key, na=False)
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
    if "initial_production_line" not in st.session_state:
        st.session_state["initial_production_line"] = snapshot_production_line()
    model_name = str(model_row.get("机型", model_row.get("品牌名称", "未知机型")))
    takt_value = float(model_row.get("节拍秒数", 20))
    if takt_value.is_integer():
        takt_value = int(takt_value)
    station_item["model"] = model_name
    station_item["takt"] = takt_value
    # 新机型自带真实价格/占地/精度，清除旧的工位级缩放覆盖
    for override_key in ("price", "reach", "precision"):
        station_item.pop(override_key, None)
    # 该工位机型被手动/AI 单点更换后，重置它的全局优化标记
    station_flags = st.session_state.get("station_optimization_flags")
    if isinstance(station_flags, dict):
        station_flags.pop(station_name, None)
    sync_line_state()
    st.session_state["optimization_applied"] = True
    return True


GLOBAL_OPTIMIZATION_OPERATIONS = {
    "全局提速": {
        "key": "speed_up",
        "metric": "节拍秒数",
        "prefer": "min",
        "label": "速度",
        "success_message": "✅ 已成功为您将全线更换为高速机型。",
        "repeat_message": "当前产线已完成全线提速，请勿重复执行。",
    },
    "全局降速": {
        "key": "speed_down",
        "metric": "节拍秒数",
        "prefer": "max",
        "label": "速度",
        "success_message": "✅ 已成功为您将全线更换为低速机型。",
        "repeat_message": "当前产线已完成全线降速，请勿重复执行。",
    },
    "全局提质": {
        "key": "quality_up",
        "metric": "精度(mm)",
        "prefer": "min",
        "label": "精度",
        "success_message": "✅ 已成功为您将全线更换为高精度机型。",
        "repeat_message": "当前产线已完成全线提质，请勿重复执行。",
    },
    "全局降质": {
        "key": "quality_down",
        "metric": "精度(mm)",
        "prefer": "max",
        "label": "精度",
        "success_message": "✅ 已成功为您将全线更换为低精度机型。",
        "repeat_message": "当前产线已完成全线降质，请勿重复执行。",
    },
    "全局降本": {
        "key": "cost_down",
        "metric": "价格",
        "prefer": "min",
        "label": "成本",
        "success_message": "✅ 已成功为您将全线更换为低成本机型。",
        "repeat_message": "当前产线已完成全线降本，请勿重复执行。",
    },
    "全局提价": {
        "key": "cost_up",
        "metric": "价格",
        "prefer": "max",
        "label": "成本",
        "success_message": "✅ 已成功为您将全线更换为高成本机型。",
        "repeat_message": "当前产线已完成全线提价，请勿重复执行。",
    },
    "全局省地": {
        "key": "space_down",
        "metric": "臂展半径",
        "prefer": "min",
        "label": "占地",
        "success_message": "✅ 已成功为您将全线更换为紧凑型机型。",
        "repeat_message": "当前产线已完成全线省地，请勿重复执行。",
    },
    "全局增地": {
        "key": "space_up",
        "metric": "臂展半径",
        "prefer": "max",
        "label": "占地",
        "success_message": "✅ 已成功为您将全线更换为大空间机型。",
        "repeat_message": "当前产线已完成全线增地，请勿重复执行。",
    },
}


METRIC_VALIDITY_COLUMNS = {
    "节拍秒数": "_节拍有效",
    "精度(mm)": "_精度有效",
    "价格": "_价格有效",
    "臂展半径": "_臂展有效",
}


# 同一维度内先判断“降低/负向”词，再判断“提高/正向”词，避免语义误判
GLOBAL_OPERATION_PATTERNS = {
    "全局降速": (
        r"(速度|节拍).{0,8}(降低|下降|变慢|减慢|放慢|调慢|减少|延长|变长)",
        r"(降低|减低|下降|减慢|放慢|调慢|减少|延长).{0,8}(速度|节拍)",
        r"降速|减速|变慢|放慢|调慢",
    ),
    "全局提速": (
        r"(速度|节拍).{0,8}(提高|提升|加快|变快|调快|加速|增加|缩短|变短)",
        r"(提高|提升|加快|变快|调快|加速|缩短).{0,8}(速度|节拍)",
        r"提速|加快|变快|加速|调快",
    ),
    "全局降质": (
        r"(质量|品质|精度).{0,8}(降低|下降|变差|减少|低)",
        r"(降低|下降|减少).{0,8}(质量|品质|精度)",
        r"降质|不要精度|精度变差|降低精度",
    ),
    "全局提质": (
        r"(质量|品质|精度).{0,8}(提高|提升|变好|高|好)",
        r"(提高|提升).{0,8}(质量|品质|精度)",
        r"提质|高精度|提高质量|提高精度",
    ),
    "全局降本": (
        r"(成本|价格).{0,8}(降低|下降|减少|低|便宜|省)",
        r"(降低|下降|减少|省).{0,8}(成本|价格)",
        r"降本|省钱|降价|降低成本",
    ),
    "全局提价": (
        r"(成本|价格).{0,8}(增加|提高|提升|上涨|涨|高|贵)",
        r"(增加|提高|提升).{0,8}(成本|价格)",
        r"提价|涨价|增加成本",
    ),
    "全局省地": (
        r"(占地|空间).{0,8}(缩小|减小|减少|降低|小|紧凑)",
        r"(缩小|减小|减少|降低).{0,8}(占地|空间)",
        r"省地|减小占地|减少空间",
    ),
    "全局增地": (
        r"(占地|空间).{0,8}(变大|增大|增加|扩大|大)",
        r"(增加|增大|扩大).{0,8}(占地|空间)",
        r"增地|占地变大|增加空间|扩大空间",
    ),
}

GLOBAL_DIMENSION_ORDER = (
    ("全局降速", "全局提速"),
    ("全局降质", "全局提质"),
    ("全局降本", "全局提价"),
    ("全局省地", "全局增地"),
)

_GLOBAL_CLAUSE_SPLIT_PATTERN = re.compile(
    r"并且|而且|同时|还要|以及|并|且|[，,；;。、]|\s+"
)


def _clause_matches_operation(clause, operation):
    if operation in clause:
        return True
    return any(
        re.search(pattern, clause)
        for pattern in GLOBAL_OPERATION_PATTERNS[operation]
    )


def detect_global_operations(text):
    """从自然语言中提取全局指令，同一维度只保留一个方向。

    先按标点/连接词拆分短句，再逐维度匹配，优先识别“降低”类语义，
    避免“提高速度并降低成本”这类复合句中的方向串扰。
    """
    clauses = [
        clause
        for clause in _GLOBAL_CLAUSE_SPLIT_PATTERN.split(str(text or ""))
        if clause.strip()
    ]
    operations = []
    for down_operation, up_operation in GLOBAL_DIMENSION_ORDER:
        matched = None
        for clause in clauses:
            if _clause_matches_operation(clause, down_operation):
                matched = down_operation
                break
        if matched is None:
            for clause in clauses:
                if _clause_matches_operation(clause, up_operation):
                    matched = up_operation
                    break
        if matched is not None:
            operations.append(matched)
    return operations


def _normalized_metric_scores(candidates, metric_columns, preferences):
    """按指标方向归一化打分，分数越高越优。"""
    total = pd.Series(0.0, index=candidates.index)
    for column in metric_columns:
        values = candidates[f"_{column}"]
        low = values.min()
        high = values.max()
        if high == low:
            normalized = pd.Series(1.0, index=candidates.index)
        elif preferences[column] == "max":
            normalized = (values - low) / (high - low)
        else:
            normalized = (high - values) / (high - low)
        total += normalized
    return total / max(len(metric_columns), 1)


def _select_compound_replacement(pool, current_values, operations):
    """在给定的同品牌/同类型候选池中选择复合最优机型。

    返回 ``(replacement_row, 是否发生冲突)``。找不到同时改善全部指标的
    机型时返回 ``None``，由调用方按比例缩放参数。
    """
    if pool is None or pool.empty:
        return None, True

    metric_columns = list(
        dict.fromkeys(
            GLOBAL_OPTIMIZATION_OPERATIONS[operation]["metric"]
            for operation in operations
        )
    )
    preferences = {
        GLOBAL_OPTIMIZATION_OPERATIONS[operation]["metric"]: (
            GLOBAL_OPTIMIZATION_OPERATIONS[operation]["prefer"]
        )
        for operation in operations
    }
    candidates = pool.copy()
    for column in metric_columns:
        validity_column = METRIC_VALIDITY_COLUMNS.get(column)
        if validity_column and validity_column in candidates.columns:
            candidates = candidates[
                candidates[validity_column].fillna(False)
            ]
    for column in metric_columns:
        candidates[f"_{column}"] = pd.to_numeric(
            candidates[column], errors="coerce"
        )
    candidates = candidates.dropna(
        subset=[f"_{column}" for column in metric_columns]
    )
    if candidates.empty:
        return None, True

    improves_all = pd.Series(True, index=candidates.index)
    for column in metric_columns:
        current_value = current_values.get(column, float("nan"))
        if pd.isna(current_value):
            continue
        if preferences[column] == "max":
            improves_all &= candidates[f"_{column}"] > current_value
        else:
            improves_all &= candidates[f"_{column}"] < current_value

    if not improves_all.any():
        return None, True

    good = candidates[improves_all].copy()
    good["_score"] = _normalized_metric_scores(
        good, metric_columns, preferences
    )
    return (
        good.sort_values("_score", ascending=False, kind="stable").iloc[0],
        False,
    )


GLOBAL_METRIC_OVERRIDE_KEYS = {
    "价格": "price",
    "臂展半径": "reach",
    "精度(mm)": "precision",
}


def _effective_item_metric(item, model_row, metric):
    """读取工位生效的指标值：优先使用工位级覆盖值，其次使用机型数据。"""
    override_key = GLOBAL_METRIC_OVERRIDE_KEYS.get(metric)
    if override_key and item.get(override_key) is not None:
        try:
            value = float(item[override_key])
            if not pd.isna(value) and value > 0:
                return value
        except (TypeError, ValueError):
            pass
    if metric == "节拍秒数":
        try:
            value = float(item.get("takt"))
            if not pd.isna(value) and value > 0:
                return value
        except (TypeError, ValueError):
            pass
    if model_row is not None:
        value = normalize_numeric(
            model_row.get(metric, float("nan")), default=float("nan")
        )
        if not pd.isna(value):
            return float(value)
    return float("nan")


def _set_effective_item_metric(item, metric, value):
    """把指标值写回工位；价格/占地/精度使用工位级覆盖，避免统一克隆。"""
    if pd.isna(value) or value <= 0:
        return
    if metric == "节拍秒数":
        item["takt"] = int(value) if float(value).is_integer() else float(value)
        return
    override_key = GLOBAL_METRIC_OVERRIDE_KEYS.get(metric)
    if override_key:
        item[override_key] = float(value)


def _clear_item_metric_overrides(item):
    for key in GLOBAL_METRIC_OVERRIDE_KEYS.values():
        item.pop(key, None)


def _station_candidate_pool(model_library, current_model, excluded_models):
    """同品牌优先、找不到同品牌时退回同工序类型。"""
    pool = model_library[
        ~model_library["机型"].astype(str).isin(excluded_models)
    ].copy()
    if current_model is None:
        return pool
    brand = str(current_model.get("品牌名称", "") or "").strip()
    process_type = str(current_model.get("工序类型", "") or "").strip()
    if brand:
        same_brand = pool[
            pool["品牌名称"].astype(str).str.strip() == brand
        ]
        if not same_brand.empty:
            return same_brand
    if process_type:
        same_type = pool[
            pool["工序类型"].astype(str).str.strip() == process_type
        ]
        if not same_type.empty:
            return same_type
    return model_library.iloc[0:0].copy()


def run_global_optimization(operations):
    """统一的全局替换寻优入口，支持单一指令或复合指令。

    ``operations`` 可以是字符串或字符串列表。返回
    ``(状态, 提示消息, 额外警告或 None)``；状态为
    ``"success"``（已替换）或 ``"warning"``（未找到匹配机型/无数据）。
    """
    if isinstance(operations, str):
        operations = [operations]
    operations = [
        operation
        for operation in operations
        if operation in GLOBAL_OPTIMIZATION_OPERATIONS
    ]
    operations = sorted(
        set(operations),
        key=lambda operation: list(GLOBAL_OPTIMIZATION_OPERATIONS).index(operation),
    )
    if not operations:
        return "warning", "未知的全局优化指令。", None

    global_cmd = "、".join(operations)
    production_line = st.session_state.get("production_line", [])
    if not production_line:
        return "warning", "当前产线没有可执行工位。", None
    if "initial_production_line" not in st.session_state:
        reset_optimization_baseline()
    initial_line = st.session_state["initial_production_line"]
    initial_takt = {
        item["name"]: normalize_numeric(item["takt"], default=float("nan"))
        for item in initial_line
        if "name" in item and "takt" in item
    }
    st.session_state["initial_takt"] = initial_takt
    missing_baselines = [
        item.get("name", "")
        for item in production_line
        if item.get("name") not in initial_takt
        or pd.isna(initial_takt.get(item.get("name")))
        or initial_takt.get(item.get("name")) <= 0
    ]
    if missing_baselines:
        return (
            "warning",
            "⚠️ 无法读取工位初始节拍，请先重置产线或重新选择行业模板。",
            None,
        )
    if st.session_state.get("global_cmd", "") == global_cmd:
        return "warning", "⚠️ 当前产线已是该状态，请勿重复操作。", None

    st.session_state["production_line"] = [
        dict(item) for item in initial_line
    ]
    st.session_state["global_cmd"] = ""
    sync_line_state()
    production_line = st.session_state["production_line"]

    database = st.session_state.get("arm_database")
    model_library = pd.DataFrame()
    known_model_names = set()
    if isinstance(database, pd.DataFrame) and not database.empty:
        model_library = ensure_arm_database_columns(database)
        if not model_library.empty:
            # 强制数值化：外部 CSV 可能包含 ±0.02mm、30万、1.2m 等格式
            for column, parser, default in (
                ("节拍秒数", parse_takt_to_seconds, 20.0),
                ("精度(mm)", parse_precision_to_mm, 0.05),
                ("价格", parse_price_to_yuan, 0.0),
                ("臂展半径", parse_reach_to_mm, 800.0),
            ):
                model_library[column] = pd.to_numeric(
                    model_library[column].map(parser), errors="coerce"
                ).fillna(default)
            model_library["占地估算(㎡)"] = (
                model_library["臂展半径"] / 1000
            ) ** 2 * 3.14
            model_library["成本(万元)"] = model_library["价格"] / 10000
            known_model_names = set(model_library["机型"].astype(str))

    is_compound = len(operations) > 1
    changed_count = 0
    conflict_count = 0

    # 当前已被占用的机型：避免多个工位被替换成完全相同的型号
    used_models = {
        str(item.get("model", "") or "").strip()
        for item in production_line
        if str(item.get("model", "") or "").strip()
        not in {"", "未配置", "无可用机型"}
    }

    def lookup_model(model_name):
        if model_library.empty or not model_name:
            return None
        rows = model_library[
            model_library["机型"].astype(str) == model_name
        ]
        return rows.iloc[0] if not rows.empty else None

    def usable_rows(pool):
        if pool.empty:
            return pool
        validity_columns = [
            column
            for column in ("_价格有效", "_臂展有效", "_节拍有效")
            if column in pool.columns
        ]
        if not validity_columns:
            return pool
        mask = pd.Series(True, index=pool.index)
        for column in validity_columns:
            mask &= pool[column].fillna(False)
        usable = pool[mask]
        return usable if not usable.empty else pool

    def pick_default_row(station_name):
        if model_library.empty:
            return None
        matched = usable_rows(
            model_library[
                model_library["工位"].astype(str).map(
                    lambda label: normalize_station_label(label)
                    == normalize_station_label(station_name)
                )
            ]
        )
        all_usable = usable_rows(model_library)
        for pool in (matched, all_usable):
            if pool.empty:
                continue
            unused = pool[~pool["机型"].astype(str).isin(used_models)]
            if not unused.empty:
                return unused.iloc[0]
        return all_usable.iloc[0]

    for item in production_line:
        station_changed = False
        model_name = str(item.get("model", "") or "").strip()
        is_unbound = model_name in {"", "未配置", "无可用机型"} or (
            bool(known_model_names) and model_name not in known_model_names
        )
        # 未绑定机械臂的工位分配一个未使用的默认机型，保证初始数据有差异
        if is_unbound and not model_library.empty:
            default_row = pick_default_row(str(item.get("name", "")).strip())
            if default_row is not None:
                model_name = str(default_row["机型"])
                item["model"] = model_name
                _clear_item_metric_overrides(item)
                default_takt = float(default_row["节拍秒数"])
                item["takt"] = (
                    int(default_takt)
                    if default_takt.is_integer()
                    else default_takt
                )
                used_models.add(model_name)
                station_changed = True

        current_model = lookup_model(model_name)
        replacement_row = None
        if not model_library.empty and current_model is not None:
            # 只在同品牌/同工序类型中寻找替代机型，且排除已被占用的型号
            pool = _station_candidate_pool(
                model_library,
                current_model,
                used_models | {model_name},
            )

            if is_compound:
                current_values = {}
                for operation in operations:
                    column = GLOBAL_OPTIMIZATION_OPERATIONS[operation]["metric"]
                    if column == "节拍秒数":
                        current_values[column] = initial_takt[item["name"]]
                    else:
                        current_values[column] = _effective_item_metric(
                            item, current_model, column
                        )
                replacement_row, has_conflict = _select_compound_replacement(
                    pool, current_values, operations
                )
                if has_conflict:
                    conflict_count += 1
            else:
                config = GLOBAL_OPTIMIZATION_OPERATIONS[operations[0]]
                metric_column = config["metric"]
                prefer = config["prefer"]
                if metric_column == "节拍秒数":
                    current_value = initial_takt[item["name"]]
                else:
                    current_value = _effective_item_metric(
                        item, current_model, metric_column
                    )
                candidates = pool
                validity_column = METRIC_VALIDITY_COLUMNS.get(metric_column)
                if (
                    validity_column
                    and validity_column in candidates.columns
                ):
                    candidates = candidates[
                        candidates[validity_column].fillna(False)
                    ]
                candidates["_metric"] = pd.to_numeric(
                    candidates[metric_column], errors="coerce"
                )
                candidates = candidates[candidates["_metric"].notna()]
                if not candidates.empty:
                    if pd.isna(current_value):
                        replacement_row = candidates.sort_values(
                            "_metric",
                            ascending=(prefer == "min"),
                            kind="stable",
                        ).iloc[0]
                    elif prefer == "min":
                        better = candidates[
                            candidates["_metric"] < current_value
                        ]
                        if not better.empty:
                            replacement_row = better.sort_values(
                                "_metric", ascending=True, kind="stable"
                            ).iloc[0]
                    else:
                        better = candidates[
                            candidates["_metric"] > current_value
                        ]
                        if not better.empty:
                            replacement_row = better.sort_values(
                                "_metric", ascending=False, kind="stable"
                            ).iloc[0]

        if replacement_row is not None:
            replacement_takt = float(replacement_row["节拍秒数"])
            item["model"] = str(replacement_row["机型"])
            item["takt"] = (
                int(replacement_takt)
                if replacement_takt.is_integer()
                else replacement_takt
            )
            _clear_item_metric_overrides(item)
            used_models.add(str(replacement_row["机型"]))
            station_changed = True
        elif not model_library.empty and current_model is not None:
            # 同品牌/同类型中没有合适替代机型：按比例缩放当前参数
            for operation in operations:
                config = GLOBAL_OPTIMIZATION_OPERATIONS[operation]
                metric_column = config["metric"]
                if metric_column == "节拍秒数":
                    current_value = initial_takt[item["name"]]
                else:
                    current_value = _effective_item_metric(
                        item, current_model, metric_column
                    )
                if pd.isna(current_value) or current_value <= 0:
                    continue
                factor = 0.8 if config["prefer"] == "min" else 1.2
                _set_effective_item_metric(
                    item, metric_column, current_value * factor
                )
                station_changed = True

        if station_changed:
            changed_count += 1

    # 最终差异化保障：成本/占地柱子不能全部雷同
    used_costs = set()
    used_areas = set()
    for item in production_line:
        model_name = str(item.get("model", "") or "").strip()
        model_row = lookup_model(model_name)
        price = _effective_item_metric(item, model_row, "价格")
        reach = _effective_item_metric(item, model_row, "臂展半径")

        if not pd.isna(price) and price > 0:
            cost_key = round(price / 10000, 2)
            adjusted = False
            while cost_key in used_costs:
                price *= 0.99
                cost_key = round(price / 10000, 2)
                adjusted = True
            if adjusted:
                item["price"] = price
            used_costs.add(cost_key)

        if not pd.isna(reach) and reach > 0:
            area_key = round((reach / 1000) ** 2 * 3.14, 2)
            adjusted = False
            while area_key in used_areas:
                reach *= 0.99
                area_key = round((reach / 1000) ** 2 * 3.14, 2)
                adjusted = True
            if adjusted:
                item["reach"] = reach
            used_areas.add(area_key)

    sync_line_state()
    st.session_state["optimization_applied"] = True

    if changed_count == 0:
        return (
            "warning",
            "⚠️ 未在当前数据库中找到符合要求的机型，产线未改变。",
            None,
        )
    st.session_state["global_cmd"] = global_cmd

    if is_compound:
        labels = "、".join(
            GLOBAL_OPTIMIZATION_OPERATIONS[operation]["label"]
            for operation in operations
        )
        if set(operations) == {"全局提速", "全局降本"}:
            message = (
                "✅ 已为您综合权衡成本与速度，"
                "并按各工位差异完成参数优化。"
            )
            warning = (
                "⚠️ 部分工位在同品牌/同类型中暂无同时满足全部要求的机型，"
                "已按比例调整相应参数。"
            ) if conflict_count else None
        else:
            message = (
                f"✅ 已为您综合权衡{labels}，"
                "并按各工位差异完成参数优化。"
            )
            warning = (
                "⚠️ 部分工位在同品牌/同类型中暂无完全匹配的机型，"
                "已按比例调整相应参数。"
            ) if conflict_count else None
        return "success", message, warning

    return (
        "success",
        GLOBAL_OPTIMIZATION_OPERATIONS[operations[0]]["success_message"],
        None,
    )


def comprehensive_model_scores(
    candidates,
    precision_weight,
    speed_weight,
    cost_weight,
    space_weight,
):
    candidates = ensure_arm_database_columns(candidates).reset_index(drop=True).copy()
    if candidates.empty:
        return candidates, pd.Series(dtype=float)

    score_columns = {}
    for name, column in (
        ("precision", "精度(mm)"),
        ("speed", "节拍秒数"),
        ("cost", "成本(万元)"),
        ("space", "占地估算(㎡)"),
    ):
        values = pd.to_numeric(candidates[column], errors="coerce")
        values = values.fillna(values.max() if values.notna().any() else 0)
        score_columns[name] = 1 - values.rank(method="average", pct=True)

    scores = pd.DataFrame(score_columns, index=candidates.index)
    weights = {
        "precision": precision_weight,
        "speed": speed_weight,
        "cost": cost_weight,
        "space": space_weight,
    }
    return candidates, sum(scores[name] * weight for name, weight in weights.items())


def format_exception_detail(error, api_key=""):
    """格式化异常信息，附带底层原因并隐藏 API Key。"""
    detail = str(error) or repr(error)
    cause = error.__cause__ or error.__context__
    if cause is not None:
        cause_detail = str(cause) or repr(cause)
        if cause_detail and cause_detail not in detail:
            detail = f"{detail}（底层原因：{type(cause).__name__}: {cause_detail}）"
    if api_key:
        detail = detail.replace(api_key, "[API Key 已隐藏]")
    return re.sub(r"sk-[A-Za-z0-9_-]+", "[API Key 已隐藏]", detail)


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

    st.session_state.pop("ai_last_error", None)
    try:
        from openai import OpenAI

        model_records = candidates[
            [
                "机型", "品牌名称", "品牌产地", "工序类型", "承重(kg)", "臂展半径", "精度(mm)",
                "IP防护", "运行速度", "通讯接口", "耐用性", "是否支持视觉", "核心特点", "瓶颈局限性", "价格",
            ]
        ].to_dict(orient="records")
        client = OpenAI(api_key=api_key, base_url="https://api.deepseek.com", timeout=25)
        st.info(
            "正在向 https://api.deepseek.com/chat/completions 发起真实请求"
            f"（model=deepseek-chat，API Key 长度 {len(api_key)}）..."
        )
        print(
            f"[AI 调试] 推荐请求 https://api.deepseek.com/chat/completions "
            f"model=deepseek-chat key_length={len(api_key)}",
            flush=True,
        )
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
        usage = getattr(response, "usage", None)
        total_tokens = getattr(usage, "total_tokens", "未知")
        st.success(
            f"DeepSeek 响应成功！model={getattr(response, 'model', 'deepseek-chat')}，"
            f"本次消耗 tokens={total_tokens}"
        )
        print(
            f"[AI 调试] 推荐响应成功 model={getattr(response, 'model', 'deepseek-chat')} "
            f"tokens={total_tokens}",
            flush=True,
        )
        result = json.loads(response.choices[0].message.content)
        model_name = str(result.get("model", "")).strip()
        matched = candidates[candidates["机型"].astype(str) == model_name]
        reason = str(result.get("reason", "根据场景与参数匹配结果推荐该机型。" )).strip()
        if matched.empty:
            return local_model.to_dict(), local_reason, "本地规则（AI 返回了候选库外机型）"
        return matched.iloc[0].to_dict(), reason, "DeepSeek AI"
    except Exception as error:
        st.session_state["ai_last_error"] = (
            f"{type(error).__name__}: {format_exception_detail(error, api_key)}"
        )
        return local_model.to_dict(), local_reason, "本地规则（AI 服务暂不可用）"


def sync_line_state():
    st.session_state["current_station_takts"] = {
        item["name"]: item["takt"] for item in st.session_state["production_line"]
    }
    st.session_state["current_station_models"] = {
        item["name"]: item["model"] for item in st.session_state["production_line"]
    }


def snapshot_production_line():
    return [dict(item) for item in st.session_state.get("production_line", [])]


def reset_optimization_baseline():
    st.session_state["initial_production_line"] = snapshot_production_line()
    st.session_state["initial_takt"] = {
        item["name"]: item["takt"]
        for item in st.session_state["initial_production_line"]
    }
    st.session_state["optimization_applied"] = False
    # 产线结构/模板发生变化后，清空各工位的已优化状态
    st.session_state["station_optimization_flags"] = {}


def reset_production_line():
    baseline = st.session_state.get("initial_production_line", [])
    st.session_state["production_line"] = [dict(item) for item in baseline]
    sync_line_state()
    st.session_state["optimization_applied"] = False
    st.session_state["global_cmd"] = ""
    st.session_state["station_optimization_flags"] = {}


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


def switch_selected_station(station):
    """切换当前工位。

    只应在控件回调（on_click / on_change）中调用：回调在脚本重新执行前运行，
    此时 ``arm_recommend_station`` 控件尚未实例化，可以安全写入其 session_state，
    不会触发 StreamlitWidgetAlreadyInstantiatedError。
    """
    if not station:
        return
    station_takts = st.session_state.get("current_station_takts", {})
    if station_takts and station not in station_takts:
        return
    st.session_state["selected_ws"] = station
    st.session_state["arm_recommend_station"] = station


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


def read_uploaded_csv(uploaded_file):
    for encoding in ("utf-8-sig", "gbk"):
        uploaded_file.seek(0)
        try:
            return pd.read_csv(uploaded_file, encoding=encoding)
        except UnicodeDecodeError:
            continue

    uploaded_file.seek(0)
    return pd.read_csv(
        uploaded_file,
        encoding="utf-8",
        encoding_errors="ignore",
    )


def load_existing_production_line(uploaded_file):
    database = read_uploaded_csv(uploaded_file)
    if database.empty:
        raise ValueError("上传的产线结构 CSV 为空。")

    available_cols = {normalize_column_name(col): col for col in database.columns}

    def resolve_column(*candidates):
        for candidate in candidates:
            normalized = normalize_column_name(candidate)
            if normalized in available_cols:
                return available_cols[normalized]
        return None

    name_col = resolve_column("工位名称", "工位名", "工位")
    if name_col is None:
        raise ValueError("CSV 必须包含“工位名称”列。")

    # 工位顺序、当前机型、节拍秒数均为可选列：只填工位名称时也能导入
    order_col = resolve_column("工位顺序(数字)", "工位顺序", "工位顺序（数字）", "工位序号")
    model_col = resolve_column("当前机型", "机型")
    takt_col = resolve_column("节拍秒数", "节拍", "节拍(秒)", "节拍秒")

    selected_columns = [name_col]
    if order_col:
        selected_columns.append(order_col)
    if model_col:
        selected_columns.append(model_col)
    if takt_col:
        selected_columns.append(takt_col)
    cleaned = database[selected_columns].copy()

    cleaned[name_col] = cleaned[name_col].map(
        lambda value: "" if pd.isna(value) else str(value).strip()
    )
    cleaned = cleaned[cleaned[name_col] != ""].copy()

    if order_col:
        cleaned[order_col] = pd.to_numeric(cleaned[order_col], errors="coerce")
        cleaned = cleaned.dropna(subset=[order_col])
        cleaned = cleaned.sort_values(
            order_col, ascending=True, kind="mergesort"
        )
    cleaned = cleaned.reset_index(drop=True)

    if takt_col:
        cleaned[takt_col] = cleaned[takt_col].map(
            lambda value: normalize_numeric(value, default=float("nan"))
        )

    if cleaned.empty:
        raise ValueError("CSV 中没有有效的工位结构数据。")

    if order_col and cleaned[order_col].duplicated().any():
        raise ValueError("工位顺序列中不能重复。")

    # 当前机械臂库：用于给未指定/无效机型的工位自动补全默认机型
    database_library = st.session_state.get("arm_database")
    if isinstance(database_library, pd.DataFrame) and not database_library.empty:
        model_library = ensure_arm_database_columns(database_library)
    else:
        model_library = pd.DataFrame()

    def pick_default_model(station_name):
        if model_library.empty:
            return None
        matched = model_library[
            model_library["工位"].astype(str).map(
                lambda label: normalize_station_label(label)
                == normalize_station_label(station_name)
            )
        ]
        if not matched.empty:
            return matched.iloc[0]
        return model_library.iloc[0]

    production_line = []
    auto_assigned_count = 0
    for _, row in cleaned.iterrows():
        station_name = str(row[name_col]).strip()

        raw_model = row[model_col] if model_col else None
        model_name = (
            "未配置"
            if raw_model is None or pd.isna(raw_model) or str(raw_model).strip() == ""
            else str(raw_model).strip()
        )

        raw_takt = row[takt_col] if takt_col else None
        takt_value = None
        if raw_takt is not None and not pd.isna(raw_takt) and float(raw_takt) > 0:
            takt_value = float(raw_takt)

        # 指定机型必须真实存在于当前机械臂库中
        matched_model = None
        if model_name != "未配置" and not model_library.empty:
            model_rows = model_library[model_library["机型"].astype(str) == model_name]
            if not model_rows.empty:
                matched_model = model_rows.iloc[0]

        auto_assigned = False
        if matched_model is None:
            matched_model = pick_default_model(station_name)
            if matched_model is not None:
                model_name = str(matched_model["机型"])
                auto_assigned = True
                auto_assigned_count += 1
            elif model_name != "未配置":
                model_name = "未配置"

        # 自动补全的工位按所分配机型的节拍重新计算；仅缺节拍时也取机型节拍
        if matched_model is not None and (auto_assigned or takt_value is None):
            takt_value = float(matched_model["节拍秒数"])
        if takt_value is None or takt_value <= 0:
            takt_value = 20.0

        takt_value = int(takt_value) if takt_value.is_integer() else takt_value
        production_line.append(
            {"name": station_name, "model": model_name, "takt": takt_value}
        )

    if len({item["name"] for item in production_line}) != len(production_line):
        raise ValueError("产线结构中不能出现重复工位名称。")

    st.session_state["production_line"] = production_line
    sync_line_state()
    reset_optimization_baseline()
    return production_line, auto_assigned_count


# 初始化各工位的占位节拍和已采用机型
initial_station_takts = {"上料": 18, "A装配": 25, "B精装": 32, "检测": 15, "下料": 12}
st.session_state.setdefault("current_station_takts", initial_station_takts.copy())
st.session_state.setdefault(
    "current_station_models",
    {station: "未配置" for station in initial_station_takts},
)


def apply_industry_template(template_name):
    custom_templates = st.session_state["custom_industry_templates"]
    if template_name in custom_templates:
        template = custom_templates[template_name]
        st.session_state["arm_database"] = template["database"].copy()
        st.session_state["arm_database_name"] = template["database_name"]
        st.session_state["arm_database_is_builtin"] = template["arm_database_is_builtin"]
    else:
        template = INDUSTRY_TEMPLATES[template_name]
        st.session_state["arm_database"] = pd.DataFrame(template["database"])
        st.session_state["arm_database_name"] = f"{template_name}默认机型库"
        st.session_state["arm_database_is_builtin"] = True

    st.session_state["industry_template"] = template_name
    st.session_state["production_line"] = [
        {"name": item["name"], "model": item.get("model", "未配置"), "takt": item["takt"]}
        for item in template["production_line"]
    ]
    sync_line_state()
    reset_optimization_baseline()
    st.session_state.setdefault("arm_filter_submitted", False)
    st.session_state.setdefault("arm_filter_conditions", None)


def save_current_custom_template(template_name):
    database = st.session_state.get("arm_database")
    st.session_state["custom_industry_templates"][template_name] = {
        "production_line": [
            {"name": item["name"], "model": item.get("model", "未配置"), "takt": item["takt"]}
            for item in st.session_state.get("production_line", [])
        ],
        "database": database.copy() if isinstance(database, pd.DataFrame) else pd.DataFrame(),
        "database_name": st.session_state.get("arm_database_name", "机械臂数据"),
        "arm_database_is_builtin": st.session_state.get("arm_database_is_builtin", False),
    }


def handle_custom_industry_name_change():
    template_name = st.session_state.get("custom_industry_name", "").strip()
    if not template_name:
        return
    if template_name in INDUSTRY_TEMPLATES:
        st.session_state["custom_industry_error"] = "该名称已被默认行业模板使用，请输入其他名称。"
        return

    save_current_custom_template(template_name)
    st.session_state["industry_template"] = template_name
    st.session_state["industry_template_selection"] = template_name
    st.session_state.pop("custom_industry_error", None)


def handle_industry_template_change():
    selected_template = st.session_state.get("industry_template_selection")
    if not selected_template or selected_template == CUSTOM_TEMPLATE_OPTION:
        return
    if selected_template != st.session_state.get("industry_template"):
        st.session_state["industry_template"] = selected_template
        apply_industry_template(selected_template)


st.session_state.setdefault("industry_template", "新能源汽车总装")
st.session_state.setdefault("industry_template_selection", st.session_state["industry_template"])
st.session_state.setdefault("custom_industry_templates", {})
if "production_line" not in st.session_state:
    apply_industry_template(st.session_state["industry_template"])

sync_line_state()
st.session_state.setdefault("initial_production_line", snapshot_production_line())
st.session_state.setdefault(
    "initial_takt",
    {item["name"]: item["takt"] for item in st.session_state["initial_production_line"]},
)
st.session_state.setdefault("optimization_applied", False)
st.session_state.setdefault("global_cmd", "")
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
        reset_optimization_baseline()
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
        reset_optimization_baseline()
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
    if station == "全部":
        operations = pending_ai_apply.get("operation", "全局提速")
        try:
            status, message, warning = run_global_optimization(operations)
        except Exception as error:
            traceback.print_exc()
            status, message, warning = (
                "warning",
                f"⚠️ 替换执行失败：{type(error).__name__}: {error}",
                None,
            )
        if status == "success":
            st.session_state["ai_apply_notice"] = message
            if warning:
                st.session_state["ai_apply_warning"] = warning
        else:
            # 找不到匹配机型/数据异常时用黄色警告，绝不静默失败
            st.session_state["ai_apply_warning"] = message
    else:
        station_item = next(
            (item for item in st.session_state["production_line"] if item["name"] == station),
            None,
        )
        if station_item is not None:
            apply_model_to_station(
                {"机型": pending_ai_apply["model"], "节拍秒数": pending_ai_apply["takt"]},
                station,
            )
            # 目标产能只作为需求指标展示，绝不回写/改变当前产线节拍或机型
            target_capacity_value = normalize_numeric(
                pending_ai_apply.get("target_capacity", 0)
            )
            if target_capacity_value > 0:
                st.session_state["ai_apply_notice"] = (
                    f"已更新 {station}：采用 {pending_ai_apply['model']}，"
                    f"目标产能 {format_display_number(target_capacity_value, 1)} 件/小时。"
                )
            else:
                st.session_state["ai_apply_notice"] = (
                    f"已更新 {station}：采用 {pending_ai_apply['model']}。"
                )
        else:
            # 不能静默忽略：目标工位可能已被删除或重命名
            st.session_state["ai_apply_error"] = (
                f"未找到工位“{station}”，AI 方案未执行，请刷新产线结构后重试。"
            )
    # 数据更新完成，强制重新加载页面，避免前端复用旧节点导致 removeChild 崩溃
    st.rerun()

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
    "运行速度(m/s)",
    "通讯接口",
    "耐用性",
    "核心特点",
    "瓶颈局限性",
    "价格",
    "维保响应",
    "节拍秒数",
    "占地估算(㎡)",
    "成本(万元)",
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
additional_default_arms = [
    ("电池合装", "ABB IRB 2600", "瑞典", "ABB", "装配", 1650, 20, 0.04, 230000, 20),
    ("电池合装", "ABB IRB 4600", "瑞典", "ABB", "上下料", 2050, 45, 0.06, 260000, 18),
    ("电池合装", "安川 GP8", "日本", "安川", "装配", 727, 8, 0.02, 125000, 18),
    ("电池包热管理", "安川 GP25", "日本", "安川", "焊接", 1730, 25, 0.06, 190000, 20),
    ("电池包热管理", "安川 GP180", "日本", "安川", "上下料", 2702, 180, 0.05, 380000, 24),
    ("底盘总装", "发那科 M-10iD/12", "日本", "发那科", "装配", 1441, 12, 0.03, 175000, 19),
    ("底盘总装", "发那科 M-710iC/50", "日本", "发那科", "上下料", 2050, 50, 0.07, 270000, 20),
    ("整车检测", "发那科 CRX-10iA/L", "日本", "发那科", "装配", 1418, 10, 0.04, 160000, 22),
    ("整车检测", "库卡 KR 10 R1100", "德国", "KUKA", "装配", 1101, 10, 0.03, 170000, 19),
    ("热处理", "库卡 KR 16 R2010", "德国", "KUKA", "上下料", 2010, 16, 0.04, 200000, 20),
    ("热处理", "库卡 KR 30 R2100", "德国", "KUKA", "焊接", 2101, 30, 0.06, 230000, 22),
    ("CNC精加工", "优傲 UR10e", "丹麦", "优傲", "装配", 1300, 12.5, 0.05, 220000, 24),
    ("CNC精加工", "遨博 AUBO-i10", "中国", "遨博", "装配", 1350, 10, 0.05, 145000, 24),
    ("铣削加工", "埃斯顿 ER10-900", "中国", "埃斯顿", "上下料", 900, 10, 0.03, 110000, 21),
    ("质检入库", "新松 SR10A", "中国", "新松", "码垛", 1300, 10, 0.03, 135000, 20),
]
default_arm_rows.extend(
    {
        "工位": station,
        "机型": model,
        "产地": origin,
        "品牌产地": "国产" if origin == "中国" else "进口",
        "品牌名称": brand,
        "工序类型": process_type,
        "臂展半径": reach,
        "承重(kg)": payload,
        "精度": f"±{precision} mm",
        "精度(mm)": precision,
        "是否支持视觉": True,
        "价格": price,
        "维保响应": "24小时",
        "节拍秒数": takt,
    }
    for station, model, origin, brand, process_type, reach, payload, precision, price, takt
    in additional_default_arms
)
st.session_state.setdefault("arm_database_name", "内置机械臂数据")
st.session_state.setdefault(
    "arm_database_is_builtin",
    st.session_state["arm_database_name"] == "内置机械臂数据",
)
if st.session_state["arm_database_is_builtin"]:
    st.session_state["arm_database"] = ensure_arm_database_columns(pd.DataFrame(default_arm_rows))
else:
    st.session_state["arm_database"] = ensure_arm_database_columns(
        st.session_state.get("arm_database", pd.DataFrame(default_arm_rows))
    )
st.session_state.setdefault("arm_filter_submitted", False)
st.session_state.setdefault("arm_filter_conditions", None)


# 读取并校验用户上传的 CSV 或 Excel 机械臂数据库
def load_arm_database(uploaded_file):
    file_extension = uploaded_file.name.rsplit(".", 1)[-1].lower()
    uploaded_file.seek(0)
    if file_extension == "csv":
        database = read_uploaded_csv(uploaded_file)
    else:
        uploaded_file.seek(0)
        database = pd.read_excel(uploaded_file)

    if database.empty:
        raise ValueError("文件中没有机械臂数据")

    database = clean_arm_database_column_names(database)
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


def is_global_speed_request(text):
    global_terms = (
        "整体",
        "整线",
        "整条",
        "全部工位",
        "所有工位",
        "全线",
        "全产线",
        "整条产线",
    )
    speed_terms = (
        "提速",
        "调快",
        "加快",
        "变快",
        "加速",
        "缩短节拍",
        "提高速度",
        "提升速度",
    )
    return any(term in text for term in global_terms) and any(
        term in text for term in speed_terms
    )


KNOWN_ORIGINS = (
    "中国",
    "日本",
    "德国",
    "美国",
    "瑞士",
    "瑞典",
    "韩国",
    "法国",
    "意大利",
    "英国",
    "加拿大",
    "奥地利",
    "西班牙",
)


def _is_origin_requirement(requirement):
    return any(
        origin in str(requirement) for origin in KNOWN_ORIGINS
    )


def rule_based_parse(text):
    global_terms = (
        "整条",
        "整线",
        "全线",
        "整体",
        "全产线",
        "整条产线",
        "全部工位",
        "所有工位",
    )
    quality_terms = ("质量", "品质", "良率")
    station_options = list(
        st.session_state.get("current_station_takts", initial_station_takts)
    )
    mentions_quality = any(term in text for term in quality_terms)

    # 统一从关键词库提取全局要求，支持同一维度的“提升/降低”双向操作
    global_requirements = detect_global_operations(text)

    explicit_station = any(
        str(name).strip() and str(name).lower() in text.lower()
        for name in station_options
    )
    has_global_scope = (
        any(term in text for term in global_terms)
        or "产线" in text
        # 只要命中全局优化关键词且未点名具体工位，一律强制按整线处理
        or (bool(global_requirements) and not explicit_station)
    )

    # 命中全局指令时，返回完整的要求列表（支持复合指令）
    if has_global_scope and global_requirements:
        return {
            "工位": "全部",
            "要求": global_requirements,
            "目标产能": 0,
        }

    requirements = []
    if "国产" in text:
        requirements.append("国产")
    elif "进口" in text:
        requirements.append("进口")
    if "高精度" in text or mentions_quality:
        # 质量/品质/良率统一映射为精度要求（高精度）
        requirements.append("高精度")

    for origin in KNOWN_ORIGINS:
        if origin in text and origin not in requirements:
            requirements.append(origin)
    if not station_options:
        raise ValueError("当前产线没有可用工位")

    # 识别到“整条/全线”等全局范围词时，强制工位输出为“全部”
    if has_global_scope or is_global_speed_request(text):
        station = "全部"
    else:
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
        target_capacity = float(
            capacity_match.group(1)
            if capacity_match.lastindex
            else capacity_match.group()
        )
        if target_capacity <= 0:
            target_capacity = 0.0
    else:
        # 未在描述中明确目标产能时，不读取右上角输入框，
        # 确保目标产能只用于对比提示，不影响选型与产线数据
        target_capacity = 0.0

    return {
        "工位": station,
        "要求": requirements,
        "目标产能": target_capacity,
    }


def _filter_candidates_by_requirements(candidates, requirements):
    filtered = candidates.copy()
    for requirement in requirements:
        requirement_text = str(requirement)
        if "国产" in requirement_text:
            filtered = filtered[filtered["产地"].map(is_domestic)]
        elif "进口" in requirement_text:
            filtered = filtered[~filtered["产地"].map(is_domestic)]
        elif "高精度" in requirement_text or "精度高" in requirement_text:
            precision = filtered["精度"].map(parse_first_number)
            filtered = filtered[precision.notna() & (precision <= 0.02)]
        elif "精度" in requirement_text:
            precision_limit = parse_first_number(requirement_text)
            if precision_limit is None:
                return filtered.iloc[0:0]
            precision = filtered["精度"].map(parse_first_number)
            filtered = filtered[
                precision.notna() & (precision <= precision_limit)
            ]
        elif "维保" in requirement_text or "响应" in requirement_text:
            maintenance_limit = parse_maintenance_hours(requirement_text)
            if maintenance_limit is None:
                return filtered.iloc[0:0]
            maintenance = filtered["维保响应"].map(parse_maintenance_hours)
            filtered = filtered[
                maintenance.notna() & (maintenance <= maintenance_limit)
            ]
        elif "价格" in requirement_text or "预算" in requirement_text:
            price_limit = parse_first_number(requirement_text)
            if price_limit is None:
                return filtered.iloc[0:0]
            prices = pd.to_numeric(filtered["价格"], errors="coerce")
            filtered = filtered[prices.notna() & (prices <= price_limit)]
        else:
            origins = (
                filtered["产地"].fillna("").astype(str)
                + " "
                + filtered["品牌产地"].fillna("").astype(str)
            )
            filtered = filtered[
                origins.str.contains(
                    re.escape(requirement_text), case=False, regex=True
                )
            ]
        if filtered.empty:
            return filtered
    return filtered


def choose_model_for_ai(database, ai_result, station_options):
    station = resolve_line_station(ai_result["工位"], station_options)
    # 目标产能为 0 表示用户未指定，仅按其它条件选型，不作为硬约束
    target_capacity = max(
        normalize_numeric(ai_result.get("目标产能", 0)), 0.0
    )
    requirements = [
        str(requirement).strip()
        for requirement in ai_result.get("要求", [])
        if str(requirement).strip()
    ]

    station_candidates = database[database["工位"] == station].copy()
    candidates = _filter_candidates_by_requirements(
        station_candidates, requirements
    )

    # 产地类要求允许跨工位在整库中强制匹配（例如“改为瑞士的”）
    if candidates.empty and any(
        _is_origin_requirement(requirement) for requirement in requirements
    ):
        candidates = _filter_candidates_by_requirements(
            database.copy(), requirements
        )

    if target_capacity > 0 and not candidates.empty:
        capacity_candidates = candidates[
            candidates["节拍秒数"] <= 3600 / target_capacity
        ]
        if not capacity_candidates.empty:
            candidates = capacity_candidates

    if candidates.empty:
        return station, None, target_capacity, "库中无符合条件的机型"

    selected_model = candidates.sort_values("节拍秒数", kind="stable").iloc[0]
    return station, selected_model, target_capacity, None


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
    except StreamlitSecretNotFoundError:
        # 未创建 secrets.toml 属于正常情况，不是需要上报的错误
        return ""
    except Exception as error:
        # 其他异常不能静默吞掉，至少写入服务端日志便于排查
        print(
            f"[配置] 读取 secrets 失败: {type(error).__name__}: {error}",
            flush=True,
        )
        traceback.print_exc()
        return ""
    if value is None:
        return ""
    return str(value).strip()


with st.sidebar:
    st.header("行业场景")
    st.subheader("产线结构导入")
    uploaded_line_structure = st.file_uploader(
        "导入已有产线结构（CSV）",
        type=["csv"],
        key="uploaded_production_structure",
    )
    if uploaded_line_structure is not None:
        uploaded_content = uploaded_line_structure.getvalue()
        import_signature = (
            uploaded_line_structure.name,
            hashlib.sha256(uploaded_content).hexdigest(),
        )
        if import_signature != st.session_state.get("last_imported_line_signature"):
            st.session_state["last_imported_line_signature"] = import_signature
            try:
                imported_line, auto_assigned_count = load_existing_production_line(
                    uploaded_line_structure
                )
                template_name = uploaded_line_structure.name.rsplit(".", 1)[0].strip()
                if template_name in INDUSTRY_TEMPLATES:
                    template_name = f"{template_name}（导入）"
                save_current_custom_template(template_name)
                st.session_state["industry_template"] = template_name
                st.session_state["industry_template_selection"] = template_name
                if auto_assigned_count:
                    st.session_state["line_import_notice"] = (
                        f"已导入 {len(imported_line)} 个工位，"
                        "系统已自动为您分配默认机械臂作为初始状态。"
                    )
                else:
                    st.session_state["line_import_notice"] = (
                        f"已导入并选中模板“{template_name}”，"
                        f"共更新 {len(imported_line)} 个工位。"
                    )
                # 机型/节拍/成本/占地已初始化完成，强制重新加载页面刷新图表
                st.rerun()
            except ValueError as error:
                st.error(f"产线结构导入失败：{error}")

    if "line_import_notice" in st.session_state:
        st.success(st.session_state.pop("line_import_notice"))

    template_options = [
        *INDUSTRY_TEMPLATES.keys(),
        *st.session_state["custom_industry_templates"].keys(),
        CUSTOM_TEMPLATE_OPTION,
    ]
    current_template = st.session_state.get("industry_template_selection")
    if current_template not in template_options:
        current_template = st.session_state.get("industry_template", "新能源汽车总装")
        if current_template not in template_options:
            current_template = "新能源汽车总装"
        st.session_state["industry_template_selection"] = current_template
    st.selectbox(
        "选择行业模板",
        template_options,
        index=template_options.index(current_template),
        key="industry_template_selection",
        on_change=handle_industry_template_change,
    )
    if st.session_state.get("industry_template_selection") == CUSTOM_TEMPLATE_OPTION:
        st.text_input(
            "请输入自定义行业/产线名称",
            key="custom_industry_name",
            on_change=handle_custom_industry_name_change,
        )
        if st.session_state.get("custom_industry_error"):
            st.warning(st.session_state["custom_industry_error"])

    st.download_button(
        label="下载产线结构模板",
        data=build_production_line_template_csv(),
        file_name="产线结构模板.csv",
        mime="text/csv",
        key="download_production_template",
    )

    if st.button("重置产线", key="reset_production_line_button"):
        reset_production_line()
        st.rerun()

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
            "model": "deepseek-chat",
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
    st.toggle("📊 查看当前机械臂数据库", key="show_arm_database")

# 页面标题
st.title("智能线搭子")

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

# 目标产能只用于达标校验，绝不参与实际产线节拍或机型计算
target_capacity_value = normalize_numeric(st.session_state.get("target_capacity", 0))
line_takts_for_check = st.session_state.get("current_station_takts", {})
if target_capacity_value > 0 and line_takts_for_check:
    actual_capacity_value = 3600 / max(
        float(takt) for takt in line_takts_for_check.values()
    )
    if actual_capacity_value < target_capacity_value:
        st.markdown(
            '<div style="color:#d95d4f;font-weight:600;">'
            "⚠️ 未达到目标产能，建议使用 AI 推荐提速"
            f"（当前实际 {format_display_number(actual_capacity_value, 1)} 件/小时 &lt; "
            f"目标 {format_display_number(target_capacity_value, 1)} 件/小时）"
            "</div>",
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            '<div style="color:#2e7d32;font-weight:600;">'
            "✅ 已达到目标产能"
            f"（当前实际 {format_display_number(actual_capacity_value, 1)} 件/小时 ≥ "
            f"目标 {format_display_number(target_capacity_value, 1)} 件/小时）"
            "</div>",
            unsafe_allow_html=True,
        )

if ai_enabled:
    # 解析完成/失败后都会主动 st.rerun()，结果消息统一放到下一轮渲染，
    # 避免同一次运行中反复增删前端元素触发 removeChild 崩溃。
    for message_key, render_message in (
        ("ai_parse_error", st.error),
        ("ai_parse_warning", st.warning),
        ("ai_parse_success", st.success),
    ):
        if message_key in st.session_state:
            render_message(st.session_state.pop(message_key))

    ai_description = st.text_area("用自然语言描述改动", key="ai_change_description")
    if st.button("AI 解析", key="parse_ai_change"):
        if not ai_description.strip():
            st.warning("请先描述希望调整的产线条件。")
        else:
            st.session_state["ai_parsed_result"] = None
            st.session_state["ai_parse_mode"] = None
            st.session_state.pop("ai_parse_error", None)
            st.session_state.pop("ai_parse_warning", None)
            st.session_state.pop("ai_parse_success", None)
            api_key = ""
            try:
                from openai import OpenAI

                provider_config = st.session_state.get("ai_provider_config", {})
                api_key = str(provider_config.get("api_key", "") or "").strip()
                base_url = str(provider_config.get("base_url", "") or "").strip()
                model_name = str(provider_config.get("model", "") or "").strip()
                provider_name = str(provider_config.get("provider", "") or "")

                if provider_name == "默认 DeepSeek":
                    # 强制使用 DeepSeek 官方配置，避免被旧的会话状态覆盖
                    if not api_key:
                        api_key = (
                            str(st.session_state.get("manual_api_key", "") or "").strip()
                            or safe_get_secret("DEEPSEEK_API_KEY")
                        )
                    base_url = "https://api.deepseek.com"
                    model_name = "deepseek-chat"

                if not api_key and provider_name != "本地 Ollama":
                    # 明确告知：没有 Key 时绝不发起请求，也不伪造 AI 结果
                    st.session_state["ai_parsed_result"] = rule_based_parse(ai_description)
                    st.session_state["ai_parse_mode"] = "规则兜底模式（未发起网络请求）"
                    st.session_state["ai_parse_warning"] = (
                        "未检测到 API Key：本次未向任何 AI 服务发起网络请求，"
                        "已使用本地规则引擎。"
                    )
                    # 数据已更新，强制重新加载页面
                    st.rerun()
                else:
                    if not base_url or not model_name:
                        raise ValueError("请在 AI 设置区填写 base_url 和 model")

                    station_options = list(st.session_state.get("current_station_takts", {}))
                    client = OpenAI(
                        api_key=api_key or "ollama",
                        base_url=base_url,
                        timeout=30,
                    )
                    request_url = f"{base_url.rstrip('/')}/chat/completions"
                    st.info(
                        f"正在向 {request_url} 发起真实请求"
                        f"（model={model_name}，API Key 长度 {len(api_key)}）..."
                    )
                    print(
                        f"[AI 调试] 发起请求 {request_url} model={model_name} "
                        f"key_length={len(api_key)} provider={provider_name}",
                        flush=True,
                    )
                    system_prompt = (
                        "你是产线重配置助手。根据用户描述，只返回一个合法 JSON 对象，"
                        '字段必须是 {"工位":"B精装","要求":["国产","高精度"],"目标产能":120}。\n'
                        "【全局范围】当描述包含 整条/整线/全线/整体/全部工位/所有工位 "
                        '等全局范围词时，工位必须输出 "全部"，不得映射为单个工位。\n'
                        "【严格映射规则】请严格根据用户输入提取要求，绝对不允许混淆以下概念：\n"
                        '- 降低速度/减速/变慢/降低节拍 -> "全局降速"\n'
                        '- 提高速度/提速/加快/变快 -> "全局提速"\n'
                        '- 降低质量/降质/精度变差/降低精度 -> "全局降质"\n'
                        '- 提高质量/提质/提高精度 -> "全局提质"\n'
                        '- 降低成本/降本/省钱 -> "全局降本"\n'
                        '- 增加成本/提价/涨价 -> "全局提价"\n'
                        '- 缩小占地/省地/减少空间 -> "全局省地"\n'
                        '- 扩大占地/增加空间/占地变大 -> "全局增地"\n'
                        '禁止把"速度"相关表述输出为质量指令，也禁止把"质量"相关表述输出为速度指令。\n'
                        "【示例】\n"
                        "用户输入：降低速度\n"
                        '输出：{"工位": "全部", "要求": ["全局降速"], "目标产能": 0}\n'
                        "用户输入：提高质量\n"
                        '输出：{"工位": "全部", "要求": ["全局提质"], "目标产能": 0}\n'
                        "用户输入：整条产线提速，并且成本要低\n"
                        '输出：{"工位": "全部", "要求": ["全局提速", "全局降本"], "目标产能": 0}\n'
                        "要求必须是字符串数组；高精度表示精度误差不大于 0.02 mm。"
                        "目标产能必须是大于等于 0 的数字；0 表示用户未提出产能诉求。"
                        "如果用户提到降低质量，必须在 requirements（要求）数组中"
                        "输出 '全局降质'，严禁返回空数组。"
                        "严禁输出 JSON 以外的任何内容，不要输出 Markdown。"
                    )
                    response = client.chat.completions.create(
                        model=model_name,
                        messages=[
                            {
                                "role": "system",
                                "content": system_prompt,
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
                    usage = getattr(response, "usage", None)
                    total_tokens = getattr(usage, "total_tokens", "未知")
                    st.session_state["ai_parse_success"] = (
                        f"DeepSeek 响应成功！model={getattr(response, 'model', model_name)}，"
                        f"本次消耗 tokens={total_tokens}"
                    )
                    print(
                        f"[AI 调试] 响应成功 model={getattr(response, 'model', model_name)} "
                        f"tokens={total_tokens}",
                        flush=True,
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
                    detected_global_operations = detect_global_operations(
                        ai_description
                    )
                    has_explicit_station = any(
                        str(name).strip()
                        and str(name).lower() in ai_description.lower()
                        for name in station_options
                    )
                    force_global = is_global_speed_request(ai_description) or (
                        detected_global_operations and not has_explicit_station
                    )
                    if force_global:
                        parsed_result["工位"] = "全部"
                    else:
                        try:
                            parsed_result["工位"] = resolve_line_station(
                                parsed_result["工位"], station_options
                            )
                        except ValueError:
                            # 安全检查：工位既不是“全部”也不在当前产线中时，
                            # 不抛异常崩溃，降级为整线应用并在 rerun 后提示用户。
                            parsed_result["工位"] = "全部"
                            st.session_state["ai_parse_warning"] = (
                                "未找到对应的工位，已默认应用至整条产线"
                            )
                    # 目标产能允许为 0（表示用户没有改变产能的诉求），不做强校验
                    parsed_result["目标产能"] = max(
                        normalize_numeric(parsed_result.get("目标产能", 0)), 0.0
                    )
                    st.session_state["ai_parsed_result"] = parsed_result
                    st.session_state["ai_parse_mode"] = "AI 模式"
                    # 数据已更新，强制重新加载页面，避免前端 DOM 复用导致 removeChild 崩溃
                    st.rerun()
            except Exception as error:
                # 完整堆栈写入服务端日志，并把错误原样呈现给用户，绝不静默吞掉
                traceback.print_exc()
                st.session_state.pop("ai_parse_success", None)
                error_message = (
                    f"AI 解析真实报错: {type(error).__name__}: "
                    f"{format_exception_detail(error, api_key)}"
                )
                print(f"[AI 解析失败] {error_message}", flush=True)
                st.session_state["ai_parse_error"] = error_message
                try:
                    st.session_state["ai_parsed_result"] = rule_based_parse(ai_description)
                    st.session_state["ai_parse_mode"] = "规则兜底模式"
                    st.session_state["ai_parse_warning"] = (
                        "AI 调用失败，已切换为本地规则引擎解析。"
                    )
                except Exception as fallback_error:
                    traceback.print_exc()
                    st.session_state["ai_parsed_result"] = None
                    st.session_state["ai_parse_mode"] = None
                    st.session_state["ai_parse_error"] = (
                        f"{error_message}；规则兜底也失败: "
                        f"{type(fallback_error).__name__}: {fallback_error}"
                    )
                # 兜底结果已写入会话状态，强制重新加载页面统一渲染
                st.rerun()

    parsed_result = st.session_state.get("ai_parsed_result")
    if parsed_result is not None:
        st.info(st.session_state.get("ai_parse_mode", "AI 模式"))
        st.json(parsed_result)
        if st.button("确认执行", key="confirm_ai_change"):
            try:
                if parsed_result.get("工位") == "全部":
                    requirements = [
                        str(item) for item in parsed_result.get("要求", [])
                    ]
                    # 兼容 AI 返回的不同措辞：统一走关键词提取
                    operations = []
                    for requirement in requirements:
                        for operation in detect_global_operations(
                            requirement
                        ):
                            if operation not in operations:
                                operations.append(operation)
                    if not operations:
                        operations = detect_global_operations(
                            st.session_state.get("ai_change_description", "")
                        )
                    if not operations:
                        operations = ["全局提速"]
                    st.session_state["ai_pending_apply"] = {
                        "station": "全部",
                        "operation": operations,
                    }
                    st.session_state["ai_parsed_result"] = None
                    st.rerun()
                (
                    station,
                    selected_model,
                    target_capacity,
                    selection_warning,
                ) = choose_model_for_ai(
                    st.session_state["arm_database"],
                    parsed_result,
                    list(st.session_state["current_station_takts"]),
                )
                if selected_model is None:
                    st.session_state["ai_parse_warning"] = (
                        selection_warning or "库中无符合条件的机型"
                    )
                    st.rerun()
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
                # 暂存提示后强制重载，避免在旧组件上直接打补丁
                st.session_state["ai_parse_warning"] = str(error)
                st.rerun()
            except Exception as error:
                traceback.print_exc()
                st.session_state["ai_parse_error"] = f"无法执行该方案：{error}"
                st.rerun()
else:
    st.session_state["ai_parsed_result"] = None
    st.session_state["ai_parse_mode"] = None

if "ai_apply_notice" in st.session_state:
    st.success(st.session_state.pop("ai_apply_notice"))
if "ai_apply_warning" in st.session_state:
    st.warning(st.session_state.pop("ai_apply_warning"))
if "ai_apply_error" in st.session_state:
    st.error(st.session_state.pop("ai_apply_error"))

if uploaded_database is not None:
    try:
        imported_database = load_arm_database(uploaded_database)
        st.session_state["arm_database"] = imported_database
        st.session_state["arm_database_name"] = uploaded_database.name
        st.session_state["arm_database_is_builtin"] = False
        # 机械臂库变化后，允许基于新库重新执行全局寻优
        st.session_state["station_optimization_flags"] = {}
        st.success(f"已导入 {len(imported_database)} 条机械臂数据，后续候选机型将使用此数据库。")
    except (ValueError, ImportError) as error:
        st.error(f"机械臂数据库导入失败：{error}")

MODEL_LIBRARY = st.session_state.get("arm_database")
if MODEL_LIBRARY is None or not hasattr(MODEL_LIBRARY, "empty"):
    MODEL_LIBRARY = pd.DataFrame(columns=required_arm_columns)
MODEL_LIBRARY = ensure_arm_database_columns(MODEL_LIBRARY)
st.session_state["arm_database"] = MODEL_LIBRARY

st.caption(
    f"当前机械臂数据：{st.session_state.get('arm_database_name', '未命名')}（{len(MODEL_LIBRARY)} 条）"
)
if st.session_state.get("show_arm_database", False):
    st.dataframe(
        MODEL_LIBRARY.drop(
            columns=[
                column
                for column in MODEL_LIBRARY.columns
                if str(column).startswith("_")
            ],
            errors="ignore",
        ),
        use_container_width=True,
        height=360,
        hide_index=True,
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

    with st.expander("⚙️ 产线结构自定义（点击展开）", expanded=False):
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
                key="add_station_submit",
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
                    key="delete_station_select",
                )
                delete_station_submitted = st.form_submit_button(
                    "删除工位",
                    key="delete_station_submit",
                )
            if delete_station_submitted:
                st.session_state["line_pending_delete"] = station_to_delete
                st.rerun()
        else:
            st.info("当前产线没有工位，可先添加一个工位。")

    if "line_edit_notice" in st.session_state:
        st.success(st.session_state.pop("line_edit_notice"))

    if st.session_state["production_line"]:
        # 图表选择等“本轮渲染后才知道”的工位切换先暂存，
        # 下一轮在目标工位控件实例化之前再写入其 key，避免状态修改冲突。
        pending_station = st.session_state.pop("_pending_station_switch", None)
        if pending_station:
            switch_selected_station(pending_station)

        station_options = list(st.session_state["current_station_takts"])
        selected_ws = (
            st.session_state.get("selected_ws")
            or st.session_state.get("arm_recommend_station")
            or next(iter(station_options), None)
        )
        if selected_ws not in station_options:
            selected_ws = next(iter(station_options), None)

        with st.expander("🌟 综合最优推荐（自定义权重）", expanded=False):
            st.caption(f"当前推荐工位：{selected_ws or '未选中'}")
            weight_columns = st.columns(2)
            with weight_columns[0]:
                precision_weight = st.slider(
                    "精度权重",
                    min_value=1,
                    max_value=10,
                    value=10,
                    key="custom_recommend_precision_weight",
                )
                speed_weight = st.slider(
                    "效率/速度权重",
                    min_value=1,
                    max_value=10,
                    value=8,
                    key="custom_recommend_speed_weight",
                )
            with weight_columns[1]:
                cost_weight = st.slider(
                    "成本权重",
                    min_value=1,
                    max_value=10,
                    value=6,
                    key="custom_recommend_cost_weight",
                )
                space_weight = st.slider(
                    "占地权重",
                    min_value=1,
                    max_value=10,
                    value=4,
                    key="custom_recommend_space_weight",
                )

            if st.button(
                "开始智能推荐",
                key="start_custom_weight_recommendation",
                width="stretch",
                disabled=MODEL_LIBRARY.empty or not selected_ws,
            ):
                station_candidates = get_station_candidate_models(
                    MODEL_LIBRARY,
                    selected_ws,
                )
                ranked_candidates, scores = comprehensive_model_scores(
                    station_candidates,
                    precision_weight,
                    speed_weight,
                    cost_weight,
                    space_weight,
                )
                if ranked_candidates.empty:
                    st.session_state.pop("custom_weight_recommendation", None)
                    st.warning("当前工位没有可用于综合推荐的机械臂数据。")
                else:
                    best_index = scores.idxmax()
                    st.session_state["custom_weight_recommendation"] = {
                        "station": selected_ws,
                        "model": ranked_candidates.loc[best_index].to_dict(),
                        "score": float(scores.loc[best_index]),
                    }

            custom_recommendation = st.session_state.get(
                "custom_weight_recommendation"
            )
            if (
                custom_recommendation
                and custom_recommendation.get("station") == selected_ws
            ):
                best_model = custom_recommendation["model"]
                st.success(
                    f"系统已为您推荐最优机型：{best_model.get('机型', '未知机型')}（综合得分最高）"
                )
                st.caption(
                    f"综合得分：{custom_recommendation['score']:.2f}"
                    f" · 精度 ±{normalize_numeric(best_model.get('精度(mm)', 0)):g} mm"
                    f" · 节拍 {format_display_number(best_model.get('节拍秒数', 0), 1)} 秒"
                    f" · 成本 {format_display_number(best_model.get('成本(万元)', 0), 2)} 万元"
                    f" · 占地 {format_display_number(best_model.get('占地估算(㎡)', 0), 2)} ㎡"
                )
                if st.button(
                    "一键采用推荐机型",
                    key="apply_custom_weight_recommendation",
                    width="stretch",
                ):
                    if apply_model_to_station(best_model, selected_ws):
                        st.session_state.pop("custom_weight_recommendation", None)
                        st.rerun()

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
            filter_submitted = st.form_submit_button(
                "筛选候选机械臂",
                key="submit_arm_filter",
            )
            recommend_submitted = st.form_submit_button(
                "🤖 AI 智能推荐",
                key="submit_ai_arm_recommendation",
                type="primary",
            )

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
            st.session_state.pop("filtered_arms", None)
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

            # 持久化筛选结果，供右侧“手动更换当前工位机械臂”下拉框联动使用
            st.session_state["filtered_arms"] = (
                filtered_models["机型"].dropna().astype(str).drop_duplicates().tolist()
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
                        brand_name = str(model.get("品牌名称", "") or "")
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
                                f"节拍：{format_display_number(model.get('节拍秒数', 20), 1)} 秒　|　"
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
                elif "AI 服务暂不可用" in recommendation["source"]:
                    st.error(
                        "DeepSeek 调用失败："
                        f"{st.session_state.get('ai_last_error', '未知错误')}"
                    )
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

        st.metric(
            "估算整线产能（件/小时）",
            format_display_number(3600 / bottleneck_takt, 1),
        )
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
            if (
                selected_station
                and selected_station in cycle_times
                and selected_station != st.session_state.get("_last_chart_station")
            ):
                # 不在本轮直接改 st.session_state["arm_recommend_station"]
                # （对应控件本轮已实例化），改为暂存后 rerun 生效。
                st.session_state["_last_chart_station"] = selected_station
                st.session_state["_pending_station_switch"] = selected_station
                st.rerun()

        st.plotly_chart(
            topology_figure,
            key=chart_key,
            use_container_width=True,
            on_select="rerun",
            selection_mode="points",
            config={
                "displayModeBar": False,
                "staticPlot": True,
                "scrollZoom": False,
            },
        )

        station_columns = st.columns(min(len(topology_stations), 5))
        for idx, (station, _) in enumerate(topology_stations):
            with station_columns[idx % len(station_columns)]:
                st.button(
                    station,
                    key=f"station_button_{station}",
                    use_container_width=True,
                    on_click=switch_selected_station,
                    args=(station,),
                )

        selected_ws = st.session_state.get("selected_ws")
        if selected_ws and selected_ws in cycle_times:
            with st.container():
                st.caption(f"当前选中工位：{selected_ws}")

                # 与左侧“筛选候选机械臂”联动：
                # 已筛选时只展示筛选结果，未筛选时展示全局机械臂库。
                if st.session_state.get("arm_filter_submitted"):
                    filtered_arm_names = st.session_state.get("filtered_arms", [])
                    replacement_candidates = MODEL_LIBRARY[
                        MODEL_LIBRARY["机型"].dropna().astype(str).isin(filtered_arm_names)
                    ]
                    if replacement_candidates.empty:
                        replacement_candidates = MODEL_LIBRARY.copy()
                else:
                    replacement_candidates = MODEL_LIBRARY.copy()

                model_options = (
                    replacement_candidates["机型"].dropna().astype(str).drop_duplicates().tolist()
                )
                if not model_options:
                    model_options = ["无可用机型"]

                current_model = st.session_state["current_station_models"].get(selected_ws, "未配置")
                default_index = model_options.index(current_model) if current_model in model_options else 0
                with st.expander("🔧 手动更换当前工位机械臂", expanded=False):
                    with st.form(f"replace_arm_form_{selected_ws}"):
                        replacement_model = st.selectbox(
                            "更换机械臂",
                            model_options,
                            index=default_index,
                            key=f"replacement_model_{selected_ws}",
                        )
                        submitted = st.form_submit_button(
                            "确认替换",
                            key=f"confirm_replacement_{selected_ws}",
                            disabled=(replacement_model == "无可用机型"),
                        )
                    if submitted and replacement_model != "无可用机型":
                        selected_row = replacement_candidates[
                            replacement_candidates["机型"].astype(str) == replacement_model
                        ].iloc[0]
                        apply_model_to_station(selected_row, selected_ws)
                        calc_line_takt(st.session_state["current_station_takts"])
                        st.rerun()

        st.subheader("优化前后节拍对比")
        st.caption(
            "柱子越矮代表干活越快，红色代表瓶颈。选型后柱子变矮，说明整线速度变快了。"
        )
        initial_takts = {
            item["name"]: float(item["takt"])
            for item in st.session_state["initial_production_line"]
        }
        stations = list(cycle_times)
        before_values = [
            initial_takts.get(station, float(cycle_times[station]))
            for station in stations
        ]
        after_values = [float(cycle_times[station]) for station in stations]
        current_bar_colors = [
            "#d95d4f" if takt == bottleneck_takt else "#39856a"
            for takt in after_values
        ]

        figure = go.Figure(
            data=[
                go.Bar(
                    name="优化前（初始状态）",
                    x=stations,
                    y=before_values,
                    marker_color="#b8bec7",
                    text=[format_display_number(takt, 1) for takt in before_values],
                    textposition="outside",
                    hovertemplate="%{x}<br>优化前节拍：%{y:.1f} 秒<extra></extra>",
                ),
                go.Bar(
                    name="优化后（当前状态）",
                    x=stations,
                    y=after_values,
                    marker_color=current_bar_colors,
                    text=[format_display_number(takt, 1) for takt in after_values],
                    textposition="outside",
                    hovertemplate="%{x}<br>优化后节拍：%{y:.1f} 秒<extra></extra>",
                ),
            ]
        )
        figure.update_layout(
            height=420,
            margin={"l": 20, "r": 20, "t": 28, "b": 20},
            template="streamlit",
            barmode="group",
            showlegend=True,
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
            use_container_width=True,
            config={
                "displayModeBar": False,
                "staticPlot": True,
                "scrollZoom": False,
            },
        )
        initial_bottleneck, initial_bottleneck_takt = calc_line_takt(initial_takts)
        if initial_bottleneck_takt is not None:
            time_change = round(
                float(initial_bottleneck_takt) - float(bottleneck_takt), 1
            )
            if time_change > 0:
                time_summary = f"单件作业时间缩短了 {time_change:.1f} 秒"
            elif time_change < 0:
                time_summary = f"单件作业时间增加了 {abs(time_change):.1f} 秒"
            else:
                time_summary = "单件作业时间未变化"

            initial_capacity_24h = 86400 / float(initial_bottleneck_takt)
            current_capacity_24h = 86400 / float(bottleneck_takt)
            capacity_change = round(current_capacity_24h - initial_capacity_24h, 1)
            if capacity_change > 0:
                capacity_summary = f"理论产能提升了 {capacity_change:.1f} 件"
            elif capacity_change < 0:
                capacity_summary = f"理论产能减少了 {abs(capacity_change):.1f} 件"
            else:
                capacity_summary = "理论产能未变化"

            st.markdown(
                f"""
                <div style="padding: 16px 18px; border-left: 6px solid #39856a;
                            background: rgba(57, 133, 106, 0.12); border-radius: 8px;
                            font-size: 1.05rem; line-height: 1.7;">
                    <strong>优化效果：</strong>相比初始状态，{time_summary}
                    （原瓶颈 {format_display_number(initial_bottleneck_takt, 1)} 秒 →
                    现瓶颈 {format_display_number(bottleneck_takt, 1)} 秒）。
                    <br><strong>产能变化：</strong>产线 24 小时理论产能{capacity_summary}
                    （{format_display_number(initial_capacity_24h, 1)} 件 →
                    {format_display_number(current_capacity_24h, 1)} 件）。
                </div>
                """,
                unsafe_allow_html=True,
            )
            st.warning(
                f"当前瓶颈：{bottleneck} {format_display_number(bottleneck_takt, 1)} 秒"
            )

    with st.expander("📊 展开查看：成本与占地分析"):
        if not st.session_state["production_line"]:
            st.info("添加工位后将显示当前机型的成本与占地分析。")
        else:
            analysis_stations = []
            analysis_models = []
            analysis_costs = []
            analysis_areas = []
            for line_item in st.session_state["production_line"]:
                station_name = line_item["name"]
                model_name = str(line_item.get("model", "未配置"))
                model_rows = MODEL_LIBRARY[
                    MODEL_LIBRARY["机型"].astype(str) == model_name
                ]
                station_rows = model_rows[
                    model_rows["工位"].astype(str).map(
                        lambda label: normalize_station_label(label)
                        == normalize_station_label(station_name)
                    )
                ]
                if not station_rows.empty:
                    model_row = station_rows.iloc[0]
                elif not model_rows.empty:
                    model_row = model_rows.iloc[0]
                else:
                    model_row = None

                analysis_stations.append(station_name)
                analysis_models.append(model_name)

                # 优先使用工位级覆盖值（按比例缩放后的价格/占地）
                price_override = line_item.get("price")
                reach_override = line_item.get("reach")
                if price_override is not None:
                    cost_value = normalize_numeric(price_override) / 10000
                elif model_row is not None:
                    cost_value = normalize_numeric(
                        model_row.get("成本(万元)", 0)
                    )
                else:
                    cost_value = 0.0

                if reach_override is not None:
                    reach_mm = normalize_numeric(reach_override)
                    area_value = (reach_mm / 1000) ** 2 * 3.14
                elif model_row is not None:
                    area_value = normalize_numeric(
                        model_row.get("占地估算(㎡)", 0)
                    )
                else:
                    area_value = 0.0

                # 未配置机械臂或价格/臂展字段为空时按 0 兜底，保证坐标轴正常显示
                analysis_costs.append(max(cost_value, 0.0))
                analysis_areas.append(max(area_value, 0.0))
            has_cost_data = any(value > 0 for value in analysis_costs)
            has_area_data = any(value > 0 for value in analysis_areas)
            if not has_cost_data and not has_area_data:
                # 全部工位都没有可用机型数据时，不画只有坐标轴的空图
                st.info("暂无成本与占地数据，请先在左侧完成机械臂选型。")
            else:
                cost_axis_max = max(analysis_costs + [0.0])
                area_axis_max = max(analysis_areas + [0.0])
                cost_y_range = [0, round(max(cost_axis_max * 1.2, 1.0), 2)]
                area_y_range = [0, round(max(area_axis_max * 1.2, 1.0), 2)]
                st.caption("*注：未配置机械臂的工位按 0 计算。请在左侧完成选型。")

                theme_base = st.get_option("theme.base")
                plotly_theme = "plotly_dark" if theme_base == "dark" else "plotly_white"
                axis_color = (
                    "rgba(220, 220, 220, 0.3)"
                    if theme_base == "dark"
                    else "rgba(80, 80, 80, 0.2)"
                )
                analysis_left, analysis_right = st.columns(2)
                with analysis_left:
                    if not has_cost_data:
                        st.info("暂无成本数据，请先在左侧完成机械臂选型。")
                    else:
                        cost_figure = go.Figure(
                            go.Bar(
                                x=analysis_stations,
                                y=analysis_costs,
                                text=[f"{value:.2f}" for value in analysis_costs],
                                textposition="outside",
                                customdata=analysis_models,
                                marker_color="#39856a",
                                hovertemplate=(
                                    "%{x}<br>机型：%{customdata}"
                                    "<br>成本：%{y:.2f} 万元<extra></extra>"
                                ),
                            )
                        )
                        cost_figure.update_layout(
                            title="各工位机械臂成本对比图",
                            height=350,
                            template=plotly_theme,
                            margin=dict(l=50, r=20, t=30, b=50),
                            xaxis={"title": "工位", "showgrid": False},
                            yaxis={
                                "title": "成本（万元）",
                                "gridcolor": axis_color,
                                "rangemode": "tozero",
                                "range": cost_y_range,
                            },
                        )
                        st.plotly_chart(
                            cost_figure,
                            use_container_width=True,
                            config={
                                "displayModeBar": False,
                                "staticPlot": True,
                                "scrollZoom": False,
                            },
                        )

                with analysis_right:
                    if not has_area_data:
                        st.info("暂无占地数据，请先在左侧完成机械臂选型。")
                    else:
                        area_figure = go.Figure(
                            go.Bar(
                                x=analysis_stations,
                                y=analysis_areas,
                                text=[f"{value:.2f}" for value in analysis_areas],
                                textposition="outside",
                                customdata=analysis_models,
                                marker_color="#5479a8",
                                hovertemplate=(
                                    "%{x}<br>机型：%{customdata}"
                                    "<br>占地：%{y:.2f} ㎡<extra></extra>"
                                ),
                            )
                        )
                        area_figure.update_layout(
                            title="各工位占地空间对比图",
                            height=350,
                            template=plotly_theme,
                            margin=dict(l=50, r=20, t=30, b=50),
                            xaxis={"title": "工位", "showgrid": False},
                            yaxis={
                                "title": "占地（平方米）",
                                "gridcolor": axis_color,
                                "rangemode": "tozero",
                                "range": area_y_range,
                            },
                        )
                        st.plotly_chart(
                            area_figure,
                            use_container_width=True,
                            config={
                                "displayModeBar": False,
                                "staticPlot": True,
                                "scrollZoom": False,
                            },
                        )
