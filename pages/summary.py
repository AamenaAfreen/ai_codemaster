
import streamlit as st
from statistics import mean, median, pstdev
import pandas as pd
import os, json

st.title("Summary")

# ---- persistent store path ----
STATS_PATH = os.path.join("results", "tech_stats.json")

# ---- helpers: load/save ----
def _load_stats_from_disk():
    try:
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)
        # migrate old "Real" bucket to "OpenAI" if present
        if "OpenAI" not in data and "Real" in data:
            data["OpenAI"] = data.pop("Real")
        data.setdefault("Mock", {})
        data.setdefault("OpenAI", {})
        return data
    except FileNotFoundError:
        return {"Mock": {}, "OpenAI": {}}
    except Exception:
        return {"Mock": {}, "OpenAI": {}}

def _save_stats_to_disk(stats):
    os.makedirs("results", exist_ok=True)
    tmp = STATS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATS_PATH)

# ---- summary math ----
def summarize(rec: dict):
    t = rec.get("turns", [])
    n = len(t)
    runs = rec.get("runs", n)
    losses = rec.get("losses", 0)
    return {
        "Runs": runs,
        "Mean turns": round(mean(t), 3) if n else 0,
        "Median": median(t) if n else 0,
        "Min": min(t) if n else 0,
        "Std": round(pstdev(t), 3) if n >= 2 else 0.0,
        "Wins": rec.get("wins", 0),
        "Losses": losses,
        "Loss rate": f"{(losses / runs * 100):.1f}%" if runs else "0.0%",
    }

def build_df(tech_dict: dict) -> pd.DataFrame:
    rows = []
    for tech, rec in tech_dict.items():
        row = {"Technique": tech}
        row.update(summarize(rec))
        rows.append(row)
    rows.sort(key=lambda r: r["Technique"].lower())
    if rows:
        return pd.DataFrame(rows)
    return pd.DataFrame(columns=["Technique","Runs","Mean turns","Median","Min","Std","Wins","Losses","Loss rate"])

def add_totals(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    numeric_cols = ["Runs","Mean turns","Median","Min","Std","Wins","Losses"]
    totals = {c: (df[c].sum() if c in ["Runs","Wins","Losses"] else "") for c in numeric_cols}
    totals["Technique"] = "— Total —"
    totals["Loss rate"] = f"{(totals['Losses']/totals['Runs']*100):.1f}%" if totals["Runs"] else "0.0%"
    return pd.concat([df, pd.DataFrame([totals])], ignore_index=True)

# ---- working copy of stats (prefer session, fallback to disk) ----
stats = st.session_state.get("tech_stats", {"Mock": {}, "OpenAI": {}})

# ---- controls ----
col1, col2 = st.columns(2)
if col1.button("Reload from disk"):
    st.session_state.tech_stats = _load_stats_from_disk()
    stats = st.session_state.tech_stats
    st.success("Reloaded summary from results/tech_stats.json")

if col2.button("Clear summary (both buckets)"):
    st.session_state.tech_stats = {"Mock": {}, "OpenAI": {}}
    _save_stats_to_disk(st.session_state.tech_stats)
    stats = st.session_state.tech_stats
    st.warning("Cleared summary. File updated.")

# ---- tabs: Mock vs OpenAI ----
tab1, tab2 = st.tabs(["Mock mode", "OpenAI"])

with tab1:
    df = build_df(stats.get("Mock", {}))
    df = add_totals(df)
    st.dataframe(df, use_container_width=True)
    st.download_button(
        "Download CSV (Mock)",
        df.to_csv(index=False).encode("utf-8"),
        file_name="summary_mock.csv",
        mime="text/csv",
    )

with tab2:
    df = build_df(stats.get("OpenAI", {}))
    df = add_totals(df)
    st.dataframe(df, use_container_width=True)
    st.download_button(
        "Download CSV (OpenAI)",
        df.to_csv(index=False).encode("utf-8"),
        file_name="summary_openai.csv",
        mime="text/csv",
    )
