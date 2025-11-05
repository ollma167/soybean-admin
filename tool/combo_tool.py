import streamlit as st
import pandas as pd
import json
import re
import copy
import time
from io import BytesIO
from typing import List, Dict, Any, Tuple
from collections import Counter
import plotly.express as px
import plotly.graph_objects as go
import requests


def format_number_chinese(value):
    """将数字格式化为中文单位：万（w）、亿等"""
    if pd.isna(value) or value == 0:
        return "0"
    
    abs_value = abs(value)
    sign = "-" if value < 0 else ""
    
    if abs_value >= 100000000:  # 1亿
        return f"{sign}{abs_value/100000000:.2f}亿"
    elif abs_value >= 10000:  # 1万
        return f"{sign}{abs_value/10000:.2f}w"
    elif abs_value >= 1000:  # 1千
        return f"{sign}{abs_value/1000:.2f}k"
    else:
        return f"{sign}{abs_value:.2f}"


def update_xaxis_ticks(fig, x_axis_data, angle, interval_threshold, interval_step):
    x_labels = pd.unique(x_axis_data)
    num_x_items = len(x_labels)

    tickvals, ticktext = None, None
    x_range = None # Initialize x_range

    # Apply special tick logic only for categorical data when items are many
    # For numerical data, let Plotly handle tick generation automatically
    if x_axis_data.dtype == 'object' and num_x_items > interval_threshold:
        tickvals = list(x_labels)
        ticktext = [str(label) for label in x_labels]

        for i in range(1, num_x_items - 1): # Keep first, check others
            if i % interval_step != 0:
                ticktext[i] = ""

        # Ensure last is visible, and hide second-to-last to avoid crowding
        if num_x_items > 1:
            ticktext[-2] = ""
            ticktext[-1] = str(x_labels[-1])
    elif pd.api.types.is_numeric_dtype(x_axis_data):
        # For numerical data, ensure the range covers the max value
        x_min = x_axis_data.min()
        x_max = x_axis_data.max()
        x_range = [x_min, x_max * 1.05] # Add a 5% buffer to the max to ensure it's fully visible

    fig.update_xaxes(tickangle=angle, tickvals=tickvals, ticktext=ticktext, automargin=True, range=x_range)
    return fig

def update_yaxis_range(fig, y_axis_data, use_chinese_format=True, yaxis_num=1):
    """更新Y轴范围和格式"""
    # Let Plotly's autorange handle the limits, but ensure the range extends to zero.
    yaxis_key = 'yaxis' if yaxis_num == 1 else f'yaxis{yaxis_num}'
    
    if use_chinese_format:
        # 获取Y轴数据的最大值来确定tickformat
        max_val = y_axis_data.max() if hasattr(y_axis_data, 'max') else max(y_axis_data)
        
        # 创建自定义的tickvals和ticktext
        fig.update_layout({
            yaxis_key: dict(
                rangemode="tozero",
                autorange=True,
                tickformat="",
                tickmode="auto"
            )
        })
        
        # 使用tickformatstops来自定义格式
        if yaxis_num == 1:
            fig.update_yaxes(rangemode="tozero", autorange=True)
        else:
            fig.update_layout({yaxis_key: dict(rangemode="tozero", autorange=True)})
    else:
        if yaxis_num == 1:
            fig.update_yaxes(rangemode="tozero", autorange=True)
        else:
            fig.update_layout({yaxis_key: dict(rangemode="tozero", autorange=True)})
    
    return fig


def apply_chinese_yaxis_format(fig, yaxis_num=1):
    """应用中文Y轴格式到图表"""
    yaxis_key = 'yaxis' if yaxis_num == 1 else f'yaxis{yaxis_num}'
    
    # 使用自定义的tickformat函数
    fig.update_layout({
        yaxis_key: dict(
            tickformat="",
            tickmode="auto",
        )
    })
    
    # 获取当前的traces并更新hover模板
    for trace in fig.data:
        if hasattr(trace, 'y') and trace.y is not None:
            # 更新hover模板以显示中文格式
            if hasattr(trace, 'hovertemplate') and trace.hovertemplate:
                # 保持现有的hovertemplate
                pass
    
    return fig

# ============================
# App Config
# ============================
st.set_page_config(page_title="组合装生成工具 · 简约专业版", page_icon="🧩", layout="centered")

# 主题样式渲染坑位（确保每次只保留一份 <style>）
if "__theme_slot" not in st.session_state:
    st.session_state["__theme_slot"] = st.empty()

# ---------- Design Tokens ----------
def inject_theme(theme_mode: str):
    if theme_mode == "深色":
        css_vars = """
        :root {
          --bg: #0f1115; --card: #161a20; --text: #e8eaf0; --muted: #9aa0aa;
          --border: rgba(255,255,255,.08); --shadow: 0 8px 30px rgba(0,0,0,.35);
          --accent: #10a37f; --accent-weak: #143c32; --hover: rgba(255,255,255,.04);
          --chip: #20242c;
        }"""
    else:
        css_vars = """
        :root {
          --bg: #f7f7f8; --card: #ffffff; --text: #111318; --muted: #61646b;
          --border: rgba(0,0,0,.08); --shadow: 0 10px 30px rgba(0,0,0,.06);
          --accent: #10a37f; --accent-weak: #e6faf2; --hover: rgba(0,0,0,.03);
          --chip: #f0f2f5;
        }"""

    base_css = """
      * { -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale; }
      .block-container { padding-top: .5rem; padding-bottom: 2rem; }
      body, .block-container, .stApp { background: var(--bg); color: var(--text); }
      h1, h2, h3, h4 { letter-spacing: .2px; }
      .hero { padding: 8px 12px 4px 12px; margin: 0 0 10px 0; }
      .hero h1 { font-size: 22px; margin:0; }
      .subtle { color: var(--muted); font-size: 12px; }
      .card { border-radius: 12px; border: 1px solid var(--border); padding: 14px; margin-bottom: 10px; background: var(--card); box-shadow: var(--shadow); transition: all .2s ease-out; }
      .card:hover { transform: translateY(-2px); border-color: var(--accent); }
      .card-muted { border-radius: 12px; border: 1px dashed var(--border); background: transparent; }
      .card-ghost { border-radius: 12px; border: 1px solid transparent; background: transparent; padding: 4px 6px; }
      .section-title { font-weight: 600; font-size: 15px; margin-bottom: 8px; color: var(--accent); }
      .chip { display:inline-block; padding: 5px 9px; border-radius: 999px; background: var(--chip); color: var(--muted); margin-right: 5px; margin-bottom: 5px; font-size: 12px; border: 1px solid var(--border); }
      .stButton>button, .stDownloadButton>button { border-radius: 8px; border: 1px solid var(--border); transition: all .18s ease; box-shadow: none; }
      .stButton>button:hover, .stDownloadButton>button:hover { transform: translateY(-1px); background: var(--hover); }
      .stButton>button:active, .stDownloadButton>button:active { transform: translateY(0); }
      .accent { color: var(--accent); }
      .accent-bg { background: var(--accent-weak); border-color: rgba(16,163,127,.28) !important; }
      .muted { color: var(--muted); }
      .divider { border:none; border-top:1px solid var(--border); margin: 8px 0; }
      .toolbar-sticky { position: sticky; top: 6px; z-index: 5; }
      .tpl-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
      .tpl-card { border-radius: 12px; border: 1px solid var(--border); background: var(--card); padding: 12px; box-shadow: var(--shadow); display: flex; align-items: center; justify-content: space-between; }
      .tpl-name { font-weight: 600; font-size: 15px; overflow:hidden; text-overflow: ellipsis; white-space: nowrap; }
      .nav-card { border:1px solid var(--border); border-radius:10px; padding:8px 10px; margin-bottom:8px; }
      .nav-card.active { background: var(--accent-weak); border-color: rgba(16,163,127,.28); }
      .nav-card .stButton>button { width:100%; border-radius:8px; }
      div[data-testid="stColorPicker"] {
        display: flex;
        align-items: center;
        justify-content: space-between;
        border: 1px solid var(--border);
        background: var(--chip);
        border-radius: 8px;
        padding: 4px 10px;
        width: 100%;
        box-sizing: border-box;
      }
      div[data-testid="stColorPicker"] p {
        font-size: 12px;
        margin-bottom: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
        margin-right: 8px;
      }
      div[data-testid="stColorPicker"] > div {
        flex-shrink: 0;
      }
      section[data-testid="stSidebar"] { width: 260px; min-width: 260px; background: transparent; }
      section[data-testid="stSidebar"] .block-container { padding-top: 10px; }
      div[data-testid="stVerticalBlock"] { gap: 0.6rem; }
      div[data-testid="stExpander"] { margin-top: 0; }
      div[data-testid="stTextInput"] input, div[data-testid="stNumberInput"] input { padding-top: 0.35rem; padding-bottom: 0.35rem; }
      .stButton>button, .stDownloadButton>button { padding-top: 0.35rem; padding-bottom: 0.35rem; }
      .stButton>button[kind="primary"], .stDownloadButton>button[kind="primary"] { 
        background: linear-gradient(135deg, var(--accent) 0%, #0d8a6a 100%);
        color: white; border: none; font-weight: 600;
      }
      .stButton>button[kind="primary"]:hover, .stDownloadButton>button[kind="primary"]:hover {
        background: linear-gradient(135deg, #0d8a6a 0%, var(--accent) 100%);
        transform: translateY(-2px); box-shadow: 0 4px 12px rgba(16,163,127,.3);
      }
      .stSpinner>div { border-top-color: var(--accent) !important; }
      div[data-testid="stImage"] { border-radius: 8px; overflow: hidden; }
      div[data-testid="stImage"] img { transition: transform .2s ease; }
      div[data-testid="stImage"]:hover img { transform: scale(1.02); }
      div[data-testid="stExpander"] { 
        border: 1px solid var(--border); border-radius: 8px; 
        background: var(--card); margin: 8px 0;
      }
      div[data-testid="stToolbar"] { visibility: hidden; height: 0; position: fixed; }
      footer { visibility: hidden; }
      #MainMenu { visibility: hidden; }

      body:before {
        content: ''; position: fixed; top: -30%; left: -20%; width: 70vw; height: 70vw;
        background: radial-gradient(circle, var(--accent-weak) 0%, transparent 60%);
        z-index: -1; pointer-events: none; opacity: 0.7; filter: blur(20px);
      }
      body:after {
        content: ''; position: fixed; bottom: -30%; right: -20%; width: 70vw; height: 70vw;
        background: radial-gradient(circle, var(--accent-weak) 0%, transparent 60%);
        z-index: -1; pointer-events: none; opacity: 0.7; filter: blur(20px);
      }

      @media (max-width: 1200px) {
        body:before, body:after { display: none; }
      }
      @media (max-width: 900px) {
        .block-container { padding-left: .5rem; padding-right: .5rem; }
        .card { padding: 10px; }
        .tpl-grid { grid-template-columns: 1fr; }
      }
    """
    st.session_state["__theme_slot"].markdown("<style>" + css_vars + base_css + "</style>", unsafe_allow_html=True)

# ============================
# Data/Domain Config
# ============================
TEMPLATE_COLUMNS = [
    '组合商品编码','组合装商品标签','组合款式编码','组合商品名称','组合商品简称','组合商品实体编码',
    '虚拟分类','组合颜色规格','禁止库存同步','商品编码','数量','应占售价','基本售价','组合成本价','图片','品牌'
]
TEMPLATE_FILE = "templates.json"
TEMPLATE_LIMIT = 999
COMBO_LIMIT_PER_TEMPLATE = 100
ADHOC_COMBO_LIMIT = 100

# ============================
# Helpers
# ============================
def _lines(raw: str):
    if not raw or not raw.strip(): return []
    return [s.strip() for s in raw.strip().splitlines() if s.strip()]

def _num(val, default):
    if val is None or str(val).strip() == "": return default
    try:
        f = float(str(val));  i = int(f)
        return i if abs(f - i) < 1e-9 else f
    except:
        return default

@st.cache_resource
def load_templates() -> List[Dict[str, Any]]:
    try:
        with open(TEMPLATE_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        templates = data["templates"] if isinstance(data, dict) and "templates" in data else (data if isinstance(data, list) else [])
        normalized = []
        for t in templates:
            if "combos" in t:
                normalized.append(t)
            else:
                normalized.append({"name": t.get("name",""), "combos": [{"prefix": t.get("prefix",""), "items": t.get("items", [])}]})
        return normalized[:TEMPLATE_LIMIT]
    except FileNotFoundError:
        return []
    except Exception as e:
        st.warning(f"读取模板失败：{e}")
        return []

def save_templates(templates: List[Dict[str, Any]]):
    data = {"templates": templates[:TEMPLATE_LIMIT]}
    with open(TEMPLATE_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def parse_items_block_codes_default1(text: str) -> List[Dict[str, Any]]:
    items = []
    for line in _lines(text):
        parts = [p.strip() for p in line.split(",")]
        if not parts:
            continue
        code = parts[0]
        qty  = _num(parts[1] if len(parts)>1 else "", 1)
        p1   = _num(parts[2] if len(parts)>2 else "", 1.0)
        p2   = _num(parts[3] if len(parts)>3 else "", 1.0)
        cost = _num(parts[4] if len(parts)>4 else "", 1.0)
        items.append({"商品编码": code, "数量": qty, "应占售价": p1, "基本售价": p2, "组合成本价": cost})
    return items

def render_sub_items_editor(session_key_prefix: str, initial_items: List[Dict[str, Any]] = None):
    """Renders a sub-items editor block with detailed inputs and paste functionality."""
    initial_items = initial_items or []
    
    items_key = f"{session_key_prefix}_items"
    if items_key not in st.session_state:
        st.session_state[items_key] = copy.deepcopy(initial_items)

    st.markdown("###### ⚡️ 副商品明细（可微调）")
    
    items_data = st.session_state[items_key]
    for i, item in enumerate(items_data):
        cols = st.columns([2, 1, 1, 1, 1, 1])
        items_data[i]['商品编码'] = cols[0].text_input("商品编码", value=item.get("商品编码", ""), key=f"{session_key_prefix}_{i}_code")
        items_data[i]['数量'] = cols[1].number_input("数量", min_value=1, step=1, value=item.get("数量", 1), key=f"{session_key_prefix}_{i}_qty")
        items_data[i]['应占售价'] = cols[2].number_input("应占售价", min_value=0.0, step=0.1, value=float(item.get("应占售价", 1.0)), format="%.4f", key=f"{session_key_prefix}_{i}_p1")
        items_data[i]['基本售价'] = cols[3].number_input("基本售价", min_value=0.0, step=0.1, value=float(item.get("基本售价", 1.0)), format="%.4f", key=f"{session_key_prefix}_{i}_p2")
        items_data[i]['组合成本价'] = cols[4].number_input("成本价", min_value=0.0, step=0.1, value=float(item.get("组合成本价", 1.0)), format="%.4f", key=f"{session_key_prefix}_{i}_cost")
        with cols[5]:
            st.write("") 
            st.write("")
            if st.button("🗑️", key=f"delete_{session_key_prefix}_{i}"):
                st.session_state[f'confirm_delete_item_{session_key_prefix}'] = i
                st.rerun()

    confirm_key = f'confirm_delete_item_{session_key_prefix}'
    if st.session_state.get(confirm_key) is not None:
        item_idx = st.session_state[confirm_key]
        st.warning(f"确定要删除副商品 {items_data[item_idx].get('商品编码', '')} 吗？")
        c1, c2 = st.columns(2)
        if c1.button("确认删除", key=f"confirm_del_item_{session_key_prefix}"):
            st.session_state[items_key].pop(item_idx)
            del st.session_state[confirm_key]
            st.rerun()
        if c2.button("取消", key=f"cancel_del_item_{session_key_prefix}"):
            del st.session_state[confirm_key]
            st.rerun()

    if st.button("➕ 添加一个副商品", key=f"add_empty_{session_key_prefix}"):
        st.session_state[items_key].append({"商品编码": "", "数量": 1, "应占售价": 1.0, "基本售价": 1.0, "组合成本价": 1.0})
        st.rerun()

    paste_key = f"paste_{session_key_prefix}"
    pasted_text = st.text_area("在此粘贴副商品", key=paste_key, height=100)
    
    if st.button("➕ 添加粘贴内容", key=f"add_paste_{session_key_prefix}"):
        if pasted_text:
            new_items = parse_items_block_codes_default1(pasted_text)
            st.session_state[items_key].extend(new_items)
            st.session_state[paste_key] = ""
            st.rerun()

    return st.session_state[items_key]

def _apply_rules_on_body(body: str, rules: List[Tuple[str, str]], use_regex: bool, case_sensitive: bool) -> str:
    flags = 0 if case_sensitive else re.IGNORECASE
    for old, new in rules:
        if old == "":
            continue
        if use_regex:
            try:
                body = re.sub(old, new, body, flags=flags)
            except re.error:
                body = body.replace(old, new) if case_sensitive else re.compile(re.escape(old), re.IGNORECASE).sub(new, body)
        else:
            body = body.replace(old, new) if case_sensitive else re.compile(re.escape(old), re.IGNORECASE).sub(new, body)
    return body

def apply_code_simplify(original: str, prefix: str, rules: List[Tuple[str, str]], use_regex: bool, case_sensitive: bool) -> str:
    head, body = (prefix, original[len(prefix):]) if original.startswith(prefix) else ("", original)
    body = _apply_rules_on_body(body, rules, use_regex, case_sensitive)
    return f"{head}{body}"

def apply_name_simplify(name: str, prefix: str, rules: List[Tuple[str, str]], use_regex: bool, case_sensitive: bool) -> str:
    head, tail = (prefix, name[len(prefix):]) if name.startswith(prefix) else ("", name)
    tail = _apply_rules_on_body(tail, rules, use_regex, case_sensitive)
    return f"{head}{tail}"

def build_rows(main_products_df, combos, simplify_rules=None, use_regex=False, case_sensitive=True, apply_to_name=False):
    rows = []
    simplify_rules = simplify_rules or []
    for prefix, items in combos:
        for _, main_prod_row in main_products_df.iterrows():
            code, spec = str(main_prod_row.get("主商品编码", "")), str(main_prod_row.get("主商品组合颜色规格", ""))
            qty, price1, price2, cost = _num(main_prod_row.get("数量"), 1), _num(main_prod_row.get("应占售价"), 1.0), _num(main_prod_row.get("基本售价"), 1.0), _num(main_prod_row.get("成本价"), 1.0)
            if not code or not spec: continue

            combo_code_raw = f"{prefix}{code}"
            combo_code_final = apply_code_simplify(combo_code_raw, prefix, simplify_rules, use_regex, case_sensitive)
            combo_name_raw = f"{prefix}{spec}"
            combo_name_final = apply_name_simplify(combo_name_raw, prefix, simplify_rules, use_regex, case_sensitive) if apply_to_name else combo_name_raw

            # Calculate totals from sub-items
            total_sub_price1 = sum(_num(it.get('应占售价', 1.0), 1.0) * _num(it.get('数量', 1), 1) for it in items)
            total_sub_price2 = sum(_num(it.get('基本售价', 1.0), 1.0) * _num(it.get('数量', 1), 1) for it in items)
            total_sub_cost = sum(_num(it.get('组合成本价', 1.0), 1.0) * _num(it.get('数量', 1), 1) for it in items)

            # Main combo row with calculated totals
            main_row = {col: "" for col in TEMPLATE_COLUMNS}
            main_row.update({
                '组合商品编码': combo_code_final,
                '组合商品名称': combo_name_final,
                '组合颜色规格': spec,
                '商品编码': code,
                '数量': qty,
                '应占售价': price1 + total_sub_price1,
                '基本售价': price2 + total_sub_price2,
                '组合成本价': cost + total_sub_cost
            })
            rows.append(main_row)

            for it in items:
                sub_row = {col: "" for col in TEMPLATE_COLUMNS}
                sub_row.update({'商品编码': it['商品编码'], '数量': _num(it.get('数量', 1), 1), '应占售价': _num(it.get('应占售价', 1.0), 1.0), '基本售价': _num(it.get('基本售价', 1.0), 1.0), '组合成本价': _num(it.get('组合成本价', 1.0), 1.0)})
                rows.append(sub_row)
    return rows


def build_rows_pairwise(main_products_df, per_main_pairs, simplify_rules=None, use_regex=False, case_sensitive=True, apply_to_name=False):
    rows = []
    simplify_rules = simplify_rules or []
    # per_main_pairs: list of tuples (prefix, items) aligned with main_products_df rows
    for idx, (_, main_prod_row) in enumerate(main_products_df.iterrows()):
        prefix, items = ("", [])
        if idx < len(per_main_pairs):
            prefix, items = per_main_pairs[idx]
        code, spec = str(main_prod_row.get("主商品编码", "")), str(main_prod_row.get("主商品组合颜色规格", ""))
        qty, price1, price2, cost = _num(main_prod_row.get("数量"), 1), _num(main_prod_row.get("应占售价"), 1.0), _num(main_prod_row.get("基本售价"), 1.0), _num(main_prod_row.get("成本价"), 1.0)
        if not code or not spec: 
            continue
        combo_code_raw = f"{prefix}{code}"
        combo_code_final = apply_code_simplify(combo_code_raw, prefix, simplify_rules, use_regex, case_sensitive)
        combo_name_raw = f"{prefix}{spec}"
        combo_name_final = apply_name_simplify(combo_name_raw, prefix, simplify_rules, use_regex, case_sensitive) if apply_to_name else combo_name_raw

        total_sub_price1 = sum(_num(it.get('应占售价', 1.0), 1.0) * _num(it.get('数量', 1), 1) for it in items)
        total_sub_price2 = sum(_num(it.get('基本售价', 1.0), 1.0) * _num(it.get('数量', 1), 1) for it in items)
        total_sub_cost = sum(_num(it.get('组合成本价', 1.0), 1.0) * _num(it.get('数量', 1), 1) for it in items)

        main_row = {col: "" for col in TEMPLATE_COLUMNS}
        main_row.update({
            '组合商品编码': combo_code_final,
            '组合商品名称': combo_name_final,
            '组合颜色规格': spec,
            '商品编码': code,
            '数量': qty,
            '应占售价': price1 + total_sub_price1,
            '基本售价': price2 + total_sub_price2,
            '组合成本价': cost + total_sub_cost
        })
        rows.append(main_row)
        for it in items:
            sub_row = {col: "" for col in TEMPLATE_COLUMNS}
            sub_row.update({'商品编码': it['商品编码'], '数量': _num(it.get('数量', 1), 1), '应占售价': _num(it.get('应占售价', 1.0), 1.0), '基本售价': _num(it.get('基本售价', 1.0), 1.0), '组合成本价': _num(it.get('组合成本价', 1.0), 1.0)})
            rows.append(sub_row)
    return rows

def suggest_tokens_from_codes(codes: List[str], min_ratio: float = 0.6) -> Dict[str, Any]:
    sug = {"lcp": "", "tokens": []}
    if not codes: return sug
    lcp = codes[0]
    for s in codes[1:]:
        i = 0
        while i < len(lcp) and i < len(s) and lcp[i] == s[i]: i += 1
        lcp = lcp[:i]
        if not lcp: break
    sug["lcp"] = lcp if len(lcp) >= 2 else ""
    token_lists = [set(t for t in re.split(r"[^A-Za-z0-9]+", s) if t) for s in codes]
    freq = Counter(t for ts in token_lists for t in ts)
    picked = sorted([(t, c) for t, c in freq.items() if c / len(codes) >= min_ratio and len(t) >= 2], key=lambda x: (-x[1], -len(x[0]), x[0]))
    sug["tokens"] = picked[:10]
    return sug

for k, v in {'temp_edits': {}, 'generated_df': None, 'txt_main_codes': "", 'txt_main_specs': "", 'rules_df': pd.DataFrame(columns=["顺序","要替换/删除","替换为（留空=删除）"]), 'show_new_tpl_modal': False, 'tpl_manage_view': 'list', 'tpl_edit_index': None, 'gen_mode': 'template', 'theme_mode': '浅色', 'page': '🚀 生成组合装', 'tpl_search': '', '__show_save_tpl_modal': False, '__pending_tpl_payload': None, '__last_saved_tpl_name': None, '__dup_modal_idx': None, '__del_modal_idx': None, '__dup_edit_flag': False, 'selected_templates_for_batch': [], 'tpl_page': 0, 'analysis_mode': '单个文件图表', 'last_fig': None, 'allow_no_subitems': False}.items():
    if k not in st.session_state: st.session_state[k] = v

with st.sidebar:
    st.markdown("<div class='hero'><h1>🧩 组合装生成</h1><div class='subtle'>简约专业版</div></div>", unsafe_allow_html=True)
    for label in ["🚀 生成组合装", "🧱 模板管理", "📊 图表生成", "📱 抖音下载"]:
        active = " active" if st.session_state['page'] == label else ""
        st.markdown(f"<div class='nav-card{active}'>", unsafe_allow_html=True)
        if st.button(label, use_container_width=True, key=f"nav_{label}"): st.session_state['page'] = label
        st.markdown("</div>", unsafe_allow_html=True)

inject_theme(st.session_state['theme_mode'])
templates = load_templates()
template_names = [t["name"] for t in templates]
page = st.session_state['page']

if page == "🚀 生成组合装":
    def clear_main_codes():
        st.session_state.txt_main_codes = ""
    def clear_main_specs():
        st.session_state.txt_main_specs = ""

    st.markdown("<div class='card-ghost'><div class='section-title'>📝 主商品</div></div>", unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    top_left, top_right = st.columns([1,1], gap="large")
    with top_left: st.text_area("主商品编码（每行一个）", height=160, placeholder="M001\nM002\nM003", key="txt_main_codes")
    with top_right: st.text_area("主商品组合颜色规格（每行一个）", height=160, placeholder="深蓝色-16\n深蓝色-18\n深蓝色-20", key="txt_main_specs")

    c_a, c_b, c_c = st.columns([1,1,2])
    with c_a:
        st.button("清空编码", key="clear_codes", use_container_width=True, on_click=clear_main_codes)
    with c_b:
        st.button("清空规格", key="clear_specs", use_container_width=True, on_click=clear_main_specs)
    with c_c:
        codes, specs = _lines(st.session_state["txt_main_codes"]), _lines(st.session_state["txt_main_specs"])
        if len(codes) > 0 and len(codes) == len(specs): st.markdown("<span class='chip accent-bg'>数量匹配 ✅</span>", unsafe_allow_html=True)
        elif len(codes) > 0 or len(specs) > 0: st.markdown(f"<span class='chip' style='border-color:#f59e0b;color:#b45309;background:#fff7ed;'>数量不一致：编码 {len(codes)} vs 规格 {len(specs)}</span>", unsafe_allow_html=True)

    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    mode = st.session_state.get("gen_mode", "template" if template_names else "adhoc")

    # 生成选项
    st.markdown("<div class='card-ghost'><div class='section-title'>⚙️ 生成选项</div></div>", unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    if mode == 'adhoc':
        st.checkbox(
            "允许不添加副商品，仅主商品生成",
            value=st.session_state.get('allow_no_subitems', False),
            key="allow_no_subitems"
        )
        st.caption("启用后：不录入副商品也可生成，但每个主商品数量必须≥2。")
    elif mode == 'per_main':
        st.info("空模板模式将默认副商品为空，您可在下方为每个主商品添加或编辑副商品。若某主商品无副商品，则其数量必须≥2。")
    else:
        st.caption("使用模板模式：请选择需要的模板并可进行临时微调。")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("###### 🔢 主商品明细")

    with st.container():
        st.markdown("###### ⚡️ 批量修改（统一设置下方所有主商品）")
        batch_cols = st.columns([1, 1, 1, 1, 2])
        min_qty = 2 if (st.session_state.get("allow_no_subitems", False) and st.session_state.get("gen_mode", "template") == "adhoc") else 1
        if (st.session_state.get("allow_no_subitems", False) and st.session_state.get("gen_mode", "template") == "adhoc") and st.session_state.get("batch_qty_input", 1) < 2:
            st.session_state["batch_qty_input"] = 2
        with batch_cols[0]: batch_qty = st.number_input("统一数量", min_value=min_qty, step=1, value=min_qty, key="batch_qty_input")
        with batch_cols[1]: batch_price1 = st.number_input("统一应占售价", min_value=0.0, step=0.1, value=1.0, format="%.4f", key="batch_price1_input")
        with batch_cols[2]: batch_price2 = st.number_input("统一基本售价", min_value=0.0, step=0.1, value=1.0, format="%.4f", key="batch_price2_input")
        with batch_cols[3]: batch_cost = st.number_input("统一成本", min_value=0.0, step=0.1, value=1.0, format="%.4f", key="batch_cost_input")
        with batch_cols[4]:
            st.write(""); st.write("")
            if st.button("➡️ 应用批量修改", key="btn_apply_batch", use_container_width=True):
                for i in range(len(_lines(st.session_state["txt_main_codes"]))):
                    st.session_state[f"main_qty_{i}"] = batch_qty
                    st.session_state[f"main_price1_{i}"] = batch_price1
                    st.session_state[f"main_price2_{i}"] = batch_price2
                    st.session_state[f"main_cost_{i}"] = batch_cost
                st.success("已应用批量修改。"); st.rerun()

    if codes and specs and len(codes) == len(specs):
        for i, (code, spec) in enumerate(zip(codes, specs)):
            default_qty = 2 if (st.session_state.get("allow_no_subitems", False) and st.session_state.get("gen_mode", "template") == "adhoc") else 1
            st.session_state.setdefault(f"main_qty_{i}", default_qty)
            if (st.session_state.get("allow_no_subitems", False) and st.session_state.get("gen_mode", "template") == "adhoc") and st.session_state.get(f"main_qty_{i}", 1) < 2:
                st.session_state[f"main_qty_{i}"] = 2
            st.session_state.setdefault(f"main_price1_{i}", 1.0)
            st.session_state.setdefault(f"main_price2_{i}", 1.0)
            st.session_state.setdefault(f"main_cost_{i}", 1.0)
            cols = st.columns([2, 2, 1, 1, 1, 1])
            with cols[0]: st.text_input("编码", value=code, key=f"main_code_{i}", disabled=True)
            with cols[1]: st.text_input("规格", value=spec, key=f"main_spec_{i}", disabled=True)
            with cols[2]: st.number_input("数量", min_value=default_qty, step=1, key=f"main_qty_{i}")
            with cols[3]: st.number_input("应占售价", min_value=0.0, step=0.1, format="%.4f", key=f"main_price1_{i}")
            with cols[4]: st.number_input("基本售价", min_value=0.0, step=0.1, format="%.4f", key=f"main_price2_{i}")
            with cols[5]: st.number_input("成本价", min_value=0.0, step=0.1, format="%.4f", key=f"main_cost_{i}")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div class='card-ghost'><div class='section-title'>🧰 方式选择</div></div>", unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    ca, cb, cc = st.columns(3)
    with ca:
        if st.button("无模板 · 表格录入副商品", use_container_width=True, key="btn_mode_adhoc"): st.session_state["gen_mode"] = "adhoc"
    with cb:
        if st.button("使用模板 · 从库中选择", use_container_width=True, key="btn_mode_tpl"): st.session_state["gen_mode"] = "template"
    with cc:
        if st.button("空模板 · 每个主商品自定义", use_container_width=True, key="btn_mode_permain"): st.session_state["gen_mode"] = "per_main"
    mode = st.session_state.get("gen_mode", "template" if template_names else "adhoc")
    if mode == 'adhoc':
        st.caption("当前模式：**无模板**")
    elif mode == 'template':
        st.caption("当前模式：**使用模板**")
    else:
        st.caption("当前模式：**空模板（按主商品自定义）**")
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div class='card-ghost'><div class='section-title'>🧹 编码简化（不改前缀） · 高级选项</div></div>", unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)
    with st.expander("展开/收起高级选项", expanded=False):
        enable_simplify, use_regex, case_sensitive, apply_to_name = st.checkbox("启用编码简化", value=True), st.checkbox("使用正则表达式", value=False), st.checkbox("大小写敏感", value=True), st.checkbox("同时对组合商品名称应用同样规则（前缀仍不改）", value=False)
        
        if 'simplify_rules' not in st.session_state:
            st.session_state['simplify_rules'] = []

        for i, rule in enumerate(st.session_state['simplify_rules']):
            cols = st.columns([2, 2, 1])
            st.session_state['simplify_rules'][i]['find'] = cols[0].text_input("要替换/删除", value=rule.get('find', ''), key=f"rule_find_{i}")
            st.session_state['simplify_rules'][i]['replace'] = cols[1].text_input("替换为", value=rule.get('replace', ''), key=f"rule_replace_{i}")
            with cols[2]:
                st.write("")
                st.write("")
                if st.button("🗑️", key=f"delete_rule_{i}"):
                    st.session_state['simplify_rules'].pop(i)
                    st.rerun()
        
        if st.button("➕ 添加规则"):
            st.session_state['simplify_rules'].append({'find': '', 'replace': ''})
            st.rerun()

    st.markdown('</div>', unsafe_allow_html=True)

    adhoc_combos = []
    if mode == "adhoc":
        st.markdown("<div class='card-ghost'><div class='section-title'>🧩 无模板 · 临时副商品</div></div>", unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        adhoc_count = st.number_input("临时组合套数", min_value=1, max_value=ADHOC_COMBO_LIMIT, value=1, step=1, key="adhoc_count")
        cclear, cspacer = st.columns([1,3])
        with cclear:
            if st.button("一键清空所有副商品", key="btn_clear_adhoc_all", use_container_width=True):
                for i in range(int(st.session_state.get("adhoc_count", 1))):
                    st.session_state[f"adhoc_{i}_items"] = []
                st.success("已清空所有副商品，当前将仅主商品参与生成。")
                st.rerun()
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        for i in range(int(adhoc_count)):
            prefix_val = st.session_state.get(f"adhoc_prefix_{i}", "")
            label = prefix_val if prefix_val else f"临时组合 {i+1}"
            with st.expander(label, expanded=True):
                prefix = st.text_input(f"前缀（临时 {i+1}）", key=f"adhoc_prefix_{i}", placeholder="如：DK_")
                if st.session_state.get('allow_no_subitems', False):
                    st.info("本组不添加副商品，仅主商品参与生成。")
                    items = []
                else:
                    items = render_sub_items_editor(session_key_prefix=f"adhoc_{i}")
                adhoc_combos.append({"prefix": prefix or "", "items": items})
        st.markdown('</div>', unsafe_allow_html=True)

    if mode == "template":
        st.markdown("<div class='card-ghost'><div class='section-title'>📚 选择模板</div></div>", unsafe_allow_html=True)
        st.markdown('<div class="card card-muted">', unsafe_allow_html=True)
        if template_names: selected_templates = st.multiselect("从模板库中选择（可多选）", options=template_names, default=[], key="gen_tpl_select")
        else: st.info("暂无模板，请先到『模板管理』创建。")
        st.markdown('</div>', unsafe_allow_html=True)
        if selected_templates:
            with st.expander("🛠️ 模板临时微调（仅本次）", expanded=False):
                st.caption("修改仅在本次生成中有效，不会保存到模板库。")
                for tname in selected_templates:
                    tpl = next((t for t in templates if t['name'] == tname), None)
                    if not tpl: continue
                    with st.expander(f"模板：{tname}", expanded=False):
                        for ci, combo in enumerate(tpl.get('combos', [])):
                            prefix_val = combo.get('prefix', '')
                            label = prefix_val if prefix_val else f"组合 {ci+1}"
                            with st.expander(label, expanded=False):
                                prefix = st.text_input("前缀", value=prefix_val, key=f"tmp_edit_{tname}_{ci}_prefix")
                                render_sub_items_editor(
                                    session_key_prefix=f"tmp_edit_{tname}_{ci}",
                                    initial_items=combo.get("items", [])
                                )

    if mode == "per_main":
        st.markdown("<div class='card-ghost'><div class='section-title'>🧩 空模板 · 每个主商品自定义</div></div>", unsafe_allow_html=True)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        # 批量操作
        c1, c2 = st.columns([1, 3])
        with c1:
            if st.button("清空全部副商品", key="btn_clear_permain_all", use_container_width=True):
                for i in range(len(_lines(st.session_state["txt_main_codes"]))):
                    st.session_state[f"permain_{i}_items"] = []
                st.success("已清空全部副商品。")
                st.rerun()
        st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
        # 每个主商品配置
        if codes and specs and len(codes) == len(specs):
            for i, (code, spec) in enumerate(zip(codes, specs)):
                with st.expander(f"主商品 {i+1} · {code}", expanded=False):
                    st.text_input("前缀", value=st.session_state.get(f"permain_{i}_prefix", ""), key=f"permain_{i}_prefix")
                    render_sub_items_editor(session_key_prefix=f"permain_{i}", initial_items=[])
        else:
            st.info("请先在上方输入并对齐主商品编码与规格，然后在此处为每个主商品设置对应的副商品。")
        st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="card toolbar-sticky">', unsafe_allow_html=True)
    g1, g2, g3, g4 = st.columns([1, 1, 1, 1])
    go = g1.button("🚀 生成 Excel", use_container_width=True)
    show_preview = g2.checkbox("生成后显示预览", value=True, key="show_preview_cb")
    
    with g3:
        save_button_pressed = False
        if mode == 'adhoc':
            if st.button("💾 保存为模板", use_container_width=True):
                st.session_state['__pending_tpl_payload'] = adhoc_combos
                st.session_state['__show_save_tpl_modal'] = True
                save_button_pressed = True
        elif mode == 'template' and selected_templates:
            if st.button("💾 保存为模板", use_container_width=True):
                tweaked_combos = []
                for tname in selected_templates:
                    tpl = next((t for t in templates if t['name'] == tname), None)
                    if not tpl: continue
                    for ci, combo in enumerate(tpl.get('combos', [])):
                        prefix = st.session_state.get(f"tmp_edit_{tname}_{ci}_prefix", combo.get('prefix', ''))
                        items = st.session_state.get(f"tmp_edit_{tname}_{ci}_items", combo.get("items", []))
                        tweaked_combos.append({"prefix": prefix, "items": items})
                st.session_state['__pending_tpl_payload'] = tweaked_combos
                st.session_state['__show_save_tpl_modal'] = True
                save_button_pressed = True
        elif mode == 'per_main':
            if st.button("💾 保存为模板", use_container_width=True):
                combos_to_save = []
                for i in range(len(_lines(st.session_state["txt_main_codes"]))):
                    prefix = st.session_state.get(f"permain_{i}_prefix", "")
                    items = st.session_state.get(f"permain_{i}_items", [])
                    if items:
                        combos_to_save.append({"prefix": prefix, "items": items})
                if not combos_to_save:
                    st.warning("当前没有可保存的副商品组合（全部为空）。")
                else:
                    st.session_state['__pending_tpl_payload'] = combos_to_save
                    st.session_state['__show_save_tpl_modal'] = True
                    save_button_pressed = True

    if mode == 'adhoc':
        g4.markdown("当前使用 <span class='chip'>无模板模式</span>", unsafe_allow_html=True)
    elif mode == 'template':
        g4.markdown(f"当前使用 <span class='chip'>{len(selected_templates)} 个模板</span>", unsafe_allow_html=True)
    else:
        g4.markdown("当前使用 <span class='chip'>空模板（按主商品自定义）</span>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    if go:
        errs = []
        if not codes: errs.append("主商品编码为空")
        if not specs: errs.append("主商品规格为空")
        if len(codes) != len(specs): errs.append("主商品编码与规格数量不一致")
        # 当未启用“允许不添加副商品”时，仍要求提供副商品（仅无模板模式）
        if mode == "adhoc" and not any(c.get("items") for c in adhoc_combos) and not st.session_state.get('allow_no_subitems', False):
            errs.append("无模板模式下未提供任何副商品行")
        if mode == "template" and not selected_templates:
            errs.append("未选择任何模板")
        
        # 规则：
        # - 无模板 + 允许不添加副商品：所有主商品数量必须≥2
        # - 空模板（按主商品自定义）：对于副商品为空的主商品，数量必须≥2
        if mode == "adhoc" and st.session_state.get('allow_no_subitems', False):
            qtys = [st.session_state.get(f"main_qty_{i}", 1) for i in range(len(codes))]
            if any(q < 2 for q in qtys):
                errs.append("已启用『不添加副商品』，主商品数量必须≥2")
        if mode == "per_main":
            for i, c in enumerate(codes):
                items = st.session_state.get(f"permain_{i}_items", [])
                qty = st.session_state.get(f"main_qty_{i}", 1)
                if not items and qty < 2:
                    errs.append(f"主商品 {c} 未设置副商品，数量需≥2")

        if errs:
            for e in errs: st.error("❌ " + e)
        else:
            rules = [(r.get('find', ''), r.get('replace', '')) for r in st.session_state.get('simplify_rules', []) if r.get('find')] if 'enable_simplify' in locals() and enable_simplify else []
            
            combos = []
            if mode == "adhoc":
                for i in range(int(st.session_state.get("adhoc_count", 1))):
                    prefix = st.session_state.get(f"adhoc_prefix_{i}", "")
                    items = [] if st.session_state.get('allow_no_subitems', False) else st.session_state.get(f"adhoc_{i}_items", [])
                    combos.append((prefix, items))
            elif mode == "template":
                for tname in selected_templates:
                    tpl = next((t for t in templates if t['name'] == tname), None)
                    if not tpl: continue
                    for ci, combo in enumerate(tpl.get('combos', [])):
                        prefix = st.session_state.get(f"tmp_edit_{tname}_{ci}_prefix", combo.get('prefix', ''))
                        items = st.session_state.get(f"tmp_edit_{tname}_{ci}_items", combo.get("items", []))
                        combos.append((prefix, items))
            else:
                # per_main
                per_main_pairs = []
                for i in range(len(codes)):
                    prefix = st.session_state.get(f"permain_{i}_prefix", "")
                    items = st.session_state.get(f"permain_{i}_items", [])
                    per_main_pairs.append((prefix, items))

            main_products_data = [{"主商品编码": c, "主商品组合颜色规格": s, "数量": st.session_state.get(f"main_qty_{i}", 1), "应占售价": st.session_state.get(f"main_price1_{i}", 1.0), "基本售价": st.session_state.get(f"main_price2_{i}", 1.0), "成本价": st.session_state.get(f"main_cost_{i}", 1.0)} for i, (c, s) in enumerate(zip(codes, specs))]
            main_products_df = pd.DataFrame(main_products_data)

            if mode == "per_main":
                rows = build_rows_pairwise(main_products_df, per_main_pairs, simplify_rules=rules, use_regex=use_regex, case_sensitive=case_sensitive, apply_to_name=apply_to_name)
            else:
                rows = build_rows(main_products_df, combos, simplify_rules=rules, use_regex=use_regex, case_sensitive=case_sensitive, apply_to_name=apply_to_name)
            df = pd.DataFrame(rows, columns=TEMPLATE_COLUMNS)
            st.session_state['generated_df'] = df
            st.success(f"✅ 生成成功，共 {len(df)} 行")

    if st.session_state['generated_df'] is not None:
        df = st.session_state['generated_df']
        out = BytesIO(); df.to_excel(out, index=False); out.seek(0)
        st.download_button("📥 下载组合装导入模板", data=out, file_name="组合装导入模板.xlsx", use_container_width=True)
        if show_preview:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.write("🔎 预览前 60 行：")
            st.dataframe(df.head(60), use_container_width=True, height=420)
            st.markdown('</div>', unsafe_allow_html=True)

    if st.session_state.get('__show_save_tpl_modal', False):
        st.warning("另存为新模板")
        new_name = st.text_input("新模板名称", value="新模板", key="save_as_new_name_input")
        
        s1, s2 = st.columns(2)
        if s1.button("确认保存", key="confirm_save_as_btn"):
            if not new_name.strip():
                st.error("新模板名称不能为空")
            elif any(t['name'] == new_name.strip() for t in templates):
                st.error("该模板名称已存在")
            else:
                payload = st.session_state.get('__pending_tpl_payload', [])
                if payload:
                    payload = payload[:COMBO_LIMIT_PER_TEMPLATE]
                    new_tpl = {"name": new_name.strip(), "combos": payload}
                    templates.append(new_tpl)
                    save_templates(templates)
                    st.cache_resource.clear()
                    st.session_state['__show_save_tpl_modal'] = False
                    st.session_state['__pending_tpl_payload'] = None
                    st.success(f"已保存新模板: {new_name.strip()}")
                    st.rerun()
        
        if s2.button("取消", key="cancel_save_as_btn"):
            st.session_state['__show_save_tpl_modal'] = False
            st.session_state['__pending_tpl_payload'] = None
            st.rerun()

elif page == "🧱 模板管理":
    view = st.session_state.get('tpl_manage_view', 'list')
    edit_index = st.session_state.get('tpl_edit_index', None)

    if view == 'edit' and edit_index is not None and edit_index < len(templates):
        tpl = templates[edit_index]
        st.markdown(f"### 正在编辑：{tpl['name']}")
        
        if st.button("⬅️ 返回模板列表"):
            st.session_state['tpl_manage_view'] = 'list'
            st.session_state['tpl_edit_index'] = None
            st.rerun()

        new_name = st.text_input("模板名称", value=tpl['name'], key=f"tpl_edit_name_{edit_index}")
        exp_all = st.checkbox("展开所有组合", value=False, key=f"tpl_expand_all_{edit_index}")

        if st.button("➕ 添加新组合"):
            if len(tpl.get('combos', [])) >= COMBO_LIMIT_PER_TEMPLATE:
                st.warning(f"该模板的组合已达上限（{COMBO_LIMIT_PER_TEMPLATE}）")
            else:
                tpl.get('combos', []).append({"prefix": "", "items": []})
                st.rerun()

        for ci, combo in enumerate(tpl.get('combos', [])):
            prefix = combo.get('prefix', '')
            label = prefix if prefix else f"组合 {ci+1}"
            with st.expander(label, expanded=exp_all):
                c1, c2 = st.columns([4, 1])
                with c1:
                    prefix = st.text_input("前缀", value=combo.get('prefix', ''), key=f"tpl_edit_{edit_index}_{ci}_prefix")
                with c2:
                    st.write("") # Align button
                    if st.button("删除此组合", key=f"delete_combo_{edit_index}_{ci}"):
                        st.session_state[f'confirm_delete_combo_{edit_index}'] = ci
                        st.rerun()
                
                render_sub_items_editor(
                    session_key_prefix=f"tpl_edit_{edit_index}_{ci}",
                    initial_items=combo.get("items", [])
                )

        # --- Combo Deletion Confirmation ---
        confirm_combo_del_key = f'confirm_delete_combo_{edit_index}'
        if st.session_state.get(confirm_combo_del_key) is not None:
            combo_idx = st.session_state[confirm_combo_del_key]
            st.warning(f"确定要删除 **组合 {combo_idx + 1}** 吗？此操作不可撤销。")
            c1, c2 = st.columns(2)
            if c1.button("确认删除组合", key=f"confirm_del_combo_{edit_index}"):
                tpl.get('combos', []).pop(combo_idx)
                del st.session_state[confirm_combo_del_key]
                st.rerun()
            if c2.button("取消删除组合", key=f"cancel_del_combo_{edit_index}"):
                del st.session_state[confirm_combo_del_key]
                st.rerun()

        if st.button("💾 保存更改", type="primary"):
            new_name_trim = new_name.strip()
            if not new_name_trim:
                st.error("模板名称不能为空")
            elif any(idx != edit_index and t['name'] == new_name_trim for idx, t in enumerate(templates)):
                st.error("模板名称已存在，请更换")
            else:
                updated_combos = []
                for ci, combo in enumerate(tpl.get('combos', [])):
                    prefix = st.session_state[f"tpl_edit_{edit_index}_{ci}_prefix"]
                    items = st.session_state[f"tpl_edit_{edit_index}_{ci}_items"]
                    updated_combos.append({"prefix": prefix, "items": items})
                
                updated_combos = updated_combos[:COMBO_LIMIT_PER_TEMPLATE]
                templates[edit_index]['name'] = new_name_trim
                templates[edit_index]['combos'] = updated_combos
                save_templates(templates)
                st.cache_resource.clear()
                st.success(f"模板 '{new_name_trim}' 已保存！")

    else: # List view
        st.session_state['tpl_manage_view'] = 'list'
        # ... (The list view code remains the same as the last correct version)
        st.markdown('<div class="card">', unsafe_allow_html=True)
        h1, h2, h3 = st.columns([1,1,2])
        with h1:
            st.markdown("### 📚 模板库")
            st.write(f"模板数量：**{len(templates)}/{TEMPLATE_LIMIT}**")
        with h2:
            if st.button("➕ 新建模板", use_container_width=True):
                st.session_state['show_new_tpl_modal'] = True
        with h3:
            buf = BytesIO()
            buf.write(json.dumps({"templates": templates}, ensure_ascii=False, indent=2).encode("utf-8"))
            buf.seek(0)
            st.download_button("📤 导出全部模板 JSON", data=buf, file_name="templates.json", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)

        st.markdown('<div class="card">', unsafe_allow_html=True)
        if 'tpl_page' not in st.session_state:
            st.session_state.tpl_page = 0
        
        search_query = st.text_input("🔎 搜索模板名（回车过滤）", key="tpl_search", placeholder="输入关键词过滤模板…")
        prev_q = st.session_state.get('_tpl_search_prev', None)
        if prev_q != search_query:
            st.session_state['_tpl_search_prev'] = search_query
            st.session_state.tpl_page = 0
        filtered = [t for t in templates if search_query.strip().lower() in t['name'].lower()]
        st.caption(f"匹配到 {len(filtered)} 个模板")
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        # --- Batch Actions ---
        if 'selected_templates_for_batch' not in st.session_state:
            st.session_state['selected_templates_for_batch'] = []
        # 去重，保持稳定
        st.session_state['selected_templates_for_batch'] = list(dict.fromkeys(st.session_state['selected_templates_for_batch']))
        selected_names = st.session_state.get('selected_templates_for_batch', [])
        has_selection = len(selected_names) > 0

        b_cols = st.columns([1, 1, 1, 1.2, 1, 2])
        with b_cols[0]:
            if st.button("全选", key="batch_select_all", use_container_width=True):
                st.session_state['selected_templates_for_batch'] = [t['name'] for t in filtered]
                for t in filtered:
                    st.session_state[f"cb_{t['name']}"] = True
                st.rerun()
        with b_cols[1]:
            if st.button("取消", key="batch_deselect_all", use_container_width=True):
                st.session_state['selected_templates_for_batch'] = []
                for t in filtered:
                    st.session_state[f"cb_{t['name']}"] = False
                st.rerun()
        with b_cols[2]:
            if st.button("复制", key="batch_copy", disabled=not has_selection, use_container_width=True):
                st.session_state['confirm_batch_copy'] = True
                st.session_state['confirm_batch_delete'] = False
                st.session_state['__dup_modal_idx'] = None
                st.session_state['__del_modal_idx'] = None
                st.rerun()
        with b_cols[3]:
            selected_for_export = [t for t in templates if t['name'] in selected_names]
            export_buf = BytesIO()
            export_buf.write(json.dumps({"templates": selected_for_export}, ensure_ascii=False, indent=2).encode("utf-8"))
            export_buf.seek(0)
            st.download_button(
                label=f"导出 ({len(selected_names)})",
                data=export_buf,
                file_name="selected_templates.json",
                mime="application/json",
                key="batch_export_btn",
                disabled=not has_selection,
                use_container_width=True
            )
        with b_cols[4]:
            if st.button("删除", key="batch_delete", type="secondary", disabled=not has_selection, use_container_width=True):
                st.session_state['confirm_batch_delete'] = True
                st.session_state['confirm_batch_copy'] = False
                st.session_state['__dup_modal_idx'] = None
                st.session_state['__del_modal_idx'] = None
                st.rerun()
        with b_cols[5]:
            if has_selection:
                st.markdown(f"<div style='text-align:right; padding-top:8px;'>已选 **{len(selected_names)}**</div>", unsafe_allow_html=True)
            else:
                st.markdown(f"<div style='text-align:right; padding-top:8px; color:var(--muted);'>未选择</div>", unsafe_allow_html=True)

        if has_selection and st.session_state.get('confirm_batch_copy'):
            st.warning(f"确定要复制选中的 {len(selected_names)} 个模板吗？")
            cc1, cc2 = st.columns(2)
            if cc1.button("确认复制所选", key="confirm_batch_copy_btn"):
                for name in selected_names:
                    src_tpl = next((t for t in templates if t['name'] == name), None)
                    if src_tpl:
                        new_name = f"{name} 副本"
                        i = 1
                        while any(t['name'] == new_name for t in templates):
                            i += 1
                            new_name = f"{name} 副本 {i}"
                        new_tpl = copy.deepcopy(src_tpl)
                        new_tpl['name'] = new_name
                        templates.append(new_tpl)
                save_templates(templates)
                st.cache_resource.clear()
                st.success(f"成功复制 {len(selected_names)} 个模板。")
                st.session_state['selected_templates_for_batch'] = []
                del st.session_state['confirm_batch_copy']
                st.rerun()
            if cc2.button("取消批量复制", key="cancel_batch_copy_btn"):
                del st.session_state['confirm_batch_copy']
                st.rerun()

        if has_selection and st.session_state.get('confirm_batch_delete'):
            st.warning(f"确定要删除选中的 {len(selected_names)} 个模板吗？此操作不可撤销。")
            cd1, cd2 = st.columns(2)
            if cd1.button("确认删除所选", key="confirm_batch_delete_btn"):
                templates = [t for t in templates if t['name'] not in selected_names]
                save_templates(templates)
                st.cache_resource.clear()
                st.success(f"成功删除 {len(selected_names)} 个模板。")
                st.session_state['selected_templates_for_batch'] = []
                del st.session_state['confirm_batch_delete']
                st.rerun()
            if cd2.button("取消批量删除", key="cancel_batch_delete_btn"):
                del st.session_state['confirm_batch_delete']
                st.rerun()
        
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)

        # --- Pagination Logic ---
        ITEMS_PER_PAGE = 5
        page_num = st.session_state.tpl_page
        total_items = len(filtered)
        total_pages = (total_items - 1) // ITEMS_PER_PAGE + 1
        # 页码校正
        if total_pages > 0 and page_num >= total_pages:
            st.session_state.tpl_page = total_pages - 1
            st.rerun()
        start_idx = page_num * ITEMS_PER_PAGE
        end_idx = start_idx + ITEMS_PER_PAGE
        paginated_filtered = filtered[start_idx:end_idx]

        st.markdown('<div class="tpl-grid">', unsafe_allow_html=True)
        for ti, tpl in enumerate(paginated_filtered):
            original_index = templates.index(tpl)
            st.markdown('<div class="tpl-card">', unsafe_allow_html=True)
            c0, c1, c2, c3, c4 = st.columns([0.5, 3, 1, 1, 1])
            with c0:
                def on_checkbox_change(tpl_name):
                    is_checked = st.session_state.get(f"cb_{tpl_name}", False)
                    if is_checked:
                        if tpl_name not in st.session_state['selected_templates_for_batch']:
                            st.session_state['selected_templates_for_batch'].append(tpl_name)
                    else:
                        if tpl_name in st.session_state['selected_templates_for_batch']:
                            st.session_state['selected_templates_for_batch'].remove(tpl_name)
                
                # 复选框状态与选中集合保持一致，跨页不丢失
                checkbox_key = f"cb_{tpl['name']}"
                st.session_state[checkbox_key] = (tpl['name'] in st.session_state.get('selected_templates_for_batch', []))
                st.checkbox(
                    "",
                    key=checkbox_key,
                    on_change=on_checkbox_change,
                    args=(tpl['name'],)
                )
            with c1:
                st.markdown(f"<div class='tpl-name'>{tpl['name']} <span style='font-weight:normal;font-size:13px;color:var(--muted);'>({len(tpl.get('combos',[]))}组)</span></div>", unsafe_allow_html=True)
            with c2:
                if st.button("编辑", key=f"grid_edit_{ti}", use_container_width=True):
                    st.session_state['tpl_manage_view'] = 'edit'
                    st.session_state['tpl_edit_index'] = templates.index(tpl)
                    st.rerun()
            with c3:
                if st.button("复制", key=f"grid_dup_{ti}", use_container_width=True):
                    st.session_state['__dup_modal_idx'] = templates.index(tpl)
                    st.session_state['__del_modal_idx'] = None
                    st.session_state['confirm_batch_copy'] = False
                    st.session_state['confirm_batch_delete'] = False
                    st.rerun()
            with c4:
                if st.button("删除", key=f"grid_del_{ti}", use_container_width=True):
                    st.session_state['__del_modal_idx'] = templates.index(tpl)
                    st.session_state['__dup_modal_idx'] = None
                    st.session_state['confirm_batch_copy'] = False
                    st.session_state['confirm_batch_delete'] = False
                    st.rerun()
            st.markdown('</div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)
        
        # --- Pagination Controls ---
        st.markdown('<div class="divider"></div>', unsafe_allow_html=True)
        p_cols = st.columns([1, 1, 1])
        with p_cols[0]:
            if st.button("⬅️ 上一页", disabled=(page_num <= 0)):
                st.session_state.tpl_page -= 1
                st.rerun()
        with p_cols[1]:
            st.markdown(f"<div style='text-align:center; padding-top:8px;'>第 {page_num + 1} / {total_pages} 页</div>", unsafe_allow_html=True)
        with p_cols[2]:
            if st.button("下一页 ➡️", disabled=(page_num >= total_pages - 1)):
                st.session_state.tpl_page += 1
                st.rerun()

        st.markdown('</div>', unsafe_allow_html=True)

        if st.session_state.get('__del_modal_idx') is not None:
            del_idx = st.session_state['__del_modal_idx']
            del_name = templates[del_idx]['name']
            st.warning(f"确定要删除模板 **{del_name}** 吗？")
            c1, c2 = st.columns(2)
            if c1.button("确认删除", type="primary"):
                del templates[del_idx]
                save_templates(templates)
                st.cache_resource.clear()
                st.session_state['__del_modal_idx'] = None
                st.success(f"已删除模板: {del_name}")
                st.rerun()
            if c2.button("取消"):
                st.session_state['__del_modal_idx'] = None
                st.rerun()

        if st.session_state.get('__dup_modal_idx') is not None:
            src_idx = st.session_state['__dup_modal_idx']
            src_name = templates[src_idx]['name']
            st.warning(f"确定要复制模板 **{src_name}** 吗？")
            
            new_name = st.text_input("新模板名称", value=f"{src_name} 副本", key="dup_new_name_input")
            
            dup_c1, dup_c2 = st.columns(2)
            if dup_c1.button("确认复制", key="confirm_dup_btn"):
                if not new_name.strip():
                    st.error("新模板名称不能为空")
                elif any(t['name'] == new_name.strip() for t in templates):
                    st.error("该模板名称已存在")
                else:
                    new_tpl = copy.deepcopy(templates[src_idx])
                    new_tpl['name'] = new_name.strip()
                    templates.insert(src_idx + 1, new_tpl)
                    save_templates(templates)
                    st.cache_resource.clear()
                    st.session_state['__dup_modal_idx'] = None
                    st.success(f"已复制模板为: {new_name}")
                    st.rerun()
            
            if dup_c2.button("取消", key="cancel_dup_btn"):
                st.session_state['__dup_modal_idx'] = None
                st.rerun()
        
        # Import
        st.markdown('<div class="card card-muted">', unsafe_allow_html=True)
        if "file_uploader_key" not in st.session_state:
            st.session_state["file_uploader_key"] = "uploader_1"
        uploaded = st.file_uploader("📥 导入模板 JSON（按名称合并；超过上限将被截断）", type=["json"], key=st.session_state["file_uploader_key"])
        if uploaded is not None:
            try:
                data = json.loads(uploaded.read().decode("utf-8"))
                imported = data["templates"] if isinstance(data, dict) and "templates" in data else (data if isinstance(data, list) else [])
                merged = {t['name']: t for t in templates}
                for t in imported:
                    if not isinstance(t, dict) or 'name' not in t: continue
                    t_name = t['name']
                    if t_name in merged:
                        existing_combos = merged[t_name].get('combos', [])
                        new_combos = t.get('combos', [])
                        if not new_combos and 'items' in t:
                            new_combos = [{'prefix': t.get('prefix', ''), 'items': t['items']}]
                        merged[t_name]['combos'] = existing_combos + new_combos
                    else:
                        if 'combos' not in t and 'items' in t:
                            t['combos'] = [{'prefix': t.get('prefix', ''), 'items': t['items']}]
                        merged[t_name] = t
                new_list = list(merged.values())[:TEMPLATE_LIMIT]
                # 限制每个模板的组合数量
                for t in new_list:
                    if isinstance(t, dict):
                        t['combos'] = t.get('combos', [])[:COMBO_LIMIT_PER_TEMPLATE]
                save_templates(new_list)
                st.cache_resource.clear()
                st.session_state["file_uploader_key"] = f"uploader_{hash(str(time.time()))}"
                st.success("模板已导入并合并")
                st.rerun()
            except Exception as e:
                st.error(f"导入失败：{e}")
        st.markdown('</div>', unsafe_allow_html=True)

elif page == "📊 图表生成":

    st.markdown("<div class='card-ghost'><div class='section-title'>📈 Excel 图表生成器（增强版）</div></div>", unsafe_allow_html=True)

    if 'uploader_key' not in st.session_state:
        st.session_state.uploader_key = 0

    @st.cache_data
    def load_excel(uploaded_file):
        df = pd.read_excel(uploaded_file, header=0)  # 第一行作为标题
        df = df.fillna('')
        return df

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.info("💡 Excel格式要求：第一行为列标题，之后各行为数据")
    uploaded_files = st.file_uploader(
        "上传一个或多个 Excel 文件",
        type=["xlsx", "xls"],
        accept_multiple_files=True,
        key=f"chart_uploader_{st.session_state.uploader_key}"
    )

    if uploaded_files:
        ordered_keys = [f"{f.name}_{f.size}" for f in uploaded_files]
        # Only clear the figure if the files have actually changed.
        if st.session_state.get('chart_df_keys') is not None and ordered_keys != st.session_state.get('chart_df_keys', []):
            st.session_state['last_fig'] = None
            st.session_state['chart_dfs'] = {} # Also clear cached dataframes

        if 'chart_dfs' not in st.session_state:
            st.session_state['chart_dfs'] = {}
        
        for i, uploaded_file in enumerate(uploaded_files):
            file_key = ordered_keys[i]
            if file_key not in st.session_state['chart_dfs']:
                df = load_excel(uploaded_file)
                st.session_state['chart_dfs'][file_key] = {
                    "name": uploaded_file.name,
                    "df": df,
                    "cols": df.columns.tolist()
                }
        
        current_keys_set = set(ordered_keys)
        st.session_state['chart_dfs'] = {k: v for k, v in st.session_state['chart_dfs'].items() if k in current_keys_set}
        st.session_state['chart_df_keys'] = ordered_keys
        
        st.success(f"✅ 成功上传并处理了 {len(uploaded_files)} 个文件！")

    if st.button("🗑️ 清空所有文件和图表", use_container_width=True):
        st.session_state.uploader_key += 1
        if 'chart_dfs' in st.session_state:
            del st.session_state['chart_dfs']
        if 'chart_df_keys' in st.session_state:
            del st.session_state['chart_df_keys']
        if 'last_fig' in st.session_state:
            st.session_state['last_fig'] = None
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown("<div class='card-ghost'><div class='section-title'>🎨 图表配置</div></div>", unsafe_allow_html=True)
    st.markdown('<div class="card">', unsafe_allow_html=True)

    # Track previous analysis mode to clear chart on change
    if 'prev_analysis_mode' not in st.session_state:
        st.session_state['prev_analysis_mode'] = st.session_state.analysis_mode

    b1, b2 = st.columns(2)
    if b1.button("单个文件图表", use_container_width=True):
        st.session_state.analysis_mode = "单个文件图表"
    if b2.button("多文件对比图表", use_container_width=True):
        st.session_state.analysis_mode = "多文件对比图表"

    # If mode has changed, clear the figure and update the tracker
    if st.session_state.analysis_mode != st.session_state.prev_analysis_mode:
        st.session_state.last_fig = None
        st.session_state.prev_analysis_mode = st.session_state.analysis_mode
        st.rerun()
    
    st.caption(f"当前模式: **{st.session_state.analysis_mode}**")
    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)

    if not st.session_state.get('chart_dfs'):
        st.info("请先上传一个或多个 Excel 文件以配置图表。")
    else:
        if st.session_state.analysis_mode == "单个文件图表":
            file_keys = list(st.session_state['chart_dfs'].keys())
            file_names = [st.session_state['chart_dfs'][k]['name'] for k in file_keys]
            selected_file_name = st.selectbox("选择要分析的文件", file_names)
            
            if selected_file_name:
                selected_key = file_keys[file_names.index(selected_file_name)]
                data = st.session_state['chart_dfs'][selected_key]
                df, cols = data['df'], data['cols']

                with st.expander("📋 预览数据", expanded=False):
                    st.dataframe(df.head(20), use_container_width=True)
                    st.caption(f"数据行数：{len(df)} | 列数：{len(cols)}")

                chart_type = st.selectbox("选择图表类型", [
                    "条形图", "折线图", "散点图", "饼图", "面积图", "箱线图", 
                    "热力图", "瀑布图", "漏斗图", "双Y轴图", "3D散点图", "3D曲面图", "数据透视表"
                ], key=f"single_chart_type_{selected_key}")
                
                st.markdown("##### ⚙️ 图表选项")
                c1, c2, c3, c4, c5 = st.columns(5)
                with c1:
                    color = st.color_picker("图表主色", "#10a37f", key=f"single_color_{selected_key}")
                with c2:
                    st.number_input("X轴角度", -90, 90, 45, 5, key="xaxis_angle_single")
                with c3:
                    st.number_input("间隔阈值", 3, 5000, 25, 5, key="interval_threshold_single")
                with c4:
                    st.number_input("间隔步长", 1, 10, 2, 1, key="interval_step_single")
                with c5:
                    use_chinese_format = st.checkbox("Y轴万单位", value=True, key=f"chinese_fmt_{selected_key}")

                st.markdown("---")

                if chart_type == "条形图":
                    x_axis = st.selectbox("选择 X 轴", cols, key=f"bar_x_{selected_key}")
                    y_axis = st.selectbox("选择 Y 轴", cols, index=1 if len(cols) > 1 else 0, key=f"bar_y_{selected_key}")
                    orientation = st.radio("方向", ["垂直", "水平"], horizontal=True, key=f"bar_orient_{selected_key}")
                    if st.button("📊 生成图表", key=f"gen_bar_{selected_key}", use_container_width=True):
                        y_data = df[y_axis].astype(str).str.replace(',', '', regex=False)
                        df[y_axis] = pd.to_numeric(y_data, errors='coerce')
                        if orientation == "水平":
                            fig = px.bar(df, y=x_axis, x=y_axis, title=f"{y_axis} vs {x_axis}", color_discrete_sequence=[color], orientation='h')
                        else:
                            fig = px.bar(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}", color_discrete_sequence=[color])
                        
                        # 应用中文格式
                        if use_chinese_format:
                            y_vals = df[y_axis].dropna()
                            tickvals = []
                            ticktext = []
                            y_min, y_max = 0, y_vals.max()
                            step = (y_max - y_min) / 8
                            for i in range(9):
                                val = y_min + i * step
                                tickvals.append(val)
                                ticktext.append(format_number_chinese(val))
                            if orientation == "水平":
                                fig.update_xaxes(tickvals=tickvals, ticktext=ticktext)
                            else:
                                fig.update_yaxes(tickvals=tickvals, ticktext=ticktext)
                        
                        fig.update_traces(hovertemplate=f"<b>{x_axis}:</b> %{{x}}<br><b>{y_axis}:</b> %{{y}}<extra></extra>")
                        fig.update_layout(margin=dict(l=80, r=120, t=80, b=120), height=600)
                        angle = st.session_state.get("xaxis_angle_single", 45)
                        threshold = st.session_state.get("interval_threshold_single", 25)
                        step = st.session_state.get("interval_step_single", 2)
                        if orientation == "垂直":
                            fig = update_xaxis_ticks(fig, df[x_axis], angle, threshold, step)
                        st.session_state['last_fig'] = fig
                        
                elif chart_type == "折线图":
                    x_axis = st.selectbox("选择 X 轴", cols, key=f"line_x_{selected_key}")
                    y_axis = st.selectbox("选择 Y 轴", cols, index=1 if len(cols) > 1 else 0, key=f"line_y_{selected_key}")
                    line_shape = st.selectbox("线条形状", ["linear", "spline"], key=f"line_shape_{selected_key}")
                    if st.button("📈 生成图表", key=f"gen_line_{selected_key}", use_container_width=True):
                        y_data = df[y_axis].astype(str).str.replace(',', '', regex=False)
                        df[y_axis] = pd.to_numeric(y_data, errors='coerce')
                        fig = px.line(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}", color_discrete_sequence=[color], line_shape=line_shape)
                        
                        if use_chinese_format:
                            y_vals = df[y_axis].dropna()
                            tickvals = []
                            ticktext = []
                            y_min, y_max = 0, y_vals.max()
                            step = (y_max - y_min) / 8
                            for i in range(9):
                                val = y_min + i * step
                                tickvals.append(val)
                                ticktext.append(format_number_chinese(val))
                            fig.update_yaxes(tickvals=tickvals, ticktext=ticktext)
                        
                        fig.update_traces(hovertemplate=f"<b>{x_axis}:</b> %{{x}}<br><b>{y_axis}:</b> %{{y}}<extra></extra>")
                        fig.update_layout(margin=dict(l=80, r=120, t=80, b=120), height=600)
                        angle = st.session_state.get("xaxis_angle_single", 45)
                        threshold = st.session_state.get("interval_threshold_single", 25)
                        step = st.session_state.get("interval_step_single", 2)
                        fig = update_xaxis_ticks(fig, df[x_axis], angle, threshold, step)
                        st.session_state['last_fig'] = fig
                        
                elif chart_type == "散点图":
                    x_axis = st.selectbox("选择 X 轴", cols, key=f"scatter_x_{selected_key}")
                    y_axis = st.selectbox("选择 Y 轴", cols, index=1 if len(cols) > 1 else 0, key=f"scatter_y_{selected_key}")
                    size_col = st.selectbox("气泡大小列（可选）", ["无"] + cols, key=f"scatter_size_{selected_key}")
                    if st.button("🔵 生成图表", key=f"gen_scatter_{selected_key}", use_container_width=True):
                        y_data = df[y_axis].astype(str).str.replace(',', '', regex=False)
                        df[y_axis] = pd.to_numeric(y_data, errors='coerce')
                        size_param = None if size_col == "无" else size_col
                        fig = px.scatter(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}", color_discrete_sequence=[color], size=size_param)
                        
                        if use_chinese_format:
                            y_vals = df[y_axis].dropna()
                            tickvals = []
                            ticktext = []
                            y_min, y_max = y_vals.min(), y_vals.max()
                            step = (y_max - y_min) / 8
                            for i in range(9):
                                val = y_min + i * step
                                tickvals.append(val)
                                ticktext.append(format_number_chinese(val))
                            fig.update_yaxes(tickvals=tickvals, ticktext=ticktext)
                        
                        fig.update_traces(hovertemplate=f"<b>{x_axis}:</b> %{{x}}<br><b>{y_axis}:</b> %{{y}}<extra></extra>")
                        fig.update_layout(margin=dict(l=80, r=120, t=80, b=120), height=600)
                        angle = st.session_state.get("xaxis_angle_single", 45)
                        threshold = st.session_state.get("interval_threshold_single", 25)
                        step = st.session_state.get("interval_step_single", 2)
                        fig = update_xaxis_ticks(fig, df[x_axis], angle, threshold, step)
                        st.session_state['last_fig'] = fig
                        
                elif chart_type == "饼图":
                    names = st.selectbox("选择标签列", cols, key=f"pie_names_{selected_key}")
                    values = st.selectbox("选择数值列", cols, index=1 if len(cols) > 1 else 0, key=f"pie_values_{selected_key}")
                    hole = st.slider("中心空洞大小（环形图）", 0.0, 0.8, 0.0, 0.1, key=f"pie_hole_{selected_key}")
                    if st.button("🥧 生成图表", key=f"gen_pie_{selected_key}", use_container_width=True):
                        val_data = df[values].astype(str).str.replace(',', '', regex=False)
                        df[values] = pd.to_numeric(val_data, errors='coerce')
                        fig = px.pie(df, names=names, values=values, title=f"{names} 分布", hole=hole)
                        fig.update_layout(margin=dict(l=80, r=120, t=80, b=120), height=600)
                        st.session_state['last_fig'] = fig
                        
                elif chart_type == "面积图":
                    x_axis = st.selectbox("选择 X 轴", cols, key=f"area_x_{selected_key}")
                    y_axis = st.selectbox("选择 Y 轴", cols, index=1 if len(cols) > 1 else 0, key=f"area_y_{selected_key}")
                    if st.button("📊 生成图表", key=f"gen_area_{selected_key}", use_container_width=True):
                        y_data = df[y_axis].astype(str).str.replace(',', '', regex=False)
                        df[y_axis] = pd.to_numeric(y_data, errors='coerce')
                        fig = px.area(df, x=x_axis, y=y_axis, title=f"{y_axis} vs {x_axis}", color_discrete_sequence=[color])
                        
                        if use_chinese_format:
                            y_vals = df[y_axis].dropna()
                            tickvals = []
                            ticktext = []
                            y_min, y_max = 0, y_vals.max()
                            step = (y_max - y_min) / 8
                            for i in range(9):
                                val = y_min + i * step
                                tickvals.append(val)
                                ticktext.append(format_number_chinese(val))
                            fig.update_yaxes(tickvals=tickvals, ticktext=ticktext)
                        
                        fig.update_layout(margin=dict(l=80, r=120, t=80, b=120), height=600)
                        angle = st.session_state.get("xaxis_angle_single", 45)
                        threshold = st.session_state.get("interval_threshold_single", 25)
                        step = st.session_state.get("interval_step_single", 2)
                        fig = update_xaxis_ticks(fig, df[x_axis], angle, threshold, step)
                        st.session_state['last_fig'] = fig
                        
                elif chart_type == "箱线图":
                    x_axis = st.selectbox("选择分组列（X轴）", cols, key=f"box_x_{selected_key}")
                    y_axis = st.selectbox("选择数值列（Y轴）", cols, index=1 if len(cols) > 1 else 0, key=f"box_y_{selected_key}")
                    if st.button("📦 生成图表", key=f"gen_box_{selected_key}", use_container_width=True):
                        y_data = df[y_axis].astype(str).str.replace(',', '', regex=False)
                        df[y_axis] = pd.to_numeric(y_data, errors='coerce')
                        fig = px.box(df, x=x_axis, y=y_axis, title=f"{y_axis} 分布（按 {x_axis}）", color_discrete_sequence=[color])
                        
                        if use_chinese_format:
                            y_vals = df[y_axis].dropna()
                            tickvals = []
                            ticktext = []
                            y_min, y_max = y_vals.min(), y_vals.max()
                            step = (y_max - y_min) / 8
                            for i in range(9):
                                val = y_min + i * step
                                tickvals.append(val)
                                ticktext.append(format_number_chinese(val))
                            fig.update_yaxes(tickvals=tickvals, ticktext=ticktext)
                        
                        fig.update_layout(margin=dict(l=80, r=120, t=80, b=120), height=600)
                        angle = st.session_state.get("xaxis_angle_single", 45)
                        threshold = st.session_state.get("interval_threshold_single", 25)
                        step = st.session_state.get("interval_step_single", 2)
                        fig = update_xaxis_ticks(fig, df[x_axis], angle, threshold, step)
                        st.session_state['last_fig'] = fig
                        
                elif chart_type == "热力图":
                    st.info("热力图需要数值型数据列")
                    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                    if len(numeric_cols) < 2:
                        st.error("数据中没有足够的数值列用于生成热力图")
                    else:
                        selected_cols = st.multiselect("选择要包含的数值列", numeric_cols, default=numeric_cols[:min(10, len(numeric_cols))], key=f"heatmap_cols_{selected_key}")
                        if st.button("🔥 生成图表", key=f"gen_heatmap_{selected_key}", use_container_width=True):
                            if len(selected_cols) >= 2:
                                corr_matrix = df[selected_cols].corr()
                                fig = px.imshow(corr_matrix, text_auto=True, aspect="auto", title="相关性热力图", 
                                               color_continuous_scale="RdBu_r", zmin=-1, zmax=1)
                                fig.update_layout(margin=dict(l=80, r=120, t=80, b=120), height=600)
                                st.session_state['last_fig'] = fig
                            else:
                                st.error("请至少选择2个数值列")
                                
                elif chart_type == "瀑布图":
                    st.info("瀑布图显示累积效果")
                    x_axis = st.selectbox("选择 X 轴（类别）", cols, key=f"waterfall_x_{selected_key}")
                    y_axis = st.selectbox("选择 Y 轴（增量值）", cols, index=1 if len(cols) > 1 else 0, key=f"waterfall_y_{selected_key}")
                    if st.button("💧 生成图表", key=f"gen_waterfall_{selected_key}", use_container_width=True):
                        y_data = df[y_axis].astype(str).str.replace(',', '', regex=False)
                        df[y_axis] = pd.to_numeric(y_data, errors='coerce')
                        
                        fig = go.Figure(go.Waterfall(
                            x=df[x_axis].tolist(),
                            y=df[y_axis].tolist(),
                            textposition="outside",
                            connector={"line": {"color": "rgb(63, 63, 63)"}},
                        ))
                        
                        # 应用Y轴中文格式
                        if use_chinese_format:
                            y_vals = df[y_axis].dropna()
                            tickvals = []
                            ticktext = []
                            y_min = min(0, y_vals.min())
                            y_max = max(0, y_vals.max())
                            step = (y_max - y_min) / 8
                            for i in range(9):
                                val = y_min + i * step
                                tickvals.append(val)
                                ticktext.append(format_number_chinese(val))
                            fig.update_yaxes(tickvals=tickvals, ticktext=ticktext)
                        
                        fig.update_layout(
                            title=f"{y_axis} 瀑布图",
                            margin=dict(l=80, r=120, t=80, b=120),
                            height=600
                        )
                        
                        angle = st.session_state.get("xaxis_angle_single", 45)
                        threshold = st.session_state.get("interval_threshold_single", 25)
                        step = st.session_state.get("interval_step_single", 2)
                        fig = update_xaxis_ticks(fig, df[x_axis], angle, threshold, step)
                        st.session_state['last_fig'] = fig
                        
                elif chart_type == "漏斗图":
                    names = st.selectbox("选择阶段列", cols, key=f"funnel_names_{selected_key}")
                    values = st.selectbox("选择数值列", cols, index=1 if len(cols) > 1 else 0, key=f"funnel_values_{selected_key}")
                    if st.button("🔻 生成图表", key=f"gen_funnel_{selected_key}", use_container_width=True):
                        val_data = df[values].astype(str).str.replace(',', '', regex=False)
                        df[values] = pd.to_numeric(val_data, errors='coerce')
                        fig = px.funnel(df, x=values, y=names, title=f"{names} 漏斗分析")
                        
                        # 应用X轴中文格式（漏斗图的X轴是数值）
                        if use_chinese_format:
                            x_vals = df[values].dropna()
                            tickvals = []
                            ticktext = []
                            x_min, x_max = 0, x_vals.max()
                            step = (x_max - x_min) / 8
                            for i in range(9):
                                val = x_min + i * step
                                tickvals.append(val)
                                ticktext.append(format_number_chinese(val))
                            fig.update_xaxes(tickvals=tickvals, ticktext=ticktext)
                        
                        fig.update_layout(margin=dict(l=80, r=120, t=80, b=120), height=600)
                        st.session_state['last_fig'] = fig
                        
                elif chart_type == "双Y轴图":
                    st.info("双Y轴图：左右两个不同量纲的数据")
                    x_axis = st.selectbox("选择 X 轴", cols, key=f"dual_x_{selected_key}")
                    y1_axis = st.selectbox("选择左Y轴", cols, index=1 if len(cols) > 1 else 0, key=f"dual_y1_{selected_key}")
                    y2_axis = st.selectbox("选择右Y轴", cols, index=2 if len(cols) > 2 else 0, key=f"dual_y2_{selected_key}")
                    chart1_type = st.radio("左Y轴图表类型", ["条形图", "折线图"], horizontal=True, key=f"dual_type1_{selected_key}")
                    chart2_type = st.radio("右Y轴图表类型", ["条形图", "折线图"], horizontal=True, key=f"dual_type2_{selected_key}")
                    
                    if st.button("📊📈 生成图表", key=f"gen_dual_{selected_key}", use_container_width=True):
                        y1_data = df[y1_axis].astype(str).str.replace(',', '', regex=False)
                        df[y1_axis] = pd.to_numeric(y1_data, errors='coerce')
                        y2_data = df[y2_axis].astype(str).str.replace(',', '', regex=False)
                        df[y2_axis] = pd.to_numeric(y2_data, errors='coerce')
                        
                        fig = go.Figure()
                        
                        # 左Y轴
                        if chart1_type == "条形图":
                            fig.add_trace(go.Bar(x=df[x_axis], y=df[y1_axis], name=y1_axis, marker_color=color, yaxis='y'))
                        else:
                            fig.add_trace(go.Scatter(x=df[x_axis], y=df[y1_axis], name=y1_axis, mode='lines+markers', line=dict(color=color), yaxis='y'))
                        
                        # 右Y轴
                        color2 = "#f59e0b"
                        if chart2_type == "条形图":
                            fig.add_trace(go.Bar(x=df[x_axis], y=df[y2_axis], name=y2_axis, marker_color=color2, yaxis='y2'))
                        else:
                            fig.add_trace(go.Scatter(x=df[x_axis], y=df[y2_axis], name=y2_axis, mode='lines+markers', line=dict(color=color2), yaxis='y2'))
                        
                        # 设置双Y轴布局
                        fig.update_layout(
                            title=f"{y1_axis} 与 {y2_axis} 对比",
                            xaxis=dict(title=x_axis),
                            yaxis=dict(title=y1_axis, side='left'),
                            yaxis2=dict(title=y2_axis, overlaying='y', side='right'),
                            margin=dict(l=80, r=120, t=80, b=120),
                            height=600,
                            legend=dict(x=0.5, y=1.1, orientation='h')
                        )
                        
                        # 应用中文格式
                        if use_chinese_format:
                            y1_vals = df[y1_axis].dropna()
                            tickvals1 = []
                            ticktext1 = []
                            y1_min, y1_max = 0, y1_vals.max()
                            step1 = (y1_max - y1_min) / 8
                            for i in range(9):
                                val = y1_min + i * step1
                                tickvals1.append(val)
                                ticktext1.append(format_number_chinese(val))
                            
                            y2_vals = df[y2_axis].dropna()
                            tickvals2 = []
                            ticktext2 = []
                            y2_min, y2_max = 0, y2_vals.max()
                            step2 = (y2_max - y2_min) / 8
                            for i in range(9):
                                val = y2_min + i * step2
                                tickvals2.append(val)
                                ticktext2.append(format_number_chinese(val))
                            
                            # 使用update_layout更新两个Y轴，而不是update_yaxes
                            fig.update_layout(
                                yaxis=dict(tickvals=tickvals1, ticktext=ticktext1),
                                yaxis2=dict(tickvals=tickvals2, ticktext=ticktext2)
                            )
                        
                        # 应用X轴配置
                        angle = st.session_state.get("xaxis_angle_single", 45)
                        threshold = st.session_state.get("interval_threshold_single", 25)
                        step = st.session_state.get("interval_step_single", 2)
                        fig = update_xaxis_ticks(fig, df[x_axis], angle, threshold, step)
                        
                        st.session_state['last_fig'] = fig
                        
                elif chart_type == "3D散点图":
                    st.info("3D散点图：需要3个数值维度")
                    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
                    if len(numeric_cols) < 3:
                        st.warning("数值列不足3个，尝试转换...")
                        numeric_cols = cols
                    
                    x_axis = st.selectbox("选择 X 轴", numeric_cols, key=f"3d_x_{selected_key}")
                    y_axis = st.selectbox("选择 Y 轴", numeric_cols, index=1 if len(numeric_cols) > 1 else 0, key=f"3d_y_{selected_key}")
                    z_axis = st.selectbox("选择 Z 轴", numeric_cols, index=2 if len(numeric_cols) > 2 else 0, key=f"3d_z_{selected_key}")
                    
                    if st.button("🌐 生成图表", key=f"gen_3d_{selected_key}", use_container_width=True):
                        # 确保数据为数值类型
                        for col in [x_axis, y_axis, z_axis]:
                            data_col = df[col].astype(str).str.replace(',', '', regex=False)
                            df[col] = pd.to_numeric(data_col, errors='coerce')
                        
                        fig = px.scatter_3d(df, x=x_axis, y=y_axis, z=z_axis, 
                                           title=f"3D散点图: {x_axis}, {y_axis}, {z_axis}",
                                           color_discrete_sequence=[color])
                        fig.update_layout(margin=dict(l=0, r=0, t=50, b=0), height=700)
                        st.session_state['last_fig'] = fig
                        
                elif chart_type == "3D曲面图":
                    st.info("3D曲面图：用于展示三维数据的表面")
                    numeric_cols = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
                    if len(numeric_cols) < 3:
                        st.warning("数值列不足3个")
                        numeric_cols = cols
                    
                    x_axis = st.selectbox("选择 X 轴", numeric_cols, key=f"surf_x_{selected_key}")
                    y_axis = st.selectbox("选择 Y 轴", numeric_cols, index=1 if len(numeric_cols) > 1 else 0, key=f"surf_y_{selected_key}")
                    z_axis = st.selectbox("选择 Z 轴（高度）", numeric_cols, index=2 if len(numeric_cols) > 2 else 0, key=f"surf_z_{selected_key}")
                    
                    if st.button("🏔️ 生成图表", key=f"gen_surf_{selected_key}", use_container_width=True):
                        # 确保数据为数值类型
                        for col in [x_axis, y_axis, z_axis]:
                            data_col = df[col].astype(str).str.replace(',', '', regex=False)
                            df[col] = pd.to_numeric(data_col, errors='coerce')
                        
                        # 创建网格数据
                        try:
                            df_sorted = df.sort_values([x_axis, y_axis])
                            x_unique = df_sorted[x_axis].unique()
                            y_unique = df_sorted[y_axis].unique()
                            
                            # 创建Z值矩阵
                            z_matrix = []
                            for y_val in y_unique:
                                row = []
                                for x_val in x_unique:
                                    z_val = df_sorted[(df_sorted[x_axis] == x_val) & (df_sorted[y_axis] == y_val)][z_axis]
                                    row.append(z_val.iloc[0] if len(z_val) > 0 else 0)
                                z_matrix.append(row)
                            
                            fig = go.Figure(data=[go.Surface(z=z_matrix, x=x_unique, y=y_unique, colorscale='Viridis')])
                            fig.update_layout(
                                title=f"3D曲面图: {z_axis} = f({x_axis}, {y_axis})",
                                scene=dict(
                                    xaxis_title=x_axis,
                                    yaxis_title=y_axis,
                                    zaxis_title=z_axis
                                ),
                                margin=dict(l=0, r=0, t=50, b=0),
                                height=700
                            )
                            st.session_state['last_fig'] = fig
                        except Exception as e:
                            st.error(f"生成3D曲面图失败：{str(e)}\n提示：数据需要形成规则网格")
                            st.info("建议：确保X和Y轴的组合能形成规则的网格数据")
                            
                elif chart_type == "数据透视表":
                    st.info("📊 数据透视表：交叉汇总分析工具")
                    
                    st.markdown("##### 📋 透视表配置")
                    
                    # 选择行、列、值
                    row_col = st.selectbox("行（分组依据）", cols, key=f"pivot_row_{selected_key}")
                    col_col = st.selectbox("列（横向分类）", ["无"] + cols, key=f"pivot_col_{selected_key}")
                    
                    # 数值列可以多选
                    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
                    if not numeric_cols:
                        st.warning("没有找到数值列，将尝试转换所有列")
                        numeric_cols = [c for c in cols if c != row_col]
                    
                    value_cols = st.multiselect(
                        "值（要汇总的数值）", 
                        numeric_cols, 
                        default=[numeric_cols[0]] if numeric_cols else [],
                        key=f"pivot_values_{selected_key}"
                    )
                    
                    # 聚合函数选择
                    agg_func = st.selectbox(
                        "聚合方式",
                        ["求和(sum)", "平均值(mean)", "计数(count)", "最大值(max)", "最小值(min)", "中位数(median)"],
                        key=f"pivot_agg_{selected_key}"
                    )
                    
                    # 映射聚合函数
                    agg_map = {
                        "求和(sum)": "sum",
                        "平均值(mean)": "mean",
                        "计数(count)": "count",
                        "最大值(max)": "max",
                        "最小值(min)": "min",
                        "中位数(median)": "median"
                    }
                    agg_func_name = agg_map[agg_func]
                    
                    # 格式选项
                    show_totals = st.checkbox("显示汇总行/列", value=True, key=f"pivot_totals_{selected_key}")
                    format_numbers = st.checkbox("格式化数值（千分位）", value=True, key=f"pivot_format_{selected_key}")
                    
                    if st.button("📊 生成透视表", key=f"gen_pivot_{selected_key}", use_container_width=True):
                        if not value_cols:
                            st.error("请至少选择一个数值列")
                        else:
                            try:
                                # 确保数值列为数值类型
                                for col in value_cols:
                                    if col in df.columns:
                                        df[col] = pd.to_numeric(df[col].astype(str).str.replace(',', ''), errors='coerce')
                                
                                # 创建透视表
                                if col_col == "无":
                                    # 单维度透视
                                    pivot_df = df.groupby(row_col)[value_cols].agg(agg_func_name).reset_index()
                                    
                                    # 添加汇总行
                                    if show_totals:
                                        total_row = {row_col: '总计'}
                                        for val_col in value_cols:
                                            if agg_func_name in ['sum', 'mean', 'count']:
                                                total_row[val_col] = df[val_col].agg(agg_func_name)
                                            else:
                                                total_row[val_col] = '-'
                                        pivot_df = pd.concat([pivot_df, pd.DataFrame([total_row])], ignore_index=True)
                                else:
                                    # 双维度透视
                                    pivot_df = pd.pivot_table(
                                        df,
                                        values=value_cols,
                                        index=row_col,
                                        columns=col_col,
                                        aggfunc=agg_func_name,
                                        fill_value=0,
                                        margins=show_totals,
                                        margins_name='总计'
                                    )
                                    
                                    # 展平多层列索引
                                    if isinstance(pivot_df.columns, pd.MultiIndex):
                                        pivot_df.columns = [f"{col[0]}_{col[1]}" if col[1] else col[0] for col in pivot_df.columns]
                                    
                                    pivot_df = pivot_df.reset_index()
                                
                                # 格式化显示
                                st.markdown("---")
                                st.markdown("##### 📊 透视表结果")
                                st.caption(f"行数：{len(pivot_df)} | 列数：{len(pivot_df.columns)}")
                                
                                if format_numbers:
                                    # 格式化数值列
                                    format_dict = {}
                                    for col in pivot_df.columns:
                                        if pd.api.types.is_numeric_dtype(pivot_df[col]):
                                            format_dict[col] = '{:,.2f}'
                                    
                                    st.dataframe(
                                        pivot_df.style.format(format_dict, na_rep='-'),
                                        use_container_width=True,
                                        height=min(600, (len(pivot_df) + 1) * 35 + 38)
                                    )
                                else:
                                    st.dataframe(
                                        pivot_df,
                                        use_container_width=True,
                                        height=min(600, (len(pivot_df) + 1) * 35 + 38)
                                    )
                                
                                # 导出Excel
                                st.markdown("---")
                                st.markdown("##### 📥 导出透视表")
                                
                                output = BytesIO()
                                with pd.ExcelWriter(output, engine='openpyxl') as writer:
                                    pivot_df.to_excel(writer, index=False, sheet_name='透视表')
                                output.seek(0)
                                
                                st.download_button(
                                    label="📊 导出为 Excel",
                                    data=output,
                                    file_name="pivot_table.xlsx",
                                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                    use_container_width=True
                                )
                                
                                # 统计摘要
                                st.markdown("---")
                                st.markdown("##### 📈 数据摘要")
                                summary_cols = st.columns(4)
                                
                                numeric_pivot_cols = pivot_df.select_dtypes(include=['number']).columns
                                if len(numeric_pivot_cols) > 0:
                                    first_numeric = numeric_pivot_cols[0]
                                    with summary_cols[0]:
                                        st.metric("总行数", len(pivot_df))
                                    with summary_cols[1]:
                                        st.metric("数值列数", len(numeric_pivot_cols))
                                    with summary_cols[2]:
                                        if show_totals and '总计' in pivot_df[row_col].values:
                                            total_val = pivot_df[pivot_df[row_col] == '总计'][first_numeric].iloc[0]
                                            st.metric("总计", f"{total_val:,.0f}")
                                        else:
                                            st.metric("总计", f"{pivot_df[first_numeric].sum():,.0f}")
                                    with summary_cols[3]:
                                        st.metric("平均值", f"{pivot_df[first_numeric].mean():,.2f}")
                                
                            except Exception as e:
                                st.error(f"生成透视表失败：{str(e)}")
                                st.info("提示：请确保选择的列包含合适的数据类型")

        elif st.session_state.analysis_mode == "多文件对比图表":
            ordered_keys = st.session_state.get('chart_df_keys', [])
            if len(ordered_keys) < 2:
                st.warning("⚠️ 请至少上传两个文件以进行对比。")
            else:
                # Find the file with the most rows to use as the reference
                longest_file_key = None
                max_rows = -1
                for key in ordered_keys:
                    num_rows = len(st.session_state['chart_dfs'][key]['df'])
                    if num_rows > max_rows:
                        max_rows = num_rows
                        longest_file_key = key
                
                reference_cols = st.session_state['chart_dfs'][longest_file_key]['cols']
                
                st.info(f"📊 数据最长的文件 '{st.session_state['chart_dfs'][longest_file_key]['name']}' ({max_rows} 行) 已被选为列名参考标准。")

                chart_type = st.selectbox("选择图表类型", ["条形图", "折线图", "散点图", "面积图"], key="compare_chart_type")
                x_axis = st.selectbox("选择 X 轴（对比基准）", reference_cols, key="compare_x")
                y_axis = st.selectbox("选择 Y 轴（对比数值）", reference_cols, index=1 if len(reference_cols) > 1 else 0, key="compare_y")

                st.markdown("---")
                st.markdown("##### ⚙️ 图表选项")
                
                c1, c2, c3, c4 = st.columns(4)
                with c1:
                    st.number_input("X轴角度", -90, 90, 45, 5, key="xaxis_angle_multi")
                with c2:
                    st.number_input("间隔阈值", 3, 5000, 25, 5, key="interval_threshold_multi")
                with c3:
                    st.number_input("间隔步长", 1, 10, 2, 1, key="interval_step_multi")
                with c4:
                    use_chinese_format_multi = st.checkbox("Y轴万单位", value=True, key="chinese_fmt_multi")

                st.markdown("##### 🎨 选择每个文件的颜色")
                ordered_keys = st.session_state.get('chart_df_keys', [])
                colors = []
                
                # 使用更好的颜色方案
                default_colors = ['#10a37f', '#f59e0b', '#3b82f6', '#ef4444', '#8b5cf6', '#ec4899', '#06b6d4', '#84cc16']
                
                color_cols = st.columns(len(ordered_keys))
                for i, key in enumerate(ordered_keys):
                    data = st.session_state['chart_dfs'][key]
                    with color_cols[i]:
                        default_color = default_colors[i % len(default_colors)]
                        color = st.color_picker(data['name'], default_color, key=f"compare_color_{key}")
                        colors.append(color)

                if st.button("📊 生成对比图表", key="gen_compare", use_container_width=True):
                    # Sort files by length (longest first) to control processing and legend order
                    files_with_lengths = [(k, len(st.session_state['chart_dfs'][k]['df'])) for k in ordered_keys]
                    sorted_files = sorted(files_with_lengths, key=lambda item: item[1], reverse=True)
                    sorted_keys = [item[0] for item in sorted_files]

                    combined_df = pd.DataFrame()
                    source_order = []
                    for key in sorted_keys:
                        data = st.session_state['chart_dfs'][key]
                        df_to_process = data['df']
                        
                        # Ensure the required columns exist before processing
                        if x_axis in df_to_process.columns and y_axis in df_to_process.columns:
                            source_order.append(data['name'])
                            temp_df = df_to_process[[x_axis, y_axis]].copy()
                            temp_df['来源'] = data['name']
                            combined_df = pd.concat([combined_df, temp_df], ignore_index=True)
                        else:
                            st.warning(f"⚠️ 文件 '{data['name']}' 因缺少 '{x_axis}' 或 '{y_axis}' 列而被跳过。")
                    
                    if combined_df.empty:
                        st.error("❌ 没有可用于生成图表的数据。请检查文件内容和列名。")
                        st.stop()

                    combined_df['来源'] = pd.Categorical(combined_df['来源'], categories=source_order, ordered=True)
                    y_data = combined_df[y_axis].astype(str).str.replace(',', '', regex=False)
                    combined_df[y_axis] = pd.to_numeric(y_data, errors='coerce')
                    
                    # Try to convert x-axis to datetime and sort for chronological plotting
                    try:
                        combined_df[x_axis] = pd.to_datetime(combined_df[x_axis])
                        combined_df = combined_df.sort_values(by=x_axis).reset_index(drop=True)
                    except (ValueError, TypeError):
                        # If conversion fails, proceed without sorting by date (e.g., for categorical data)
                        pass

                    fig = None
                    custom_data_cols = [x_axis, '来源']
                    if chart_type == "条形图":
                        fig = px.bar(combined_df, x=x_axis, y=y_axis, color='来源', title=f"{y_axis} vs {x_axis} 对比", barmode='group', color_discrete_sequence=colors, custom_data=custom_data_cols)
                    elif chart_type == "折线图":
                        fig = px.line(combined_df, x=x_axis, y=y_axis, color='来源', title=f"{y_axis} vs {x_axis} 对比", color_discrete_sequence=colors, custom_data=custom_data_cols)
                    elif chart_type == "散点图":
                        fig = px.scatter(combined_df, x=x_axis, y=y_axis, color='来源', title=f"{y_axis} vs {x_axis} 对比", color_discrete_sequence=colors, custom_data=custom_data_cols)
                    elif chart_type == "面积图":
                        fig = px.area(combined_df, x=x_axis, y=y_axis, color='来源', title=f"{y_axis} vs {x_axis} 对比", color_discrete_sequence=colors, custom_data=custom_data_cols)
                    
                    if fig:
                        fig.update_traces(hovertemplate=f"来源: %{{customdata[1]}}<br><b>{x_axis}:</b> %{{customdata[0]}}<br><b>{y_axis}:</b> %{{y}}<extra></extra>")
                        
                        # 应用中文格式
                        if use_chinese_format_multi:
                            y_vals = combined_df[y_axis].dropna()
                            tickvals = []
                            ticktext = []
                            y_min, y_max = 0, y_vals.max()
                            step = (y_max - y_min) / 8
                            for i in range(9):
                                val = y_min + i * step
                                tickvals.append(val)
                                ticktext.append(format_number_chinese(val))
                            fig.update_yaxes(tickvals=tickvals, ticktext=ticktext)
                        
                        angle = st.session_state.get("xaxis_angle_multi", 45)
                        threshold = st.session_state.get("interval_threshold_multi", 25)
                        step = st.session_state.get("interval_step_multi", 2)
                        
                        # Use the x-axis from the longest dataframe as the standard for ticks
                        x_axis_standard_df = st.session_state['chart_dfs'][longest_file_key]['df']
                        fig = update_xaxis_ticks(fig, x_axis_standard_df[x_axis], angle, threshold, step)
                        
                        fig.update_layout(
                            margin=dict(l=80, r=120, t=80, b=120),
                            height=600,
                            title_x=0.05,
                            legend=dict(
                                orientation="h",
                                yanchor="bottom",
                                y=1.02,
                                xanchor="right",
                                x=1
                            )
                        )
                        
                        st.session_state['last_fig'] = fig

    if st.session_state.get('last_fig'):
        st.plotly_chart(st.session_state.last_fig, use_container_width=True)
        st.markdown("---")
        st.markdown("##### 📥 导出图表")
        
        export_cols = st.columns(5)
        
        # PNG 导出
        with export_cols[0]:
            img_bytes = None
            try:
                img_bytes = st.session_state.last_fig.to_image(format="png", scale=2)
            except Exception as e:
                st.warning("PNG需要kaleido库")
                img_bytes = None
            
            if img_bytes:
                st.download_button(
                    label="PNG",
                    data=img_bytes,
                    file_name="chart.png",
                    mime="image/png",
                    use_container_width=True
                )
            else:
                st.button("PNG", disabled=True, use_container_width=True, help="需要安装kaleido库")
        
        # SVG 导出
        with export_cols[1]:
            try:
                svg_bytes = st.session_state.last_fig.to_image(format="svg")
                st.download_button(
                    label="SVG",
                    data=svg_bytes,
                    file_name="chart.svg",
                    mime="image/svg+xml",
                    use_container_width=True
                )
            except Exception as e:
                st.button("SVG", disabled=True, use_container_width=True, help="需要安装kaleido库")
        
        # HTML 导出
        with export_cols[2]:
            html_str = st.session_state.last_fig.to_html(include_plotlyjs='cdn')
            st.download_button(
                label="HTML",
                data=html_str.encode('utf-8'),
                file_name="chart.html",
                mime="text/html",
                use_container_width=True
            )
        
        # JSON 导出
        with export_cols[3]:
            json_str = st.session_state.last_fig.to_json()
            st.download_button(
                label="JSON",
                data=json_str.encode('utf-8'),
                file_name="chart.json",
                mime="application/json",
                use_container_width=True
            )
        
        # PDF 导出（可选）
        with export_cols[4]:
            try:
                pdf_bytes = st.session_state.last_fig.to_image(format="pdf")
                st.download_button(
                    label="PDF",
                    data=pdf_bytes,
                    file_name="chart.pdf",
                    mime="application/pdf",
                    use_container_width=True
                )
            except Exception as e:
                st.button("PDF", disabled=True, use_container_width=True, help="需要安装kaleido库")
        
        st.caption("💡 提示：HTML和JSON格式不需要额外依赖，可直接导出。PNG/SVG/PDF需要安装kaleido库。")
        
    st.markdown('</div>', unsafe_allow_html=True)

elif page == "📱 抖音下载":
    st.markdown("""
        <div style='padding: 30px 0 20px 0;'>
            <h1 style='margin: 0 0 8px 0; font-size: 32px; font-weight: 600; color: var(--text); letter-spacing: -0.5px;'>
                抖音视频解析
            </h1>
            <p style='margin: 0; color: var(--muted); font-size: 15px; line-height: 1.5;'>
                支持无水印下载，自动识别链接格式
            </p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="card" style="padding: 20px;">', unsafe_allow_html=True)
    
    douyin_url_input = st.text_input(
        "输入链接",
        placeholder="粘贴抖音分享内容...",
        label_visibility="collapsed",
        key="douyin_input"
    )
    
    parse_button = st.button("解析", use_container_width=True, type="primary")
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if parse_button and douyin_url_input:
        douyin_url = None
        
        import re
        url_patterns = [
            r'https?://[^\s]+douyin\.com[^\s]*',
            r'v\.douyin\.com/[^\s]+',
            r'www\.douyin\.com/[^\s]+',
            r'm\.douyin\.com/[^\s]+'
        ]
        
        for pattern in url_patterns:
            match = re.search(pattern, douyin_url_input)
            if match:
                douyin_url = match.group(0)
                douyin_url = douyin_url.rstrip('!！。.，,、')
                break
        
        if not douyin_url:
            douyin_url = douyin_url_input.strip()
        
        if douyin_url != douyin_url_input.strip():
            st.info(f"🔗 已识别链接：{douyin_url}")
        with st.spinner("正在解析视频信息..."):
            try:
                api_url = "https://zerorust.dev/api/douyin"
                
                response = requests.post(
                    api_url,
                    json={"url": douyin_url},
                    headers={"Content-Type": "application/json"},
                    timeout=30
                )
                
                if response.status_code == 200:
                    data = response.json()
                    st.session_state['douyin_data'] = data
                    st.success("✅ 解析成功！")
                else:
                    st.error(f"❌ 解析失败：HTTP {response.status_code}")
                    st.error(f"错误详情：{response.text}")
            except requests.exceptions.Timeout:
                st.error("❌ 请求超时，请稍后重试")
            except requests.exceptions.RequestException as e:
                st.error(f"❌ 网络请求失败：{str(e)}")
            except Exception as e:
                st.error(f"❌ 解析出错：{str(e)}")
    
    if 'douyin_data' in st.session_state:
        data = st.session_state['douyin_data']
        
        if 'code' in data and data['code'] != 200:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.error(f"❌ 解析失败：{data.get('message', '未知错误')}")
            st.markdown('</div>', unsafe_allow_html=True)
        elif 'data' in data:
            video_info = data['data']
            
            st.markdown('<div class="card" style="padding: 24px; margin-top: 16px;">', unsafe_allow_html=True)
            
            if 'cover' in video_info:
                st.image(video_info['cover'], use_container_width=True)
            
            if 'desc' in video_info and video_info['desc']:
                st.markdown(f"""
                    <div style='margin: 16px 0 20px 0; color: var(--text); font-size: 15px; line-height: 1.7; font-weight: 500;'>
                        {video_info['desc']}
                    </div>
                """, unsafe_allow_html=True)
            
            author_name = video_info.get('author_name', video_info.get('author', video_info.get('nickname', '')))
            create_time = video_info.get('create_time', video_info.get('createTime', ''))
            
            primary_stats_mapping = [
                ('comment_count', 'comment', 'commentCount', '评论', '💬'),
                ('like_count', 'digg_count', 'like', 'likeCount', 'diggCount', '点赞', '❤️'),
                ('share_count', 'share', 'shareCount', '分享', '📤'),
                ('collect_count', 'collect', 'collectCount', '收藏', '⭐')
            ]
            
            primary_stats = []
            for fields in primary_stats_mapping:
                *field_names, label, icon = fields
                value = None
                for field in field_names:
                    if field in video_info and video_info[field]:
                        value = video_info[field]
                        break
                if value is not None and value >= 0:
                    formatted_count = value
                    if value >= 10000:
                        formatted_count = f"{value/10000:.1f}w"
                    elif value >= 1000:
                        formatted_count = f"{value/1000:.1f}k"
                    else:
                        formatted_count = str(value)
                    primary_stats.append((label, formatted_count, icon))
            
            while len(primary_stats) < 4:
                primary_stats.append(('', '0', ''))
            
            st.markdown("""
                <table style='width: 100%; border-collapse: collapse; margin: 20px 0; background: linear-gradient(135deg, var(--accent-weak) 0%, rgba(16,163,127,0.03) 100%); border-radius: 12px; overflow: hidden; border: 1px solid rgba(16,163,127,.15);'>
                    <thead>
                        <tr style='background: rgba(16,163,127,0.08); border-bottom: 2px solid rgba(16,163,127,.2);'>
                            <th style='padding: 14px 16px; text-align: left; color: var(--text); font-weight: 600; font-size: 14px; width: 35%;'>信息</th>
            """, unsafe_allow_html=True)
            
            for label, formatted_count, icon in primary_stats:
                st.markdown(f"""
                    <th style='padding: 14px 10px; text-align: center; color: var(--text); font-weight: 600; font-size: 14px; width: 16.25%;'>
                        <div style='font-size: 20px; margin-bottom: 2px;'>{icon}</div>
                    </th>
                """, unsafe_allow_html=True)
            
            st.markdown("</tr></thead><tbody>", unsafe_allow_html=True)
            
            if author_name:
                st.markdown(f"""
                    <tr style='border-bottom: 1px solid rgba(16,163,127,.1);'>
                        <td style='padding: 14px 16px; color: var(--text); font-size: 14px;'>
                            <span style='color: var(--muted); margin-right: 6px;'>👤</span>{author_name}
                        </td>
                """, unsafe_allow_html=True)
                
                for label, formatted_count, icon in primary_stats:
                    st.markdown(f"""
                        <td style='padding: 14px 10px; text-align: center; color: var(--accent); font-weight: 700; font-size: 18px;'>
                            {formatted_count}
                        </td>
                    """, unsafe_allow_html=True)
                
                st.markdown("</tr>", unsafe_allow_html=True)
            
            if create_time:
                st.markdown(f"""
                    <tr>
                        <td style='padding: 14px 16px; color: var(--muted); font-size: 13px;'>
                            <span style='margin-right: 6px;'>📅</span>{create_time}
                        </td>
                """, unsafe_allow_html=True)
                
                for label, formatted_count, icon in primary_stats:
                    st.markdown(f"""
                        <td style='padding: 14px 10px; text-align: center; color: var(--muted); font-size: 12px; font-weight: 500;'>
                            {label}
                        </td>
                    """, unsafe_allow_html=True)
                
                st.markdown("</tr>", unsafe_allow_html=True)
            
            st.markdown("</tbody></table>", unsafe_allow_html=True)
            
            st.markdown('</div>', unsafe_allow_html=True)
            
            st.markdown('<div class="card" style="padding: 20px; margin-top: 16px;">', unsafe_allow_html=True)
            
            content_type = video_info.get('type', 'video')
            
            possible_video_fields = ['video_url', 'videoUrl', 'video', 'play_url', 'playUrl', 'download_url', 'downloadUrl', 'url', 'video_link', 'videoLink', 'play_addr', 'playAddr']
            video_url = None
            
            for field in possible_video_fields:
                if field in video_info:
                    value = video_info[field]
                    if isinstance(value, str) and value.startswith('http'):
                        video_url = value
                        break
                    elif isinstance(value, dict):
                        for sub_field in ['url', 'uri', 'link', 'url_list']:
                            if sub_field in value:
                                sub_value = value[sub_field]
                                if isinstance(sub_value, str) and sub_value.startswith('http'):
                                    video_url = sub_value
                                    break
                                elif isinstance(sub_value, list) and len(sub_value) > 0:
                                    video_url = sub_value[0]
                                    break
                        if video_url:
                            break
                    elif isinstance(value, list) and len(value) > 0:
                        if isinstance(value[0], str) and value[0].startswith('http'):
                            video_url = value[0]
                            break
            
            if content_type == 'video':
                if video_url:
                    with st.spinner("获取中..."):
                        try:
                            video_response = requests.get(video_url, timeout=30)
                            if video_response.status_code == 200:
                                video_bytes = video_response.content
                                file_size_mb = len(video_bytes) / 1024 / 1024
                                
                                st.markdown('<div style="margin-bottom: 12px;">', unsafe_allow_html=True)
                                st.download_button(
                                    label=f"下载原视频 · {file_size_mb:.1f} MB",
                                    data=video_bytes,
                                    file_name=f"douyin_{time.strftime('%Y%m%d_%H%M%S')}.mp4",
                                    mime="video/mp4",
                                    use_container_width=True,
                                    type="primary"
                                )
                                st.markdown('</div>', unsafe_allow_html=True)
                                
                                with st.expander("预览视频", expanded=False):
                                    st.video(video_bytes)
                            else:
                                st.error(f"❌ 获取视频失败 (HTTP {video_response.status_code})")
                                st.code(video_url, language="text")
                        except Exception as e:
                            st.error(f"❌ 下载失败：{str(e)}")
                            with st.expander("🔗 查看直链"):
                                st.code(video_url, language="text")
                else:
                    st.warning("⚠️ 未找到视频链接")
                    with st.expander("🔍 查看调试信息"):
                        st.json(video_info)
            
            elif content_type == 'image' or 'images' in video_info:
                images = video_info.get('images', [])
                if images:
                    st.success(f"🖼️ 找到 {len(images)} 张图片")
                    
                    cols_per_row = 3
                    for i in range(0, len(images), cols_per_row):
                        cols = st.columns(cols_per_row)
                        for j, col in enumerate(cols):
                            img_idx = i + j
                            if img_idx < len(images):
                                img_url = images[img_idx]
                                with col:
                                    try:
                                        img_response = requests.get(img_url, timeout=30)
                                        if img_response.status_code == 200:
                                            img_bytes = img_response.content
                                            st.image(img_bytes, use_container_width=True)
                                            st.download_button(
                                                label=f"⬇️ 图 {img_idx+1}",
                                                data=img_bytes,
                                                file_name=f"douyin_{img_idx+1}_{time.strftime('%H%M%S')}.jpg",
                                                mime="image/jpeg",
                                                use_container_width=True,
                                                key=f"img_{img_idx}"
                                            )
                                    except Exception as e:
                                        st.error(f"❌ 加载失败")
                    
                    st.markdown("<div class='divider'></div>", unsafe_allow_html=True)
                    
                    if st.button("📦 批量下载全部", use_container_width=True, type="primary"):
                        with st.spinner(f"正在打包 {len(images)} 张图片..."):
                            import zipfile
                            
                            zip_buffer = BytesIO()
                            success_count = 0
                            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                                for i, img_url in enumerate(images):
                                    try:
                                        img_response = requests.get(img_url, timeout=30)
                                        if img_response.status_code == 200:
                                            img_bytes = img_response.content
                                            zip_file.writestr(f"douyin_{i+1}.jpg", img_bytes)
                                            success_count += 1
                                    except:
                                        pass
                            
                            zip_buffer.seek(0)
                            st.download_button(
                                label=f"⬇️ 下载压缩包 ({success_count}/{len(images)} 张)",
                                data=zip_buffer.getvalue(),
                                file_name=f"douyin_{time.strftime('%Y%m%d_%H%M%S')}.zip",
                                mime="application/zip",
                                use_container_width=True
                            )
                else:
                    st.warning("⚠️ 未找到图片")
            else:
                st.info("📦 内容类型未知，请查看调试信息")
            
            st.markdown('</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="card">', unsafe_allow_html=True)
            st.error("❌ API返回数据格式异常")
            with st.expander("查看原始数据"):
                st.json(data)
            st.markdown('</div>', unsafe_allow_html=True)
