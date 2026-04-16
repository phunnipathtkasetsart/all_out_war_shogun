"""
game.py  –  Main entry point. Run this file to start the game.

    python game.py

Requires: pygame  (pip install pygame)

Input modes (state machine):
  NORMAL        – default, click army/province to select
  MARCH         – army selected, waiting for player to click a destination
  ATTACK_TARGET – waiting for player to click an enemy ARMY to attack
  SIEGE_TARGET  – waiting for player to click an enemy PROVINCE to siege
"""
import pygame
import sys
import os
from enum import Enum, auto

from game_state import GameState
from clans import make_clans
from ui import GameRenderer, draw_clan_select, init_fonts, PANEL_LINE, GOLD_COLOR, WHITE
from stats import show_stats_screen, StatsLogger
from combat import resolve_battle, resolve_siege
from map import MapArmy, TERRAIN

SCREEN_W = 1280
SCREEN_H = 720
FPS = 60


class InputMode(Enum):
    NORMAL        = auto()
    MARCH         = auto()
    ATTACK_TARGET = auto()
    SIEGE_TARGET  = auto()



def _load_saved_game(screen, clock, fps):
    """
    Show the in-game save-file list picker, load the chosen CSV,
    then show the stats screen.  No external OS file dialog is used.
    """
    save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saves")
    saves    = StatsLogger.list_saved_games(save_dir)
    if not saves:
        _draw_no_saves_notice(screen, clock, fps)
        return

    path = _pick_save_in_game(screen, clock, fps, saves)
    if not path or not os.path.exists(path):
        return

    rows = StatsLogger.load(path)
    if not rows:
        return

    # Detect player clan from event types logged only for the player
    def _detect_player_clan(rows):
        for r in rows:
            if r["event_type"] == "RECRUIT" and r["clan"]:
                return r["clan"]
        for r in rows:
            if r["event_type"] == "REBELLION" and r["clan"]:
                return r["clan"]
        for r in rows:
            if r["event_type"] in ("SIEGE_WIN", "SIEGE_LOSS", "BATTLE_WIN",
                                    "BATTLE_LOSS", "AMBUSH_WIN", "AMBUSH_LOSS"):
                return r["clan"]
        return rows[0]["clan"] if rows else "Unknown"

    player_clan = _detect_player_clan(rows)

    # Only show clans that have at least one player-action event.
    # This filters out AI-only clans that appear solely in TURN_SNAPSHOT rows.
    active_event_types = {"RECRUIT", "REBELLION", "SIEGE_WIN", "SIEGE_LOSS",
                          "BATTLE_WIN", "BATTLE_LOSS", "AMBUSH_WIN", "AMBUSH_LOSS"}
    detected_clans = sorted({r["clan"] for r in rows
                              if r["clan"] and r["event_type"] in active_event_types})

    # Safety fallback: if no action events exist, use snapshot clans
    if not detected_clans:
        detected_clans = sorted({r["clan"] for r in rows
                                  if r["clan"] and r["event_type"] == "TURN_SNAPSHOT"})
    if player_clan not in detected_clans and detected_clans:
        player_clan = detected_clans[0]

    # Let the user confirm / change only among detected (player-action) clans
    if len(detected_clans) > 1:
        chosen = _pick_player_clan(screen, clock, fps, detected_clans, player_clan)
        if chosen:
            player_clan = chosen

    show_stats_screen(screen, rows, player_clan, "Loaded", clock, fps)


def _pick_player_clan(screen, clock, fps, clans, default_clan):
    """
    Show a small overlay letting the user pick which clan is theirs
    when loading a saved game. Returns chosen clan name or None to keep default.
    """
    from ui import FONT_SM, FONT_MD, FONT_LG, PANEL_BG, PANEL_LINE, WHITE, GOLD_COLOR, GRAY, HIGHLIGHT, ACCENT_RED
    selected = None
    ROW_H    = 44

    while selected is None:
        sw, sh = screen.get_size()
        bw     = 420
        total_h = 80 + len(clans) * ROW_H + 60
        bx     = sw//2 - bw//2
        by     = sh//2 - total_h//2

        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                return default_clan   # keep detected clan
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mx, my = ev.pos
                for i, clan in enumerate(clans):
                    ry = by + 60 + i * ROW_H
                    row_r = pygame.Rect(bx + 10, ry, bw - 20, ROW_H - 4)
                    if row_r.collidepoint(mx, my):
                        selected = clan
                        break

        # Overlay
        ov = pygame.Surface((sw, sh), pygame.SRCALPHA)
        ov.fill((0, 0, 0, 170))
        screen.blit(ov, (0, 0))

        # Box
        pygame.draw.rect(screen, (22, 18, 14), (bx, by, bw, total_h), border_radius=10)
        pygame.draw.rect(screen, PANEL_LINE,   (bx, by, bw, total_h), 2, border_radius=10)
        pygame.draw.rect(screen, ACCENT_RED,   (bx, by, bw, 5),       border_radius=10)

        t = FONT_LG.render("Select Your Clan", True, GOLD_COLOR)
        screen.blit(t, t.get_rect(centerx=sw//2, y=by+14))
        sub = FONT_SM.render("Which clan did you play?", True, GRAY)
        screen.blit(sub, sub.get_rect(centerx=sw//2, y=by+42))

        mx2, my2 = pygame.mouse.get_pos()
        CLAN_COLORS = {"Tada":(220,60,60),"Date":(70,110,210),"Nori":(80,180,80),"Abe":(180,80,220)}
        for i, clan in enumerate(clans):
            ry  = by + 60 + i * ROW_H
            row_r = pygame.Rect(bx + 10, ry, bw - 20, ROW_H - 4)
            hov = row_r.collidepoint(mx2, my2)
            is_default = clan == default_clan
            col = CLAN_COLORS.get(clan, (150, 150, 150))
            bg  = (50, 42, 30) if hov else ((35, 30, 22) if is_default else (25, 22, 18))
            pygame.draw.rect(screen, bg, row_r, border_radius=6)
            pygame.draw.rect(screen, col if (hov or is_default) else (55,50,42), row_r, 2, border_radius=6)
            # Colour dot
            pygame.draw.circle(screen, col, (row_r.x + 20, row_r.centery), 8)
            lbl = FONT_MD.render(clan + (" (detected)" if is_default else ""), True, GOLD_COLOR if hov else WHITE)
            screen.blit(lbl, lbl.get_rect(midleft=(row_r.x + 36, row_r.centery)))

        pygame.display.flip()
        clock.tick(fps)

    return selected


def _draw_no_saves_notice(screen, clock, fps):
    """Show a brief 'no saves found' message for 2 seconds."""
    from ui import FONT_LG, PANEL_BG, GOLD_COLOR
    end = pygame.time.get_ticks() + 2000
    while pygame.time.get_ticks() < end:
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.MOUSEBUTTONDOWN:
                return
        screen.fill(PANEL_BG)
        msg = FONT_LG.render("No saved games found in 'saves/' folder.", True, GOLD_COLOR)
        screen.blit(msg, msg.get_rect(center=(screen.get_width()//2, screen.get_height()//2)))
        pygame.display.flip()
        clock.tick(fps)


def _pick_save_in_game(screen, clock, fps, saves):
    """
    In-game scrollable list to pick a save file when tkinter is unavailable.
    Returns the selected path or None if cancelled.
    """
    from ui import FONT_SM, FONT_MD, FONT_LG, PANEL_BG, PANEL_LINE, WHITE, GOLD_COLOR, GRAY, HIGHLIGHT
    selected = None
    scroll   = 0
    ROW_H    = 36
    LIST_TOP = 130

    while selected is None:
        LIST_BOT = screen.get_height() - 80
        for ev in pygame.event.get():
            if ev.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if ev.type == pygame.KEYDOWN and ev.key == pygame.K_ESCAPE:
                return None
            if ev.type == pygame.MOUSEWHEEL:
                scroll = max(0, min(scroll - ev.y, max(0, len(saves) - (LIST_BOT - LIST_TOP) // ROW_H)))
            if ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                mx, my = ev.pos
                for i, fpath in enumerate(saves[scroll:]):
                    ry = LIST_TOP + i * ROW_H
                    if ry + ROW_H > LIST_BOT:
                        break
                    row_rect = pygame.Rect(screen.get_width()//2 - 300, ry, 600, ROW_H - 2)
                    if row_rect.collidepoint(mx, my):
                        selected = fpath
                        break
                sw2 = screen.get_width()
                cancel_rect = pygame.Rect(sw2//2 - 80, screen.get_height() - 65, 160, 38)
                if cancel_rect.collidepoint(mx, my):
                    return None

        sw, sh = screen.get_size()
        screen.fill(PANEL_BG)
        t = FONT_LG.render("Select a Saved Game", True, GOLD_COLOR)
        screen.blit(t, t.get_rect(centerx=sw//2, y=50))
        pygame.draw.line(screen, PANEL_LINE, (sw//2 - 200, 90), (sw//2 + 200, 90), 1)
        sub = FONT_SM.render("Click to load  |  ESC to cancel  |  Scroll to browse", True, GRAY)
        screen.blit(sub, sub.get_rect(centerx=sw//2, y=100))

        mx, my = pygame.mouse.get_pos()
        LIST_BOT = sh - 80
        for i, fpath in enumerate(saves[scroll:]):
            ry = LIST_TOP + i * ROW_H
            if ry + ROW_H > LIST_BOT:
                break
            row_rect = pygame.Rect(sw//2 - 300, ry, 600, ROW_H - 2)
            hov = row_rect.collidepoint(mx, my)
            pygame.draw.rect(screen, (44, 38, 28) if hov else (28, 24, 18), row_rect, border_radius=4)
            pygame.draw.rect(screen, PANEL_LINE if hov else (55, 50, 40), row_rect, 1, border_radius=4)
            fname = os.path.basename(fpath)
            lbl = FONT_MD.render(fname, True, HIGHLIGHT if hov else WHITE)
            screen.blit(lbl, lbl.get_rect(midleft=(row_rect.x + 12, row_rect.centery)))

        cancel_rect = pygame.Rect(sw//2 - 80, sh - 65, 160, 38)
        chov = cancel_rect.collidepoint(mx, my)
        pygame.draw.rect(screen, (80, 30, 30) if chov else (55, 25, 25), cancel_rect, border_radius=6)
        pygame.draw.rect(screen, PANEL_LINE, cancel_rect, 1, border_radius=6)
        clbl = FONT_MD.render("Cancel", True, WHITE)
        screen.blit(clbl, clbl.get_rect(center=cancel_rect.center))

        pygame.display.flip()
        clock.tick(fps)

    return selected


def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H), pygame.RESIZABLE)
    pygame.display.set_caption("All Out War : Shogun")
    clock = pygame.time.Clock()
    init_fonts()

    # ── Clan select screen ────────────────────────────────────────────────────
    clans_preview = make_clans()
    hovered_clan  = None
    player_clan_name = None
    clan_buttons  = {}
    load_btn_rect = None

    while player_clan_name is None:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEMOTION:
                hovered_clan = None
                for name, rect in clan_buttons.items():
                    if rect.collidepoint(event.pos):
                        hovered_clan = name
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # Load saved game button
                if load_btn_rect and load_btn_rect.collidepoint(event.pos):
                    _load_saved_game(screen, clock, FPS)
                    continue
                for name, rect in clan_buttons.items():
                    if rect.collidepoint(event.pos):
                        player_clan_name = name

        clan_buttons, load_btn_rect = draw_clan_select(screen, clans_preview, hovered_clan or "")
        pygame.display.flip()
        clock.tick(FPS)

    # ── Init game ─────────────────────────────────────────────────────────────
    gs       = GameState(player_clan_name)
    renderer = GameRenderer(screen, gs)
    renderer._gs_ref = gs   # for fade overlay turn display
    mode     = InputMode.NORMAL
    gs.log(f"You lead the {player_clan_name} clan. Conquer Japan!")
    is_fullscreen = False

    # ── Main loop ─────────────────────────────────────────────────────────────
    running = True
    while running:
        clock.tick(FPS)

        sw, sh = screen.get_size()
        # Panel is always right 300px; map is everything left of it
        panel_x = sw - 300

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # F11 → toggle fullscreen
            if event.type == pygame.KEYDOWN and event.key == pygame.K_F9:
                # Debug: show stats screen immediately with current data
                show_stats_screen(screen, gs.stats.rows, gs.player_clan_name,
                                  "Debug", clock, FPS)

            if event.type == pygame.KEYDOWN and event.key == pygame.K_F11:
                is_fullscreen = not is_fullscreen
                if is_fullscreen:
                    screen = pygame.display.set_mode((0, 0), pygame.FULLSCREEN)
                else:
                    screen = pygame.display.set_mode((1280, 720), pygame.RESIZABLE)
                renderer.surface = screen
                init_fonts()

            # Window resized
            if event.type == pygame.VIDEORESIZE:
                screen = pygame.display.set_mode(
                    (max(event.w, 960), max(event.h, 600)), pygame.RESIZABLE)
                renderer.surface = screen

            # Middle/right mouse drag → pan map (consume before other handlers)
            if renderer.handle_camera(event):
                continue

            renderer.handle_slider(event)

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                pos = event.pos

                # Block ALL clicks during map fade transition
                if renderer.is_fading():
                    continue

                # Ambush popup: only intercept clicks ON the popup buttons
                if gs.pending_ambush and not gs.pending_ambush.resolved:
                    wr = getattr(gs, '_ambush_withdraw_rect', None)
                    fr = getattr(gs, '_ambush_fight_rect',    None)
                    if (wr and wr.collidepoint(pos)) or (fr and fr.collidepoint(pos)):
                        _handle_ambush_click(pos, gs)
                        continue   # ate the click on a popup button

                # Right panel = last 300px of screen
                if pos[0] >= panel_x:
                    mode = _handle_panel_click(event, gs, renderer, mode)
                    continue

                # Map area
                mode = _handle_map_click(pos, gs, renderer, mode)

        # Edge scroll when mouse near map border
        renderer.update_edge_scroll()

        # Advance map fade state machine
        renderer.advance_map_fade()

        renderer.set_mode_label(_mode_label(mode))
        renderer.draw()

        # Ambush notification drawn on top
        if gs.pending_ambush and not gs.pending_ambush.resolved:
            _draw_ambush_popup(screen, gs, renderer)

        # Disable Next Turn button while animating OR fading
        renderer.btn_next_turn.enabled = (not renderer.is_animating()
                                           and not renderer.is_fading())

        # Map area fade overlay (drawn OVER map, not over panel)
        renderer.draw_map_fade(screen)

        if gs.game_over:
            _draw_game_over(screen, gs)
            # First time: save CSV and show stats screen
            if not getattr(gs, '_stats_shown', False):
                gs._stats_shown = True
                gs.stats.save()
                result_str = "Win" if gs.winner == gs.player_clan_name else "Loss"
                show_stats_screen(screen, gs.stats.rows, gs.player_clan_name,
                                  result_str, clock, FPS)

        pygame.display.flip()

    pygame.quit()


# ── Map click handler ─────────────────────────────────────────────────────────

def _handle_map_click(pos, gs, renderer, mode):

    # MARCH: player clicks any reachable destination — full path queued
    if mode == InputMode.MARCH:
        dest = renderer.province_at(pos)
        if dest and dest in gs.highlighted_provinces and dest != gs.selected_army.province:
            army = gs.selected_army
            ok = army.set_march_destination(dest, lambda p: _can_pass(gs, p))
            if ok:
                turns = army.turns_to_arrive()
                gs.log(f"Marching to {dest} — {turns} turn(s) to arrive.")
            else:
                gs.log("No valid path to that destination.")
        else:
            gs.log("March cancelled.")
        gs.highlighted_provinces = []
        return InputMode.NORMAL

    # ATTACK_TARGET: click an enemy army
    if mode == InputMode.ATTACK_TARGET:
        clicked_army = renderer.army_at(pos)
        if clicked_army and clicked_army.owner != gs.player_clan_name:
            if clicked_army in gs.highlighted_armies:
                _execute_attack(gs, gs.selected_army, clicked_army)
            else:
                gs.log("That target is out of range.")
        else:
            gs.log("Attack cancelled.")
        gs.highlighted_armies    = []
        gs.highlighted_provinces = []
        return InputMode.NORMAL

    # SIEGE_TARGET: click enemy province → queue march there, siege fires on arrival
    if mode == InputMode.SIEGE_TARGET:
        prov = renderer.province_at(pos)
        if prov and prov in gs.highlighted_provinces:
            army = gs.selected_army
            # Queue march toward the target province (adjacent or further)
            ok = army.set_march_destination(
                prov, passable_fn=lambda p: _can_pass_siege(gs, p, prov))
            if ok:
                army.siege_target = prov
                turns = army.turns_to_arrive()
                gs.log(f"Marching to siege {prov} — arrives in {turns} turn(s). "
                       f"Siege will resolve automatically on arrival.")
            else:
                gs.log(f"No path to {prov}.")
        else:
            gs.log("Siege cancelled.")
        gs.highlighted_armies    = []
        gs.highlighted_provinces = []
        return InputMode.NORMAL

    # NORMAL: select army or province
    clicked_army = renderer.army_at(pos)
    if clicked_army:
        gs.selected_army     = clicked_army
        gs.selected_province = clicked_army.province
        gs.highlighted_provinces = []
        gs.highlighted_armies    = []
        label = "Your" if clicked_army.owner == gs.player_clan_name else clicked_army.owner
        gs.log(f"Selected {label} army at {clicked_army.province} ({clicked_army.total_units()} units)")
        return InputMode.NORMAL

    prov = renderer.province_at(pos)
    if prov:
        gs.selected_province     = prov
        gs.selected_army         = None
        gs.highlighted_provinces = []
        gs.highlighted_armies    = []
        city = gs.cities.get(prov)
        if city:
            renderer.tax_slider_value = city.tax_level
            gs.log(f"{prov} — {city.label()}, owner: {city.owner}, rage: {city.rage_level}")
        return InputMode.NORMAL

    return InputMode.NORMAL


# ── Panel button handler ──────────────────────────────────────────────────────

def _handle_panel_click(event, gs, renderer, mode):

    if renderer.btn_next_turn.is_clicked(event):
        if not renderer.is_fading():
            renderer.begin_turn_animation()
            gs.end_turn()
            renderer.commit_turn_animation()
            gs.highlighted_provinces = []
            gs.highlighted_armies    = []
            gs.selected_army         = None
            renderer.start_banner()   # show "Turn X — Processing" banner
        return InputMode.NORMAL

    if renderer.btn_recruit.is_clicked(event):
        city = gs.cities.get(gs.selected_province)
        if city and city.owner == gs.player_clan_name:
            clan = gs.player_clan()
            if not city.can_queue_recruit():
                gs.log(f"Recruit queue full ({city.MAX_QUEUE_SIZE} max) or upgrade in progress.")
            elif city.queue_recruit(clan):
                turns = city.RECRUIT_TURNS
                gs.log(f"Recruiting {clan.default_name} at {gs.selected_province} "
                       f"— ready in {turns} turns. "
                       f"({len(city.recruit_queue)}/{city.MAX_QUEUE_SIZE} queued)")
            else:
                gs.log(f"Not enough gold to recruit! "
                       f"Need {(clan.default_unit + city._config()['soldier_bonus']) * 10}G")
        return mode

    if renderer.btn_upgrade.is_clicked(event):
        city = gs.cities.get(gs.selected_province)
        if city and city.owner == gs.player_clan_name:
            if not city.can_queue_upgrade():
                if city.upgrade_turns_left > 0:
                    gs.log(f"Upgrade already in progress — {city.upgrade_turns_left} turn(s) left.")
                elif city.city_level >= 5:
                    gs.log("City is already at max level (Citadel).")
                else:
                    gs.log("Cannot upgrade while soldiers are being recruited.")
            elif city.queue_upgrade(gs.player_clan()):
                gs.log(f"Upgrading {gs.selected_province} to "
                       f"{city.CITY_LEVEL_CONFIG[city.city_level + 1]['label'] if city.city_level < 5 else '?'}"
                       f" — ready in {city.UPGRADE_TURNS} turns.")
            else:
                from city import CITY_LEVEL_CONFIG
                cost = CITY_LEVEL_CONFIG[city.city_level]["upgrade_cost"]
                gs.log(f"Not enough gold to upgrade! Need {cost}G")
        return mode

    # MARCH → highlight all passable provinces as destination options
    if renderer.btn_march.is_clicked(event):
        army = gs.selected_army
        if army and army.owner == gs.player_clan_name:
            if army.is_marching():
                was_siege = army.siege_target
                army.cancel_march()
                army.siege_target = None
                gs.highlighted_provinces = []
                if was_siege:
                    gs.log(f"Siege march to {was_siege} cancelled.")
                else:
                    gs.log("March cancelled.")
                return mode
            # Show all provinces the army can potentially reach (BFS, no enemy blocking)
            from map import bfs_path, PROVINCE_POSITIONS
            reachable = []
            for prov in PROVINCE_POSITIONS:
                if prov != army.province:
                    path = bfs_path(army.province, prov, lambda p: _can_pass(gs, p))
                    if path:
                        reachable.append(prov)
            if reachable:
                gs.highlighted_provinces = reachable
                gs.highlighted_armies    = []
                gs.log("March mode — click any province to set destination.")
                return InputMode.MARCH
            gs.log("No reachable provinces.")
        return mode

    # ATTACK → enter targeting mode, highlight valid enemy armies
    if renderer.btn_attack.is_clicked(event):
        army = gs.selected_army
        if army and army.owner == gs.player_clan_name:
            targets = army.adjacent_enemy_armies(gs.armies, gs.player_clan_name)
            if targets:
                gs.highlighted_armies    = targets
                gs.highlighted_provinces = []
                gs.log("Attack mode — click an enemy army to attack.")
                return InputMode.ATTACK_TARGET
            gs.log("No adjacent enemy armies. March closer first.")
        return mode

    # SIEGE → highlight ALL enemy provinces the army can path toward
    if renderer.btn_siege.is_clicked(event):
        army = gs.selected_army
        if army and army.owner == gs.player_clan_name:
            from map import PROVINCE_POSITIONS, bfs_path
            targets = []
            for prov, city in gs.cities.items():
                # Can siege enemies AND rebel cities
                if city.owner in (gs.player_clan_name, "Neutral"):
                    continue
                path = bfs_path(army.province, prov,
                                passable_fn=lambda p: _can_pass_siege(gs, p, prov))
                if path:
                    targets.append(prov)
            if targets:
                gs.highlighted_provinces = targets
                gs.highlighted_armies    = []
                gs.log("Siege mode — click any enemy province to march and siege.")
                return InputMode.SIEGE_TARGET
            gs.log("No enemy provinces reachable to siege.")
        return mode

    # JOIN
    if renderer.btn_join.is_clicked(event):
        army = gs.selected_army
        if army:
            same = [a for a in gs.get_player_armies()
                    if a.province == army.province and a is not army]
            if same:
                army.join(same[0])
                gs.armies.remove(same[0])
                gs.log(f"Armies joined — {army.total_units()} units at {army.province}")
            else:
                gs.log("No friendly army at same province to join.")
        return mode

    # HIDE / UNHIDE — move army into/out of a nearby ForestPoint
    if renderer.btn_hide.is_clicked(event):
        army = gs.selected_army
        if army and army.owner == gs.player_clan_name:
            if army.hidden:
                # Exit forest
                fp = getattr(army, 'forest_point', None)
                if fp:
                    fp.exit(army)
                else:
                    army.hidden = False
                gs.log(f"Army revealed — no longer hiding in forest.")
            else:
                # Find the nearest ForestPoint this army can enter
                fp = _nearest_forest(gs, army)
                if fp:
                    fp.enter(army)
                    gs.log(f"Army hidden in {fp.name}! Invisible to enemies on that route.")
                else:
                    gs.log("No forest ambush point reachable from here. Move to a route endpoint first.")
        return mode

    return mode


# ── Combat executors ──────────────────────────────────────────────────────────

def _execute_attack(gs, attacker, target):
    owner_name = target.owner
    result = resolve_battle(attacker, target)
    attacker.moved_this_turn = True
    gs.clean_dead_armies()
    _log_battle(gs, result, attacker.owner, owner_name)
    # Log to CSV if player is involved
    if attacker.owner == gs.player_clan_name:
        evt = "BATTLE_WIN" if result.get("attacker_wins") else "BATTLE_LOSS"
        gs.stats.log(gs.turn, evt, gs.player_clan_name,
                     province=attacker.province,
                     units=int(result.get("effective_def_power", 0)),    # dmg taken
                     damage=int(result.get("effective_atk_power", 0)),   # dmg dealt
                     units_lost=int(result.get("attacker_lost", 0)),
                     provinces=len(gs.player_clan().territories))
    elif target.owner == gs.player_clan_name:
        evt = "BATTLE_WIN" if result.get("defender_wins") else "BATTLE_LOSS"
        gs.stats.log(gs.turn, evt, gs.player_clan_name,
                     province=target.province,
                     units=int(result.get("effective_atk_power", 0)),    # dmg taken
                     damage=int(result.get("effective_def_power", 0)),   # dmg dealt
                     units_lost=int(result.get("defender_lost", 0)),
                     provinces=len(gs.player_clan().territories))
    gs.check_clan_elimination()


def _execute_siege(gs, attacker, target_prov):
    city         = gs.cities[target_prov]
    old_owner    = city.owner
    new_dmg      = gs.clans[attacker.owner].default_dmg if attacker.owner in gs.clans else 3.0
    # Include any enemy MapArmy objects physically at the target province
    defending_armies = [a for a in gs.armies
                        if a.province == target_prov
                        and a.owner != attacker.owner
                        and a.is_alive()]
    if defending_armies:
        gs.log(f"Siege of {target_prov}: {len(defending_armies)} enemy army/armies also defending!")

    result = resolve_siege(attacker, city,
                           province_key=target_prov,
                           new_garrison_dmg=new_dmg,
                           defending_armies=defending_armies)
    attacker.moved_this_turn  = True
    attacker.moved_this_turn = True

    if result.get("attacker_wins"):
        old_clan = gs.clans.get(old_owner)
        if old_clan and target_prov in old_clan.territories:
            old_clan.territories.remove(target_prov)
        if target_prov not in gs.player_clan().territories:
            gs.player_clan().territories.append(target_prov)
        attacker.exhaust(siege=True)  # 2-turn siege recovery
        gs.log(f"Conquered {target_prov} from {old_owner}! "
               f"(ATK {int(result['attacker_power'])} vs DEF {int(result['defender_power'])}) "
               f"— Army exhausted.")
        gs.stats.log(gs.turn, "SIEGE_WIN", gs.player_clan_name,
                     province=target_prov,
                     units=int(result.get("defender_power", 0)),
                     damage=int(result.get("attacker_power", 0)),
                     units_lost=int(result.get("attacker_lost", 0)),
                     provinces=len(gs.player_clan().territories))
    else:
        gs.log(f"Siege of {target_prov} failed — "
               f"ATK {int(result['attacker_power'])} vs DEF {int(result['defender_power'])}. "
               f"Recruit more soldiers or combine armies.")
        gs.stats.log(gs.turn, "SIEGE_LOSS", gs.player_clan_name,
                     province=target_prov,
                     units=int(result.get("defender_power", 0)),
                     damage=int(result.get("attacker_power", 0)),
                     units_lost=int(result.get("attacker_lost", 0)),
                     provinces=len(gs.player_clan().territories))
    gs.clean_dead_armies()
    gs.check_clan_elimination()


# ── Misc helpers ──────────────────────────────────────────────────────────────

def _nearest_forest(gs, army):
    """Return the closest ForestPoint that this army can currently enter, or None."""
    for fp in gs.forests.values():
        if fp.can_hide(army):
            return fp
    return None


def _can_pass(gs, province):
    city = gs.cities.get(province)
    if city is None:
        return True
    return city.owner in (gs.player_clan_name, "Neutral", "Rebels")


def _can_pass_siege(gs, province, siege_target):
    if province == siege_target:
        return True
    # Also let army pass through rebel cities en route (can't claim, but can move through)
    city = gs.cities.get(province)
    if city and city.owner == "Rebels":
        return True
    return _can_pass(gs, province)


def _mode_label(mode):
    return {
        InputMode.NORMAL:        "",
        InputMode.MARCH:         "MARCH — click a highlighted province",
        InputMode.ATTACK_TARGET: "ATTACK — click an enemy army",
        InputMode.SIEGE_TARGET:  "SIEGE  — click an enemy province",
    }.get(mode, "")


def _log_battle(gs, result, attacker, defender):
    if result.get("attacker_wins"):
        gs.log(f"{attacker} defeated {defender}! Units left: {result['attacker_units_left']}")
    elif result.get("defender_wins"):
        gs.log(f"{defender} repelled {attacker}! Units left: {result['defender_units_left']}")
    else:
        gs.log("Mutual destruction — both armies wiped out.")


def _draw_ambush_popup(screen, gs, renderer):
    """Overlay popup drawn ON TOP of the already-drawn frame. No extra renderer.draw()."""
    sw, sh = screen.get_size()

    # Semi-transparent dark veil
    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 155))
    screen.blit(overlay, (0, 0))

    from ui import FONT_TL, FONT_LG, FONT_MD, FONT_SM, GOLD_COLOR, WHITE, RED, ORANGE, PANEL_BG, PANEL_LINE
    amb = gs.pending_ambush
    fp  = amb.forest

    # Popup box
    BW, BH = 520, 320
    bx, by = sw//2 - BW//2, sh//2 - BH//2
    pygame.draw.rect(screen, (20, 16, 12), (bx, by, BW, BH), border_radius=12)
    pygame.draw.rect(screen, PANEL_LINE,   (bx, by, BW, BH), 2, border_radius=12)
    # Red accent top
    pygame.draw.rect(screen, (160, 30, 30), (bx, by, BW, 6), border_radius=12)

    # Title
    title = FONT_TL.render("⚔ AMBUSH!", True, (220, 60, 60))
    screen.blit(title, title.get_rect(centerx=sw//2, y=by+18))

    # Forest name
    loc = FONT_LG.render(f"at {fp.name}", True, (100, 200, 80))
    screen.blit(loc, loc.get_rect(centerx=sw//2, y=by+66))

    # Ambusher info
    total_units = sum(a.total_units() for a in amb.ambushers)
    total_power = sum(a.total_power() for a in amb.ambushers)
    info1 = FONT_MD.render(
        f"{amb.ambushers[0].owner} forces ({total_units} units, {int(total_power)}pw) strike from the trees!",
        True, ORANGE)
    screen.blit(info1, info1.get_rect(centerx=sw//2, y=by+108))

    hint = FONT_SM.render("Ambushers struck FIRST — battle already resolved!", True, (160, 150, 130))
    screen.blit(hint, hint.get_rect(centerx=sw//2, y=by+138))
    sub  = FONT_SM.render("(You cannot withdraw from an ambush)", True, (130, 80, 80))
    screen.blit(sub, sub.get_rect(centerx=sw//2, y=by+158))

    # Single dismiss button — fight already resolved, this just clears popup
    BW2, BH2 = 240, 52
    fight_rect = pygame.Rect(sw//2 - BW2//2, by + BH - 76, BW2, BH2)
    mx, my = pygame.mouse.get_pos()
    hov = fight_rect.collidepoint(mx, my)
    c   = (180, 40, 40) if hov else (140, 30, 30)
    pygame.draw.rect(screen, c, fight_rect, border_radius=8)
    pygame.draw.rect(screen, PANEL_LINE if hov else (70, 60, 45), fight_rect, 2, border_radius=8)
    lbl = FONT_LG.render("UNDERSTOOD", True, WHITE)
    screen.blit(lbl, lbl.get_rect(center=fight_rect.center))

    # Store rects for click detection
    gs._ambush_withdraw_rect = None   # no withdraw option
    gs._ambush_fight_rect    = fight_rect


def _handle_ambush_click(pos, gs):
    """Handle player clicking Withdraw or Fight on the ambush popup."""
    amb = gs.pending_ambush
    if not amb or amb.resolved:
        gs.pending_ambush = None
        return
    wr = getattr(gs, '_ambush_withdraw_rect', None)
    fr = getattr(gs, '_ambush_fight_rect',    None)
    if wr and wr.collidepoint(pos):
        amb.resolve_withdraw(gs)
        gs.pending_ambush = None
    elif fr and fr.collidepoint(pos):
        amb.resolve_fight(gs)
        gs.pending_ambush = None


def _draw_game_over(screen, gs):
    sw, sh = screen.get_size()   # always use live screen size (supports fullscreen)
    from ui import FONT_TL, FONT_LG, FONT_MD, FONT_SM, GOLD_COLOR, WHITE, PANEL_LINE, ACCENT_RED
    is_win = gs.winner == gs.player_clan_name

    # Full screen semi-transparent overlay
    overlay = pygame.Surface((sw, sh), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 185))
    screen.blit(overlay, (0, 0))

    # Centred result box
    BW, BH = min(700, sw - 60), 220
    bx, by = sw // 2 - BW // 2, sh // 2 - BH // 2

    pygame.draw.rect(screen, (18, 14, 10), (bx, by, BW, BH), border_radius=14)
    accent_col = GOLD_COLOR if is_win else ACCENT_RED
    pygame.draw.rect(screen, accent_col, (bx, by, BW, BH), 2, border_radius=14)
    pygame.draw.rect(screen, accent_col, (bx, by, BW, 6),  border_radius=14)

    msg = "VICTORY — YOU ARE SHOGUN!" if is_win else "DEFEAT — YOUR CLAN FALLS"
    col = GOLD_COLOR if is_win else (220, 60, 60)
    t = FONT_TL.render(msg, True, col)
    screen.blit(t, t.get_rect(centerx=sw // 2, y=by + 30))

    sub = FONT_LG.render(
        f"{gs.player_clan_name} Clan  —  Turn {gs.turn}",
        True, (180, 170, 140))
    screen.blit(sub, sub.get_rect(centerx=sw // 2, y=by + 100))

    hint = FONT_MD.render("Statistics screen opening…  (ESC to skip)", True, (120, 110, 90))
    screen.blit(hint, hint.get_rect(centerx=sw // 2, y=by + 148))


if __name__ == "__main__":
    main()