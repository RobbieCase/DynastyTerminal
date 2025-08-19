
import streamlit as st
import pandas as pd
from typing import List, Dict

st.set_page_config(page_title="Dynasty Superflex Draft War Room", layout="wide")

# -------------------------------
# Utilities
# -------------------------------
def load_rankings(src) -> pd.DataFrame:
    df = pd.read_csv(src)
    cols = {c.lower().strip(): c for c in df.columns}
    def get(col_candidates, default=None):
        for c in col_candidates:
            if c in df.columns:
                return df[c]
            lc = c.lower()
            if lc in cols:
                return df[cols[lc]]
        return default
    out = pd.DataFrame({
        "rk": pd.to_numeric(get(["RK", "Rank", "Overall Rank"]), errors="coerce"),
        "player": get(["PLAYER NAME","Player","Name"]).astype(str),
        "team": get(["TEAM","Tm"]).astype(str),
        "pos_raw": get(["POS","Position"]).astype(str),
        "age": pd.to_numeric(get(["AGE","Age"]), errors="coerce"),
        "tier": get(["TIERS","Tier"], pd.Series([""] * len(df)))
    })
    out = out.dropna(subset=["rk"])
    out["pos"] = out["pos_raw"].str.extract(r"([A-Z]+)")
    out = out.sort_values("rk").reset_index(drop=True)
    return out

def bucket_label(rk: int) -> str:
    if rk <= 36:
        return "Rounds 1–3"
    elif rk <= 72:
        return "Rounds 4–6"
    elif rk <= 120:
        return "Rounds 7–10"
    elif rk <= 180:
        return "Rounds 11–15"
    return "Rounds 16+"

BUCKET_ORDER = ["Rounds 1–3","Rounds 4–6","Rounds 7–10","Rounds 11–15","Rounds 16+"]

BUCKET_POS_PRIORITY: Dict[str, List[str]] = {
    "Rounds 1–3":  ["QB","WR","RB","TE"],
    "Rounds 4–6":  ["WR","RB","TE","QB"],
    "Rounds 7–10": ["QB","WR","RB","TE"],
    "Rounds 11–15":["RB","WR","TE","QB"],
    "Rounds 16+":  ["QB","RB","WR","TE"],
}

def superflex_score(row, round_num:int, strategy:str):
    score = row["rk"]
    if pd.notna(row["age"]) and row["age"] <= 26:
        score -= 2.5
    if strategy == "QB Avalanche (QB-Heavy)":
        if row["pos"] == "QB":
            score -= 16 if round_num <= 5 else 10
        elif row["pos"] == "WR":
            score -= 2 if round_num <= 6 else 0
        elif row["pos"] == "RB" and round_num <= 4:
            score += 4
    elif strategy == "Balanced (Hero WR)":
        if row["pos"] == "WR":
            score -= 8 if round_num <= 6 else 3
        if row["pos"] == "QB":
            score -= 10 if round_num <= 3 else 4
        if row["pos"] == "TE" and round_num in (4,5,6):
            score -= 2.5
        if row["pos"] == "RB" and round_num <= 4:
            score += 6
    elif strategy == "Zero RB (Dynasty)":
        if row["pos"] == "QB":
            score -= 12 if round_num <= 6 else 6
        if row["pos"] == "WR":
            score -= 10 if round_num <= 7 else 4
        if row["pos"] == "TE" and round_num in (3,4,5,6):
            score -= 3
        if row["pos"] == "RB" and round_num <= 6:
            score += 8
    return score

def compute_lineup(my_df: pd.DataFrame) -> Dict[str, pd.DataFrame]:
    # Return dict of lineup slots based on ADP (rk)
    if my_df.empty:
        return {
            "QB1": my_df.head(0),
            "RB2": my_df.head(0),
            "WR3": my_df.head(0),
            "TE1": my_df.head(0),
            "FLEX2": my_df.head(0),
            "SFLX1": my_df.head(0),
            "BENCH": my_df.head(0),
        }
    mys = my_df.sort_values("rk")
    q = mys[mys["pos"]=="QB"]
    rb = mys[mys["pos"]=="RB"]
    wr = mys[mys["pos"]=="WR"]
    te = mys[mys["pos"]=="TE"]

    def take(df, n): return df.head(n)
    QB1 = take(q,1)
    RB2 = take(rb,2)
    WR3 = take(wr,3)
    TE1 = take(te,1)

    used_names = set(pd.concat([QB1,RB2,WR3,TE1])["player"])

    wrtete = mys[(mys["pos"]!="QB") & (~mys["player"].isin(used_names))]
    FLEX2 = take(wrtete,2)
    used2_names = used_names | set(FLEX2["player"])

    pool = mys[~mys["player"].isin(used2_names)]
    SFLX1 = take(pool,1)
    used3_names = used2_names | set(SFLX1["player"])

    BENCH = mys[~mys["player"].isin(used3_names)]

    return {
        "QB1": QB1,
        "RB2": RB2,
        "WR3": WR3,
        "TE1": TE1,
        "FLEX2": FLEX2,
        "SFLX1": SFLX1,
        "BENCH": BENCH,
    }

# -------------------------------
# Sidebar: Data + Settings
# -------------------------------
with st.sidebar:
    st.header("Setup")
    src_choice = st.radio("Rankings source", ["Use default path", "Upload CSV"])
    if src_choice == "Use default path":
        default_path = "FantasyPros_2025_Dynasty_OP_Rankings.csv"
        csv_path = st.text_input("CSV file path", value=default_path)
        df = load_rankings(csv_path)
    else:
        upl = st.file_uploader("Upload FantasyPros CSV", type=["csv"])
        if upl is None:
            st.stop()
        df = load_rankings(upl)

    slot = st.slider("Your draft slot (12-team snake)", 1, 12, 6)
    current_round = st.number_input("Current round", min_value=1, max_value=40, value=1, step=1)
    strategy = st.selectbox("Strategy", ["QB Avalanche (QB-Heavy)", "Balanced (Hero WR)", "Zero RB (Dynasty)"])
    st.caption("Tip: click 'Refresh queue' each round to re-bias the board for that round + strategy.")

# -------------------------------
# Session State
# -------------------------------
for key, default in {
    "queue": [],
    "off_board": [],
    "my_team": [],
}.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Compute buckets
df["bucket"] = df["rk"].apply(bucket_label)

# Dashboard header
st.title("🏈 Dynasty Superflex Draft War Room")
st.caption("Live drafting: manage queue, mark opponents, build your team, and see lineup fill in real time.")

# Filters row
f1, f2, f3, f4 = st.columns([1,1,1,1])
with f1:
    pos_filter = st.multiselect("Positions", ["QB","WR","RB","TE"], default=["QB","WR","RB","TE"])
with f2:
    max_age = st.slider("Max age", 18, 40, 40)
with f3:
    bucket_sel = st.multiselect("Buckets", BUCKET_ORDER, default=BUCKET_ORDER)
with f4:
    name_query = st.text_input("Search player")

# Strategy-adjusted board
board = df.copy()
board = board[(board["pos"].isin(pos_filter)) & (board["age"].fillna(99) <= max_age) & (board["bucket"].isin(bucket_sel))]
if name_query.strip():
    s = name_query.strip().lower()
    board = board[board["player"].str.lower().str.contains(s)]

board = board.copy()
board["sf_score"] = board.apply(lambda x: superflex_score(x, int(current_round), strategy), axis=1)
board = board.sort_values(["bucket","sf_score","rk"])

# Remove already taken
taken = set([p["player"] for p in st.session_state.off_board] + [p["player"] for p in st.session_state.my_team])
display_board = board[~board["player"].isin(taken)]

# Initialize queue from the display board (once)
if len(st.session_state.queue) == 0:
    st.session_state.queue = display_board.head(40).to_dict(orient="records")

# -------------------------------
# Top dashboard: counts & targets
# -------------------------------
my_df = pd.DataFrame(st.session_state.my_team)
if not my_df.empty:
    my_counts = my_df["pos"].value_counts().to_dict()
else:
    my_counts = {}

targets = {"QB": 3, "RB": 5, "WR": 7, "TE": 2}  # end-of-draft guideline
dcols = st.columns(4)
for i, p in enumerate(["QB","RB","WR","TE"]):
    with dcols[i]:
        have = my_counts.get(p,0)
        need = targets[p]
        st.metric(label=f"{p} drafted", value=have, delta=f"target {need}")

st.divider()

# -------------------------------
# Main layout
# -------------------------------
c1, c2, c3 = st.columns([1.3, 1, 1])

# ---- Suggested Queue ----
with c1:
    st.subheader("🎯 Suggested Queue")
    if st.button("Refresh queue from current round & filters"):
        st.session_state.queue = display_board.head(50).to_dict(orient="records")

    new_queue = []
    for i, rec in enumerate(st.session_state.queue):
        if rec["player"] in taken:
            continue
        with st.container(border=True):
            st.markdown(f"**{rec['player']}** — {rec['team']} • {rec['pos']} • Age {'' if pd.isna(rec['age']) else int(rec['age'])}  \n"
                        f"ADP RK {int(rec['rk'])} • {rec['bucket']}")
            b1,b2,b3,b4 = st.columns([0.15,0.15,0.35,0.35])
            if b1.button("⬆️", key=f"up_{rec['player']}") and i>0:
                st.session_state.queue[i-1], st.session_state.queue[i] = st.session_state.queue[i], st.session_state.queue[i-1]
            if b2.button("⬇️", key=f"dn_{rec['player']}") and i < len(st.session_state.queue)-1:
                st.session_state.queue[i+1], st.session_state.queue[i] = st.session_state.queue[i], st.session_state.queue[i+1]
            if b3.button("➕ My Team", key=f"add_{rec['player']}"):
                st.session_state.my_team.append({"player": rec["player"], "team": rec["team"], "pos": rec["pos"], "age": rec["age"], "rk": rec["rk"], "bucket": rec["bucket"]})
            if b4.button("🚫 Drafted", key=f"off_{rec['player']}"):
                st.session_state.off_board.append({"player": rec["player"], "team": rec["team"], "pos": rec["pos"], "age": rec["age"], "rk": rec["rk"], "bucket": rec["bucket"]})
        new_queue.append(rec)
    st.session_state.queue = new_queue

# ---- My Team ----
with c2:
    st.subheader("📋 My Team")
    if len(st.session_state.my_team)==0:
        st.info("No players yet. Use ➕ to add from the queue.")
    else:
        tdf = pd.DataFrame(st.session_state.my_team).sort_values(["pos","rk"])
        st.dataframe(tdf, use_container_width=True, hide_index=True)
        for idx, p in enumerate(st.session_state.my_team):
            if st.button(f"Remove {p['player']}", key=f"rm_team_{idx}"):
                st.session_state.my_team.pop(idx)
                st.rerun()
        st.download_button("⬇️ Export My Team (CSV)", data=tdf.to_csv(index=False), file_name="my_team.csv", mime="text/csv")

# ---- Drafted (Off Board) ----
with c3:
    st.subheader("🧱 Drafted (Off Board)")
    if len(st.session_state.off_board)==0:
        st.info("Mark opponents' picks with 🚫")
    else:
        odf = pd.DataFrame(st.session_state.off_board).sort_values(["pos","rk"])
        st.dataframe(odf, use_container_width=True, hide_index=True)
        for idx, p in enumerate(st.session_state.off_board):
            if st.button(f"Undo {p['player']}", key=f"rm_off_{idx}"):
                st.session_state.off_board.pop(idx)
                st.rerun()

st.divider()

# -------------------------------
# Lineup Builder (auto from My Team)
# -------------------------------
st.subheader("📐 Auto Lineup from My Team")
if len(st.session_state.my_team)==0:
    st.caption("Add players to 'My Team' to see suggested starters & bench.")
else:
    lineup = compute_lineup(pd.DataFrame(st.session_state.my_team))
    l1,l2 = st.columns([1,1])
    with l1:
        st.markdown("**QB (1)**")
        st.dataframe(lineup["QB1"], hide_index=True, use_container_width=True)
        st.markdown("**RB (2)**")
        st.dataframe(lineup["RB2"], hide_index=True, use_container_width=True)
        st.markdown("**WR (3)**")
        st.dataframe(lineup["WR3"], hide_index=True, use_container_width=True)
        st.markdown("**TE (1)**")
        st.dataframe(lineup["TE1"], hide_index=True, use_container_width=True)
    with l2:
        st.markdown("**FLEX (2)** — best WR/RB/TE remaining")
        st.dataframe(lineup["FLEX2"], hide_index=True, use_container_width=True)
        st.markdown("**SUPERFLEX (1)** — best remaining")
        st.dataframe(lineup["SFLX1"], hide_index=True, use_container_width=True)
        st.markdown("**BENCH — remaining**")
        st.dataframe(lineup["BENCH"], hide_index=True, use_container_width=True)

st.caption("Pro tip: Use filters + Refresh queue each round. Keep 3–4 QBs total, flood young WRs, and harvest RB value later.")
