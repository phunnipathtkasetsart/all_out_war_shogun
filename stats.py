import csv
import os
import time
import datetime
import pygame

# lazy debug1 */ Fix territory gains/lost */
gain = 0 #lazy debug
lost = 0
def territory_helper(territories, max_t):
    global gain,lost
    # Stats for subtitle
    gains  = sum(1 for t in range(2, max_t+1) if territories[t] > territories[t-1] > 0)
    gain = gains
    losses = sum(1 for t in range(2, max_t+1) if 0 < territories[t] < territories[t-1])
    lost = losses




# ── CSV logger ────────────────────────────────────────────────────────────────
class StatsLogger:
    """
    Logs every game event as a row in a CSV file.
    Each game gets its own file: Game_N_DD-M-YYYY.csv
    """

    FIELDS = ["turn", "time_elapsed", "event_type", "clan",
              "province", "units", "provinces", "damage", "units_lost"]

    def __init__(self, save_dir: str = "."):
        self.save_dir   = save_dir
        self.rows: list = []
        self._game_start_time = time.time()
        self._turn_start_time = time.time()
        self.csv_path   = self._make_path()

    def _make_path(self) -> str:
        os.makedirs(self.save_dir, exist_ok=True)
        # Count existing game files to get next game number
        existing = [f for f in os.listdir(self.save_dir)
                    if f.startswith("Game_") and f.endswith(".csv")]
        n = len(existing) + 1
        today = datetime.date.today()
        fname = f"Game_{n}_{today.day}-{today.month}-{today.year}.csv"
        return os.path.join(self.save_dir, fname)

    def reset_turn_timer(self):
        self._turn_start_time = time.time()

    def _elapsed(self) -> float:
        return round(time.time() - self._turn_start_time, 1)

    def log(self, turn: int, event_type: str, clan: str,
            province: str = "", units: int = 0, provinces: int = 0, damage: int = 0, units_lost: int = 0):
        self.rows.append({
            "turn":         turn,
            "time_elapsed": self._elapsed(),
            "event_type":   event_type,
            "clan":         clan,
            "province":     province,
            "units":        units,
            "provinces":    provinces,
            "damage":       damage,
            "units_lost":   units_lost,
        })

    def save(self):
        """Write all rows to CSV."""
        try:
            with open(self.csv_path, "w", newline="", encoding="utf-8") as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDS)
                writer.writeheader()
                writer.writerows(self.rows)
        except Exception as e:
            print(f"[Stats] Failed to save CSV: {e}")

    @staticmethod
    def load(path: str) -> list:
        """Load rows from an existing CSV file."""
        rows = []
        try:
            with open(path, newline="", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append({
                        "turn":         int(row.get("turn", 0)),
                        "time_elapsed": float(row.get("time_elapsed", 0)),
                        "event_type":   row.get("event_type", ""),
                        "clan":         row.get("clan", ""),
                        "province":     row.get("province", ""),
                        "units":        int(row.get("units", 0)),
                        "provinces":    int(row.get("provinces", 0)),
                        "damage":       int(row.get("damage", 0)),
                        "units_lost":   int(row.get("units_lost", 0)),
                    })
        except Exception as e:
            print(f"[Stats] Failed to load CSV: {e}")
        return rows

    @staticmethod
    def list_saved_games(save_dir: str = ".") -> list:
        """Return sorted list of saved CSV paths."""
        try:
            files = [os.path.join(save_dir, f)
                     for f in os.listdir(save_dir)
                     if f.startswith("Game_") and f.endswith(".csv")]
            return sorted(files)
        except Exception:
            return []


# ── Data analysis helpers ─────────────────────────────────────────────────────

def _summarise(rows: list, player_clan: str) -> dict:
    """Derive summary stats from raw rows."""
    s = {
        "total_turns":       0,
        "recruited":         0,
        "lost":              0,
        "cities_gained":     0,
        "cities_lost":       0,
        "damage_dealt":      0,
        "damage_taken":      0,
        "result":            "Unknown",
    }
    for r in rows:
        et = r["event_type"]
        clan = r["clan"]
        is_player = clan == player_clan

        if et == "TURN_SNAPSHOT" and is_player:
            s["total_turns"] = max(s["total_turns"], r["turn"])
        elif et == "RECRUIT" and is_player:
            s["recruited"] += r["units"]
        elif et in ("BATTLE_WIN", "BATTLE_LOSS", "SIEGE_WIN", "SIEGE_LOSS",
                    "AMBUSH_WIN", "AMBUSH_LOSS") and is_player:
            s["damage_dealt"] += r.get("damage", 0)      # our power dealt to enemy
            s["damage_taken"] += r.get("units", 0)       # enemy power dealt to us
            s["lost"]         += r.get("units_lost", 0)  # actual soldier units we lost
        if et == "SIEGE_WIN" and is_player:
            s["cities_gained"] += 1
        elif et == "SIEGE_WIN" and not is_player:
            s["cities_lost"] += 1
        elif et == "REBELLION" and is_player:
            s["cities_lost"] += 1

    return s


def _per_turn(rows: list, player_clan: str, max_turn: int):
    """Build per-turn arrays for graphing."""
    recruited     = [0] * (max_turn + 1)
    lost          = [0] * (max_turn + 1)
    dmg_dealt     = [0] * (max_turn + 1)
    dmg_taken     = [0] * (max_turn + 1)
    territories   = [0] * (max_turn + 1)   # total player territories at end of turn
    time_per      = [0.0] * (max_turn + 1)
    clan_power    = {}

    BATTLE_EVENTS = ("BATTLE_WIN", "BATTLE_LOSS",
                     "SIEGE_WIN",  "SIEGE_LOSS",
                     "AMBUSH_WIN", "AMBUSH_LOSS")

    for r in rows:
        t    = min(r["turn"], max_turn)
        et   = r["event_type"]
        clan = r["clan"]
        is_p = clan == player_clan

        if et == "RECRUIT" and is_p:
            recruited[t] += r["units"]

        if et in BATTLE_EVENTS and is_p:
            # damage = our power dealt to enemy (damage dealt)
            # units  = enemy power dealt to us  (damage taken)
            # units_lost = actual soldier unit losses
            dmg_dealt[t] += r.get("damage", 0)
            dmg_taken[t] += r.get("units", 0)
            lost[t]      += r.get("units_lost", 0)

        if et == "TURN_SNAPSHOT":
            if clan not in clan_power:
                clan_power[clan] = [0] * (max_turn + 1)
            clan_power[clan][t] = r["units"]
            if is_p:
                time_per[t]    = r["time_elapsed"]
                territories[t] = r["provinces"]

    # Carry-forward territories — fill gaps between snapshots
    # so graph shows a continuous line rather than spiky zeros
    last_known = 0
    for t in range(1, max_turn + 1):
        if territories[t] > 0:
            last_known = territories[t]
        elif last_known > 0:
            territories[t] = last_known

    return dict(recruited=recruited, lost=lost,
                dmg_dealt=dmg_dealt, dmg_taken=dmg_taken,
                territories=territories,
                clan_power=clan_power, time_per=time_per)


# ── Pygame stats screen ───────────────────────────────────────────────────────
def show_stats_screen(screen, rows: list, player_clan: str,
                      result: str, clock, FPS: int = 60):

    import pygame
    from ui import (FONT_SM, FONT_MD, FONT_LG, FONT_TL,
                    GOLD_COLOR, WHITE, GRAY, RED, GREEN,
                    PANEL_BG, PANEL_LINE, ACCENT_RED, ORANGE, BLUE)



    # max_turn from TURN_SNAPSHOT of any clan, or from any row
    snap_turns = [r["turn"] for r in rows if r["event_type"] == "TURN_SNAPSHOT"]
    max_turn   = max(snap_turns) if snap_turns else max((r["turn"] for r in rows), default=20)
    summary  = _summarise(rows, player_clan)
    pt       = _per_turn(rows, player_clan, max_turn)

    # Clan colour map (pulled from any available source)
    clan_colors = {
        "Tada": (220, 60, 60),
        "Date": (70, 110, 210),
        "Nori": (80, 180, 80),
        "Abe":  (180, 80, 220),
    }

    page     = 0   # 0=table, 1-6=graphs+raw
    PAGES    = 7
    running  = True

    while running:
        sw, sh = screen.get_size()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_ESCAPE, pygame.K_q):
                    running = False
                elif event.key in (pygame.K_RIGHT, pygame.K_d):
                    page = (page + 1) % PAGES
                elif event.key in (pygame.K_LEFT, pygame.K_a):
                    page = (page - 1) % PAGES
            if event.type == pygame.MOUSEWHEEL and page == 6:
                if hasattr(_draw_raw_data, '_scroll'):
                    snap_turns2 = [r["turn"] for r in rows if r["event_type"] == "TURN_SNAPSHOT"]
                    mt2 = max(snap_turns2) if snap_turns2 else 20
                    vis = (content_h - 56) // 20
                    mx_sc = max(0, len(rows) - vis)
                    _draw_raw_data._scroll = max(0, min(_draw_raw_data._scroll - event.y, mx_sc))
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Navigation arrows
                if event.pos[0] < 60:
                    page = (page - 1) % PAGES
                    if hasattr(_draw_raw_data, '_scroll'): _draw_raw_data._scroll = 0
                elif event.pos[0] > sw - 60:
                    page = (page + 1) % PAGES
                    if hasattr(_draw_raw_data, '_scroll'): _draw_raw_data._scroll = 0

        screen.fill(PANEL_BG)

        # ── Header bar ────────────────────────────────────────────────────────
        pygame.draw.rect(screen, (18, 15, 12), (0, 0, sw, 56))
        pygame.draw.line(screen, PANEL_LINE, (0, 56), (sw, 56), 1)
        pygame.draw.rect(screen, ACCENT_RED, (0, 0, sw, 4))

        res_col = GOLD_COLOR if result == "Win" else RED
        title   = FONT_LG.render(f"All Out War : Shogun  —  {result.upper()}  —  {player_clan} Clan",
                                 True, res_col)
        screen.blit(title, title.get_rect(centerx=sw//2, centery=28))

        # Page tabs
        tabs = ["Summary", "Recruited/Lost", "Damage", "Territories", "Power Growth", "Time/Turn", "Raw Data"]
        tab_w = sw // PAGES
        for i, tab in enumerate(tabs):
            tx = i * tab_w
            bg = (35, 30, 24) if i == page else (20, 17, 14)
            pygame.draw.rect(screen, bg, (tx, 56, tab_w, 30))
            if i == page:
                pygame.draw.rect(screen, PANEL_LINE, (tx, 56, tab_w, 30), 1)
                pygame.draw.rect(screen, GOLD_COLOR, (tx, 82, tab_w, 2))
            tc = GOLD_COLOR if i == page else GRAY
            tl = FONT_SM.render(tab, True, tc)
            screen.blit(tl, tl.get_rect(centerx=tx+tab_w//2, centery=71))

        # Navigation hint
        hint = FONT_SM.render("← → to navigate   ESC to close", True, (70, 65, 55))
        screen.blit(hint, (sw - hint.get_width() - 16, sh - 22))

        content_y = 96
        content_h = sh - content_y - 30

        if page == 0:
            territory_helper(pt["territories"], max_turn)
            _draw_summary_table(screen, summary, player_clan, result,
                                sw, content_y, content_h,
                                FONT_SM, FONT_MD, FONT_LG, FONT_TL,
                                GOLD_COLOR, WHITE, GRAY, GREEN, RED, PANEL_LINE)
            

        elif page == 1:
            _draw_stacked_bar(screen, pt["recruited"], pt["lost"], max_turn,
                              "Soldiers Recruited vs Soldiers Lost",
                              GREEN, RED, sw, content_y, content_h,
                              FONT_SM, FONT_MD, WHITE, GRAY, PANEL_LINE)
        elif page == 2:
            _draw_scatter(screen, pt["dmg_dealt"], pt["dmg_taken"], max_turn,
                          "Damage Dealt vs Damage Taken  (Player vs All Enemies)",
                          GOLD_COLOR, RED, sw, content_y, content_h,
                          FONT_SM, FONT_MD, WHITE, GRAY, PANEL_LINE)
        elif page == 3:
            _draw_territory_chart(screen, pt["territories"], max_turn,
                                  "Total Territories Held Per Turn",
                                  GREEN, ORANGE, sw, content_y, content_h,
                                  FONT_SM, FONT_MD, WHITE, GRAY, PANEL_LINE)
        elif page == 4:
            _draw_cumulative_line(screen, pt["clan_power"], max_turn,
                                  "Overall Military Power Growth",
                                  clan_colors, sw, content_y, content_h,
                                  FONT_SM, FONT_MD, WHITE, GRAY, PANEL_LINE)
        elif page == 5:
            _draw_line_chart(screen, pt["time_per"], max_turn,
                             "Time Spent Per Turn (seconds)",
                             ORANGE, sw, content_y, content_h,
                             FONT_SM, FONT_MD, WHITE, GRAY, PANEL_LINE)
        elif page == 6:
            _draw_raw_data(screen, rows, sw, content_y, content_h,
                           FONT_SM, FONT_MD, WHITE, GRAY, GOLD_COLOR, PANEL_LINE, PANEL_BG)

        pygame.display.flip()
        clock.tick(FPS)


# ── Graph helpers ─────────────────────────────────────────────────────────────

def _chart_area(sw, content_y, content_h):
    """Return (left, top, width, height) for chart drawing area."""
    pad_l, pad_r, pad_t, pad_b = 80, 40, 20, 50
    return (pad_l, content_y + pad_t,
            sw - pad_l - pad_r,
            content_h - pad_t - pad_b)


def _draw_axes(surf, cx, cy, cw, ch, max_x, max_y,
               font, WHITE, GRAY, PANEL_LINE, x_label="Turn", y_label=""):
    import pygame
    # Axes lines
    pygame.draw.line(surf, PANEL_LINE, (cx, cy), (cx, cy+ch), 2)
    pygame.draw.line(surf, PANEL_LINE, (cx, cy+ch), (cx+cw, cy+ch), 2)
    # X ticks
    steps = min(max_x, 20)
    for i in range(0, steps+1):
        t = i * max_x // steps
        x = cx + int(t / max(max_x,1) * cw)
        pygame.draw.line(surf, (60,55,45), (x, cy), (x, cy+ch), 1)
        lbl = font.render(str(t), True, GRAY)
        surf.blit(lbl, lbl.get_rect(centerx=x, y=cy+ch+4))
    # Y ticks
    for i in range(5):
        y = cy + ch - int(i/4 * ch)
        val = int(i/4 * max_y)
        pygame.draw.line(surf, (60,55,45), (cx, y), (cx+cw, y), 1)
        lbl = font.render(str(val), True, GRAY)
        surf.blit(lbl, lbl.get_rect(right=cx-4, centery=y))
    # Labels
    xl = font.render(x_label, True, GRAY)
    surf.blit(xl, xl.get_rect(centerx=cx+cw//2, y=cy+ch+20))


def _draw_summary_table(surf, s, player_clan, result,
                         sw, cy, ch, fs, fm, fl, ft,
                         GOLD, WHITE, GRAY, GREEN, RED, LINE):
    import pygame
    global gain,lost
    metrics = [
        ("Total Turns",          str(s["total_turns"])),
        ("Soldiers Recruited",   f"{s['recruited']:,}"),
        ("Soldiers Lost",        f"{s['lost']:,}"),
        ("Provinces Conquered",  str(gain)),
        ("Provinces Lost",       str(lost)),
        ("Total Damage Dealt",   f"{s['damage_dealt']:,}  (enemy units killed)"),
        ("Total Damage Taken",   f"{s['damage_taken']:,}  (own units lost)"),
        ("Game Result",          result),
    ]
    TW = min(700, sw - 80)
    tx = sw//2 - TW//2
    ty = cy + 20
    ROW_H = 38
    C1 = int(TW * 0.62)
    C2 = TW - C1

    # Header
    pygame.draw.rect(surf, (35,30,24), (tx, ty, TW, ROW_H), border_radius=4)
    pygame.draw.rect(surf, LINE, (tx, ty, TW, ROW_H), 1, border_radius=4)
    surf.blit(fm.render("Metric", True, GOLD), (tx+16, ty+10))
    surf.blit(fm.render("Value",  True, GOLD), (tx+C1+16, ty+10))
    ty += ROW_H

    for i, (metric, value) in enumerate(metrics):
        bg = (28,24,20) if i%2==0 else (22,19,16)
        pygame.draw.rect(surf, bg, (tx, ty, TW, ROW_H))
        pygame.draw.line(surf, (45,40,34), (tx, ty+ROW_H-1), (tx+TW, ty+ROW_H-1))
        pygame.draw.line(surf, (45,40,34), (tx+C1, ty), (tx+C1, ty+ROW_H))
        vc = (GOLD if metric=="Game Result" and value=="Win"
              else (RED  if metric=="Game Result"
                    else WHITE))
        surf.blit(fs.render(metric, True, GRAY), (tx+16, ty+11))
        # Clip value text to fit in the right column — try fm first, fall back to fs
        val_surf = fm.render(value, True, vc)
        max_val_w = TW - C1 - 20
        if val_surf.get_width() > max_val_w:
            val_surf = fs.render(value, True, vc)
        if val_surf.get_width() > max_val_w:
            # Truncate text to fit
            for clip in range(len(value), 0, -1):
                val_surf = fs.render(value[:clip] + "…", True, vc)
                if val_surf.get_width() <= max_val_w:
                    break
        surf.blit(val_surf, (tx+C1+10, ty + ROW_H//2 - val_surf.get_height()//2))
        ty += ROW_H

    pygame.draw.rect(surf, LINE, (tx, cy+20, TW, (len(metrics)+1)*ROW_H), 1, border_radius=4)

    note = fs.render(f"Clan: {player_clan}  |  ← → to view graphs", True, (80,75,65))
    surf.blit(note, note.get_rect(centerx=sw//2, y=ty+16))


def _draw_stacked_bar(surf, series_a, series_b, max_t,
                       title, col_a, col_b,
                       sw, cy, ch, fs, fm, WHITE, GRAY, LINE):
    import pygame
    cx, gy, cw, gh = _chart_area(sw, cy, ch)
    max_val = max(max(series_a+[1]), max(series_b+[1]))
    # Title
    surf.blit(fm.render(title, True, WHITE), (cx, cy+2))
    _draw_axes(surf, cx, gy, cw, gh, max_t, max_val, fs, WHITE, GRAY, LINE)
    # Bars
    bar_w = max(2, cw // max(max_t, 1) - 2)
    for t in range(1, max_t+1):
        x = cx + int((t-1)/max(max_t,1)*cw)
        ha = int(series_a[t] / max(max_val,1) * gh) if t < len(series_a) else 0
        hb = int(series_b[t] / max(max_val,1) * gh) if t < len(series_b) else 0
        if ha: pygame.draw.rect(surf, col_a, (x, gy+gh-ha, bar_w, ha))
        if hb: pygame.draw.rect(surf, col_b, (x, gy+gh-ha-hb, bar_w, hb))
    # Legend
    pygame.draw.rect(surf, col_a, (cx, gy+gh+36, 14, 10))
    surf.blit(fs.render("Recruited", True, GRAY), (cx+18, gy+gh+34))
    pygame.draw.rect(surf, col_b, (cx+110, gy+gh+36, 14, 10))
    surf.blit(fs.render("Lost", True, GRAY), (cx+128, gy+gh+34))


def _draw_scatter(surf, series_a, series_b, max_t,
                  title, col_a, col_b,
                  sw, cy, ch, fs, fm, WHITE, GRAY, LINE):
    import pygame
    cx, gy, cw, gh = _chart_area(sw, cy, ch)
    max_val = max(max(series_a+[1]), max(series_b+[1]))
    surf.blit(fm.render(title, True, WHITE), (cx, cy+2))
    _draw_axes(surf, cx, gy, cw, gh, max_t, max_val, fs, WHITE, GRAY, LINE)
    for t in range(1, max_t+1):
        x = cx + int((t-0.5)/max(max_t,1)*cw)
        if t < len(series_a) and series_a[t]:
            y = gy + gh - int(series_a[t]/max(max_val,1)*gh)
            pygame.draw.circle(surf, col_a, (x, y), 5)
        if t < len(series_b) and series_b[t]:
            y = gy + gh - int(series_b[t]/max(max_val,1)*gh)
            pygame.draw.circle(surf, col_b, (x, y), 5)
    pygame.draw.rect(surf, col_a, (cx, gy+gh+36, 10, 10))
    surf.blit(fs.render("Player Dealt", True, GRAY), (cx+14, gy+gh+34))
    pygame.draw.rect(surf, col_b, (cx+120, gy+gh+36, 10, 10))
    surf.blit(fs.render("Player Taken", True, GRAY), (cx+134, gy+gh+34))



def _draw_territory_chart(surf, territories, max_t,
                          title, col_line, col_avg,
                          sw, cy, ch, fs, fm, WHITE, GRAY, LINE):
    cx, gy, cw, gh = _chart_area(sw, cy, ch)

    active  = [territories[t] for t in range(1, max_t + 1) if territories[t] > 0]
    max_val = max(max(territories[1:max_t+1] + [1]), 1)
    avg_val = (sum(active) / len(active)) if active else 0

    # Stats for subtitle
    gains  = sum(1 for t in range(2, max_t+1) if territories[t] > territories[t-1] > 0)
    losses = sum(1 for t in range(2, max_t+1) if 0 < territories[t] < territories[t-1])
    peak   = max(active) if active else 0

    # Colours — teal/amber/crimson palette
    COL_NEUTRAL = (56, 189, 180)    
    COL_GAIN    = (255, 185,  30)   
    COL_LOSS    = (210,  50,  60)   
    COL_AVG     = (200, 160,  60)   

    surf.blit(fm.render(title, True, WHITE), (cx, cy + 2))

    # Subtitle
    sub_colors = {
        f"Peak: {peak}":      (200, 195, 175),
        f"Gained: +{gains}":  COL_GAIN,
        f"Lost: -{losses}":   COL_LOSS,
        f"Avg: {avg_val:.1f}": COL_AVG,
    }
    sub_x = cx
    for part, color in sub_colors.items():
        lbl = fs.render(part, True, color)
        if sub_x + lbl.get_width() < cx + cw:
            surf.blit(lbl, (sub_x, cy + 22))
            sub_x += lbl.get_width() + 22

    # ── Axes (X unchanged, Y redrawn with fine integer ticks) ─────────────────
    pygame.draw.line(surf, LINE, (cx, gy),      (cx, gy + gh), 2)
    pygame.draw.line(surf, LINE, (cx, gy + gh), (cx + cw, gy + gh), 2)

    # X ticks — same as _draw_axes
    steps = min(max_t, 20)
    for i in range(0, steps + 1):
        t  = i * max_t // steps
        x  = cx + int(t / max(max_t, 1) * cw)
        pygame.draw.line(surf, (60, 55, 45), (x, gy), (x, gy + gh), 1)
        lbl = fs.render(str(t), True, GRAY)
        surf.blit(lbl, lbl.get_rect(centerx=x, y=gy + gh + 4))
    xl = fs.render("Turn", True, GRAY)
    surf.blit(xl, xl.get_rect(centerx=cx + cw // 2, y=gy + gh + 20))

    # Y ticks — one tick per integer territory value for full detail
    for v in range(0, max_val + 1):
        y   = gy + gh - int(v / max_val * gh)
        # Major tick every 1 unit; faint grid line
        grid_col = (50, 46, 38) if v % 2 == 0 else (38, 35, 28)
        pygame.draw.line(surf, grid_col, (cx, y), (cx + cw, y), 1)
        # Tick mark on Y axis
        pygame.draw.line(surf, GRAY, (cx - 5, y), (cx, y), 1)
        lbl = fs.render(str(v), True, GRAY)
        surf.blit(lbl, lbl.get_rect(right=cx - 7, centery=y))

    # ── Bars ──────────────────────────────────────────────────────────────────
    bar_w = max(2, cw // max(max_t, 1) - 1)

    for t in range(1, max_t + 1):
        val = territories[t]
        if val <= 0:
            continue
        x   = cx + int((t - 1) / max(max_t, 1) * cw)
        bh  = int(val / max_val * gh)
        y   = gy + gh - bh

        prev = territories[t - 1] if t > 1 else val
        if val > prev:
            bar_col = COL_GAIN
        elif val < prev:
            bar_col = COL_LOSS
        else:
            bar_col = COL_NEUTRAL

        pygame.draw.rect(surf, bar_col, (x, y, bar_w, bh))
        # One-pixel dark top edge for bar separation
        pygame.draw.line(surf, (15, 13, 10), (x, y), (x + bar_w, y), 1)

    # ── Average dashed line ───────────────────────────────────────────────────
    if avg_val > 0:
        avg_y = gy + gh - int(avg_val / max_val * gh)
        x, drawing = cx, True
        while x < cx + cw:
            x2 = min(x + (10 if drawing else 6), cx + cw)
            if drawing:
                pygame.draw.line(surf, COL_AVG, (x, avg_y), (x2, avg_y), 2)
            x, drawing = x2, not drawing
        lbl = fs.render(f"Avg {avg_val:.1f}", True, COL_AVG)
        lbl_x = min(cx + cw - lbl.get_width() - 4, cx + cw + 4)
        surf.blit(lbl, (lbl_x, avg_y - 9))

    # ── Legend ────────────────────────────────────────────────────────────────
    ly = gy + gh + 34
    items = [
        (COL_NEUTRAL, True,  "Held"),
        (COL_GAIN,    True,  "Gain"),
        (COL_LOSS,    True,  "Loss"),
        (COL_AVG,     False, "Average"),
    ]
    lx = cx
    for col, filled, label in items:
        if filled:
            pygame.draw.rect(surf, col, (lx, ly + 2, 12, 10))
        else:
            pygame.draw.line(surf, col, (lx, ly + 7), (lx + 18, ly + 7), 2)
            lx += 4
        surf.blit(fs.render(label, True, GRAY), (lx + 16, ly))
        lx += fs.size(label)[0] + 34


def _draw_cumulative_line(surf, clan_power, max_t,
                           title, clan_colors,
                           sw, cy, ch, fs, fm, WHITE, GRAY, LINE):
    import pygame
    cx, gy, cw, gh = _chart_area(sw, cy, ch)
    all_vals = [v for series in clan_power.values() for v in series if v > 0]
    max_val  = max(all_vals + [1])
    surf.blit(fm.render(title, True, WHITE), (cx, cy+2))
    _draw_axes(surf, cx, gy, cw, gh, max_t, max_val, fs, WHITE, GRAY, LINE)
    lx = cx
    for ci, (clan, series) in enumerate(clan_power.items()):
        col = clan_colors.get(clan, (180, 180, 180))
        pts = []
        # Build cumulative max (power never goes backwards for display)
        cum = 0
        for t in range(1, min(max_t+1, len(series))):
            cum = max(cum, series[t])
            x = cx + int((t-0.5)/max(max_t,1)*cw)
            y = gy + gh - int(cum/max(max_val,1)*gh)
            pts.append((x, y))
        if len(pts) > 1:
            pygame.draw.lines(surf, col, False, pts, 2)
        # Legend
        pygame.draw.rect(surf, col, (lx, gy+gh+36, 14, 10))
        surf.blit(fs.render(clan, True, GRAY), (lx+18, gy+gh+34))
        lx += 90


def _draw_line_chart(surf, series, max_t,
                     title, col,
                     sw, cy, ch, fs, fm, WHITE, GRAY, LINE):
    import pygame
    cx, gy, cw, gh = _chart_area(sw, cy, ch)
    max_val = max(max(series+[1]), 1)
    surf.blit(fm.render(title, True, WHITE), (cx, cy+2))
    _draw_axes(surf, cx, gy, cw, gh, max_t, max_val, fs, WHITE, GRAY, LINE,
               y_label="Seconds")
    pts = []
    for t in range(1, min(max_t+1, len(series))):
        if series[t] > 0:
            x = cx + int((t-0.5)/max(max_t,1)*cw)
            y = gy + gh - int(series[t]/max(max_val,1)*gh)
            pts.append((x, y))
            pygame.draw.circle(surf, col, (x, y), 3)
    if len(pts) > 1:
        pygame.draw.lines(surf, col, False, pts, 2)


# ── Raw data viewer ─────────────────────────────────────────────────────────────

def _draw_raw_data(surf, rows, sw, cy, ch, fs, fm, WHITE, GRAY, GOLD, LINE, BG):
    import pygame

    COLS = ["turn", "time_elapsed", "event_type", "clan",
            "province", "units", "provinces", "damage", "units_lost"]
    COL_W = [45, 70, 110, 70, 80, 60, 65, 70, 70]   # pixel widths per column
    ROW_H  = 20
    HDR_H  = 26
    PAD_L  = 20
    PAD_T  = 30

    total_w = sum(COL_W) + PAD_L * 2
    start_x = max(PAD_L, sw // 2 - total_w // 2)

    # Scroll state stored on the surface's parent — use a mutable list trick
    if not hasattr(_draw_raw_data, '_scroll'):
        _draw_raw_data._scroll = 0

    visible_rows = (ch - HDR_H - PAD_T) // ROW_H
    max_scroll   = max(0, len(rows) - visible_rows)

    # Handle scroll events THIS frame
    keys = pygame.key.get_pressed()
    if keys[pygame.K_DOWN]: _draw_raw_data._scroll = min(_draw_raw_data._scroll + 1, max_scroll)
    if keys[pygame.K_UP]:   _draw_raw_data._scroll = max(_draw_raw_data._scroll - 1, 0)

    scroll = _draw_raw_data._scroll

    # Title
    surf.blit(fm.render(f"Raw Event Log  ({len(rows)} rows total)  ↑↓ to scroll", True, WHITE),
              (start_x, cy + 8))

    # Header row
    hx = start_x
    hy = cy + PAD_T
    pygame.draw.rect(surf, (35, 30, 24), (start_x, hy, sum(COL_W), HDR_H))
    pygame.draw.rect(surf, LINE,         (start_x, hy, sum(COL_W), HDR_H), 1)
    for col, w in zip(COLS, COL_W):
        lbl = fs.render(col, True, GOLD)
        surf.blit(lbl, (hx + 4, hy + 5))
        pygame.draw.line(surf, (55, 50, 40), (hx + w, hy), (hx + w, hy + HDR_H))
        hx += w

    # Data rows
    event_colors = {
        "RECRUIT":      (80,  185,  80),
        "BATTLE_WIN":   (80,  150, 220),
        "BATTLE_LOSS":  (220,  70,  70),
        "SIEGE_WIN":    (100, 220, 100),
        "SIEGE_LOSS":   (220, 100, 100),
        "AMBUSH_WIN":   (180, 130, 220),
        "AMBUSH_LOSS":  (220, 100, 180),
        "REBELLION":    (255, 140,  30),
        "TURN_SNAPSHOT":(120, 110,  90),
    }

    for i, row in enumerate(rows[scroll: scroll + visible_rows]):
        ry = cy + PAD_T + HDR_H + i * ROW_H
        bg = (28, 24, 20) if i % 2 == 0 else (22, 19, 16)
        pygame.draw.rect(surf, bg, (start_x, ry, sum(COL_W), ROW_H))

        rx = start_x
        for col, w in zip(COLS, COL_W):
            val  = str(row.get(col, ""))
            col_color = event_colors.get(val, WHITE) if col == "event_type" else WHITE
            if col == "clan":
                cmap = {"Tada":(220,60,60),"Date":(70,110,210),"Nori":(80,180,80),"Abe":(180,80,220)}
                col_color = cmap.get(val, GRAY)
            cell = fs.render(val[:12], True, col_color)
            surf.blit(cell, (rx + 3, ry + 3))
            pygame.draw.line(surf, (45, 40, 35), (rx + w, ry), (rx + w, ry + ROW_H))
            rx += w

        pygame.draw.line(surf, (38, 34, 30), (start_x, ry + ROW_H - 1), (start_x + sum(COL_W), ry + ROW_H - 1))

    # Outer border
    table_h = HDR_H + min(visible_rows, len(rows)) * ROW_H
    pygame.draw.rect(surf, LINE, (start_x, cy + PAD_T, sum(COL_W), table_h), 1)

    # Scroll indicator
    if len(rows) > visible_rows:
        scroll_pct = scroll / max(max_scroll, 1)
        bar_h      = int(ch * visible_rows / len(rows))
        bar_y      = int(cy + PAD_T + scroll_pct * (ch - bar_h))
        pygame.draw.rect(surf, (60, 55, 45), (start_x + sum(COL_W) + 6, cy + PAD_T, 6, ch))
        pygame.draw.rect(surf, GOLD,         (start_x + sum(COL_W) + 6, bar_y, 6, bar_h), border_radius=3)
        info = fs.render(f"Rows {scroll+1}–{min(scroll+visible_rows, len(rows))} / {len(rows)}", True, GRAY)
        surf.blit(info, (start_x + sum(COL_W) + 16, cy + PAD_T + 2))


