import os
import json
import time
from dataclasses import dataclass, asdict, field
import streamlit as st

st.set_page_config(page_title="Codenames GPT", layout="wide")

from codenames.game import Game
from codenames.players.codemaster_gpt import AICodemaster
from codenames.players.guesser_gpt import AIGuesser



# ---------------- UI helpers & styles ----------------

ROLE_COLORS = {
    "RED":      ("#ffebee", "#e53935"),   # bg, border
    "BLUE":     ("#e8f0ff", "#1e88e5"),
    "CIVILIAN": ("#f5f5f5", "#9e9e9e"),
    "NEUTRAL":  ("#f5f5f5", "#9e9e9e"),
    "ASSASSIN": ("#fff3e0", "#fb8c00"),
}
MARKER_WORDS = {"RED", "BLUE", "CIVILIAN", "NEUTRAL", "ASSASSIN"}
# SAVE_DIR = "ui_runs"   # where past games are stored as JSON
STRATEGY_LABELS = ["Default", "Cautious", "Risky", "COT", "Self Refine", "Solo Performance"]
STRATEGY_DIR = {
    "Default": "Default",
    "Cautious": "Cautious",
    "Risky": "Risky",
    "COT": "COT",
    "Self Refine": "SelfRefine",
    "Solo Performance": "SoloPerformance",
}

def get_save_dir(mock_mode: bool, cm_strategy_label: str, g_strategy_label: str) -> str:
    mode_dir = "MockMode" if mock_mode else "NoMockMode"
    cm_dir = STRATEGY_DIR.get(cm_strategy_label, "Default")
    g_dir = STRATEGY_DIR.get(g_strategy_label, "Default")
    # folder looks like: results/MockMode/CM-Cautious__G-Risky
    combo = f"CM-{cm_dir}__G-{g_dir}"
    return os.path.join("results", mode_dir, combo)


def clean_token(t: str) -> str:
    return str(t).replace("*", "").strip()

def is_marker(t: str) -> bool:
    return clean_token(t).upper() in MARKER_WORDS

def role_at(i, key_grid):
    try:
        return str(key_grid[i]).replace("*", "").strip().upper()
    except Exception:
        return None

def tile_html(text, bg="#fafafa", border="#ddd", color="#222"):
    return (
        f"<div style='border:2px solid {border};"
        f"background:{bg};color:{color};"
        f"border-radius:12px;padding:12px 10px;margin:6px;"
        f"text-align:center;font-weight:600;letter-spacing:.3px'>"
        f"{text}</div>"
    )

# Optional global CSS tweaks
st.markdown("""
<style>
.block-container {padding-top: 1.2rem;}
</style>
""", unsafe_allow_html=True)

# ---------------- Event capture ----------------

@dataclass
class EventLog:
    seed: float = 0.0
    board: list = field(default_factory=list)      # CURRENT board (labels only)
    key_grid: list = field(default_factory=list)   # roles aligned with board
    timeline: list = field(default_factory=list)   # [{type, ...}]
    final_score: int = 0
    did_win: bool = False
    started_at: float = 0.0                        # wall-clock start
    run_id: str = ""                               # file name id
    strategy: str = ""

    def to_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False, indent=2)

    @staticmethod
    def from_json(s: str):
        d = json.loads(s)
        return EventLog(**d)

class StreamObserver:
    def __init__(self):
        self.log = EventLog()

    def on_start(self, seed, words_in_play, key_grid):
        self.log.seed = seed
        self.log.started_at = time.time()
        # store cleaned labels; keep key_grid raw for role lookup
        self.log.board = [clean_token(w).upper() for w in words_in_play]
        self.log.key_grid = list(key_grid)
        # first timeline entry contains initial board snapshot
        self.log.timeline.append({
            "type": "start",
            "board_snapshot": list(self.log.board)
        })

    def on_clue(self, turn_num, clue, clue_num):
        self.log.timeline.append({
            "type": "clue",
            "turn": int(turn_num),
            "clue": str(clue),
            "num": int(clue_num)
        })

    def on_guess(self, guess_word, role, was_correct):
        # take a snapshot *before* mutating current board
        snapshot = list(self.log.board)

        guess_clean = clean_token(guess_word).upper()
        role_up = str(role).upper()

        # find guessed index in current board (matches label, not markers)
        idx = None
        for i, lbl in enumerate(snapshot):
            if clean_token(lbl).upper() == guess_clean:
                idx = i
                break
        # if not found (edge case), just append without snapshot mutation
        if idx is not None and role_up in MARKER_WORDS:
            # mark this tile in current board as revealed
            self.log.board[idx] = f"*{role_up}*"
            # reflect the same in the snapshot we store with this event
            snapshot[idx] = f"*{role_up}*"

        self.log.timeline.append({
            "type": "guess",
            "guess": guess_clean,
            "role": role_up,
            "correct": bool(was_correct),
            "board_snapshot": snapshot
        })

    def on_end(self, final_score, did_win):
        self.log.final_score = int(final_score)
        self.log.did_win = bool(did_win)

# ---------------- Persistence helpers ----------------


def ensure_save_dir(mock_mode: bool, cm_strategy_label: str, g_strategy_label: str):
    os.makedirs(get_save_dir(mock_mode, cm_strategy_label, g_strategy_label), exist_ok=True)

def list_saved_runs(mock_mode: bool, cm_strategy_label: str, g_strategy_label: str):
    ensure_save_dir(mock_mode, cm_strategy_label, g_strategy_label)
    base = get_save_dir(mock_mode, cm_strategy_label, g_strategy_label)
    files = [f for f in os.listdir(base) if f.endswith(".json")]
    files.sort(reverse=True)
    return files

def save_run(log: EventLog, mock_mode: bool, cm_strategy_label: str, g_strategy_label: str):
    ensure_save_dir(mock_mode, cm_strategy_label, g_strategy_label)
    ts = time.strftime("%Y%m%d-%H%M%S", time.localtime(log.started_at or time.time()))
    run_id = f"{ts}_{int(log.seed)}.json" if isinstance(log.seed, (int, float)) else f"{ts}.json"
    log.run_id = run_id
    path = os.path.join(get_save_dir(mock_mode, cm_strategy_label, g_strategy_label), run_id)
    with open(path, "w", encoding="utf-8") as f:
        f.write(log.to_json())
    return run_id

def load_run(mock_mode: bool, cm_strategy_label: str, g_strategy_label: str, run_id: str) -> EventLog:
    path = os.path.join(get_save_dir(mock_mode, cm_strategy_label, g_strategy_label), run_id)
    with open(path, "r", encoding="utf-8") as f:
        return EventLog.from_json(f.read())

    
STATS_PATH = os.path.join("results", "tech_stats.json")

def _ensure_results_dir():
    os.makedirs("results", exist_ok=True)

def _load_stats_from_disk():
    _ensure_results_dir()
    try:
        with open(STATS_PATH, "r", encoding="utf-8") as f:
            data = json.load(f)

        # ---- migrate old formats ----
        # If old file used "Real", rename to "OpenAI"
        if "OpenAI" not in data and "Real" in data:
            data["OpenAI"] = data.pop("Real")

        # Ensure both buckets exist
        if "Mock" not in data:
            data["Mock"] = {}
        if "OpenAI" not in data:
            data["OpenAI"] = {}

        return data
    except FileNotFoundError:
        return {"Mock": {}, "OpenAI": {}}  # first run
    except Exception:
        # corrupted/unexpected -> start clean
        return {"Mock": {}, "OpenAI": {}}

def _save_stats_to_disk_atomic(stats_dict: dict):
    _ensure_results_dir()
    tmp = STATS_PATH + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(stats_dict, f, ensure_ascii=False, indent=2)
    os.replace(tmp, STATS_PATH)  


# ---------------- Run a game ----------------


def run_game(mock_mode: bool, cm_strategy_label: str, g_strategy_label: str) -> EventLog:
    if mock_mode:
        os.environ["MOCK_GPT"] = "1"
    else:
        os.environ.pop("MOCK_GPT", None)

    observer = StreamObserver()
    game = Game(
        AICodemaster,
        AIGuesser,
        seed="time",
        do_print=True,
        do_log=True,
        game_name="ui_run",
        cm_kwargs={"strategy": cm_strategy_label},
        g_kwargs={"strategy": g_strategy_label},   # 👈 pass to guesser
        observer=observer,
    )
    game.run()
    save_run(observer.log, mock_mode, cm_strategy_label, g_strategy_label)
    return observer.log


# --------- Stats helpers ---------

def _turns_from_log(log) -> int:
    turns = 0
    for e in getattr(log, "timeline", []):
        if isinstance(e, dict) and e.get("type") == "clue":
            try: turns = max(turns, int(e.get("turn", 0)))
            except: pass
    return turns

def _did_win_from_log(log):
    if hasattr(log, "did_win"): return bool(log.did_win)
    try:
        last = (getattr(log, "timeline", []) or [{}])[-1]
        msg = str(last.get("result") or last.get("status") or "").lower()
        if "win" in msg: return True
        if "lose" in msg or "loss" in msg or "assassin" in msg: return False
    except: pass
    return None

def _update_tech_stats(strategy: str, log, mock_mode: bool):
    # choose bucket
    bucket = st.session_state.tech_stats["Mock" if mock_mode else "OpenAI"]
    rec = bucket.setdefault(strategy, {"runs": 0, "wins": 0, "losses": 0, "turns": []})

    rec["runs"] += 1
    win = _did_win_from_log(log)
    if win is True:  rec["wins"] += 1
    elif win is False: rec["losses"] += 1
    rec["turns"].append(_turns_from_log(log))

    # persist to disk after every run
    _save_stats_to_disk_atomic(st.session_state.tech_stats)



# ---------------- Streamlit UI ----------------


st.title("🧩 Codenames GPT — Interactive UI")

if "game_log" not in st.session_state:
    st.session_state.game_log = None
if "tech_stats" not in st.session_state:
    st.session_state.tech_stats = _load_stats_from_disk()


with st.sidebar:
    st.header("Run a new game")
    mock_mode = st.toggle("Mock mode (no API calls)", value=True)
    cm_strategy_label = st.selectbox("Codemaster strategy", STRATEGY_LABELS, index=0)
    g_strategy_label = st.selectbox("Guesser strategy", STRATEGY_LABELS, index=0)
    start_btn = st.button("Run Game")
    st.caption(f"Saves to: `{get_save_dir(mock_mode, cm_strategy_label, g_strategy_label)}`")

    st.markdown("---")
    st.header("Past games")
    saved = list_saved_runs(mock_mode, cm_strategy_label, g_strategy_label)
    selection = st.selectbox(
        "Choose a past run",
        options=["-- select --"] + saved,
        index=0
    )
    load_btn = st.button("Load selected")



# start a new game
if start_btn:
    with st.spinner("Running game..."):
        st.session_state.game_log = run_game(
            mock_mode,
            cm_strategy_label,
            g_strategy_label,
        )
        # if you want to see CM+G in stats:
        _update_tech_stats(f"CM:{cm_strategy_label} / G:{g_strategy_label}",
                           st.session_state.game_log,
                           mock_mode)
        st.success(f"Saved run: {st.session_state.game_log.run_id}")

# load a saved game

if load_btn and selection != "-- select --":
    try:
        st.session_state.game_log = load_run(
            mock_mode,
            cm_strategy_label,
            g_strategy_label,
            selection,
        )
        st.success(f"Loaded run: {selection}")
    except Exception as e:
        st.error(f"Failed to load: {e}")


log = st.session_state.game_log

if not log:
    st.info("Click **Run Game** or pick one under **Past games**.")
else:
    st.subheader("Board")

    reveal = st.toggle(
        "Reveal colors (show roles)",
        value=bool(log.did_win),  # auto-reveal after the game ends
        help="During the game keep this off; after finishing, toggle to reveal RED/BLUE/CIVILIAN/ASSASSIN."
    )

    # render current board
    cols = st.columns(5)
    for i in range(len(log.board)):
        label = clean_token(log.board[i]).upper()
        role = role_at(i, log.key_grid)

        if is_marker(log.board[i]):
            # shown as revealed tile (role-only)
            bg, border = ROLE_COLORS.get(role or "NEUTRAL", ("#eee", "#999"))
            show_text = role.title() if reveal else "?"
            html = tile_html(show_text, bg if reveal else "#fafafa", border if reveal else "#ddd")
        else:
            if reveal and role in ROLE_COLORS:
                bg, border = ROLE_COLORS[role]
                html = tile_html(label, bg, border, "#111")
            else:
                html = tile_html(label, "#fafafa", "#ddd", "#111")

        cols[i % 5].markdown(html, unsafe_allow_html=True)

    with st.expander("Legend"):
        lg = []
        for r, (bg, border) in ROLE_COLORS.items():
            lg.append(tile_html(r.title(), bg, border))
        st.markdown("<div style='display:flex;flex-wrap:wrap'>" + "".join(lg) + "</div>", unsafe_allow_html=True)

    st.markdown("---")
    st.subheader("Timeline (replay)")

    for event in log.timeline:
        if event["type"] == "start":
            st.caption("Game started.")
        elif event["type"] == "clue":
            st.markdown(
                f"🎯 **Turn {event['turn']} — Clue:** `{event['clue']}` for **{event['num']}**"
            )
        elif event["type"] == "guess":
            emoji = "✅" if event["correct"] else "❌"
            st.markdown(
                f"{emoji} **Guess:** `{event['guess']}`  (_role: {event['role']}_)"
            )
            # show snapshot of board state right after this guess
            snapshot = event.get("board_snapshot")
            if snapshot:
                cols = st.columns(5)
                for i, cell in enumerate(snapshot):
                    label = clean_token(cell).upper()
                    role = role_at(i, log.key_grid)
                    if is_marker(cell):
                        bg, border = ROLE_COLORS.get(role or "NEUTRAL", ("#eee", "#999"))
                        html = tile_html(role.title(), bg, border, "#111")
                    else:
                        html = tile_html(label, "#fafafa", "#ddd", "#111")
                    cols[i % 5].markdown(html, unsafe_allow_html=True)

    st.markdown("---")
    result_text = "✅ Win" if log.did_win else "❌ Loss"
    ts = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(log.started_at or time.time()))
    st.subheader(f"Result: {result_text}  ·  Score: **{log.final_score}**  ·  Seed: `{log.seed}`  ·  Started: {ts}")
    if log.run_id:
        st.caption(f"Run ID: {log.run_id}")

    
