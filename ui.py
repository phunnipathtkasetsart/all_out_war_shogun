import pygame
import math
from map import (PROVINCE_POSITIONS, ROUTES, TERRAIN, TERRAIN_COLORS,
                 NODE_RADIUS, CLAN_STARTS)
from city import CITY_LEVEL_CONFIG

# ── Colour palette ─────────────────────────────────────────────────────────────
WHITE       = (255, 255, 255)
BLACK       = (0,   0,   0)
GRAY        = (170, 165, 150)
DARK_GRAY   = (45,  42,  38)
PANEL_BG    = (22,  20,  18)
PANEL_MID   = (32,  28,  24)
PANEL_LINE  = (120, 95,  45)
HIGHLIGHT   = (255, 220,  80)
REACH_HL    = (100, 200, 255, 120)
RED         = (210,  55,  55)
GREEN       = (80,  185,  80)
GOLD_COLOR  = (255, 200,  30)
GOLD_DARK   = (180, 130,  20)
BLUE        = (70,  110, 210)
ORANGE      = (230, 140,  30)
NEUTRAL_CLR = (145, 140, 125)
ACCENT_RED  = (180,  40,  40)

PANEL_W = 310

FLAG_W = 40
FLAG_H = 28

FONT_SM  = None
FONT_MD  = None
FONT_LG  = None
FONT_TL  = None

CLAN_SPRITES: dict = {}
CLAN_SPRITE_CACHE: dict = {}


def init_fonts():
    global FONT_SM, FONT_MD, FONT_LG, FONT_TL
    FONT_SM = pygame.font.SysFont("Arial", 15)
    FONT_MD = pygame.font.SysFont("Arial", 18)
    FONT_LG = pygame.font.SysFont("Arial", 22, bold=True)
    FONT_TL = pygame.font.SysFont("Arial", 34, bold=True)
    _load_clan_sprites()


def _load_clan_sprites():
    global CLAN_SPRITES, CLAN_SPRITE_CACHE
    import os
    base = os.path.dirname(os.path.abspath(__file__))
    CLAN_SPRITES = {}; CLAN_SPRITE_CACHE = {}
    for clan, filename in [("Tada","tada.png"),("Date","date.png"),
                            ("Nori","nori.png"),("Abe","abe.png")]:
        for folder in ["assets", ""]:
            path = os.path.join(base, folder, filename) if folder else os.path.join(base, filename)
            if os.path.exists(path):
                try:   img = pygame.image.load(path).convert_alpha(); CLAN_SPRITES[clan] = img
                except: CLAN_SPRITES[clan] = None
                break
        else:
            CLAN_SPRITES[clan] = None


def _get_sprite(clan: str, size: int, exhausted: bool):
    key = (clan, size, exhausted)
    if key in CLAN_SPRITE_CACHE: return CLAN_SPRITE_CACHE[key]
    raw = CLAN_SPRITES.get(clan)
    if raw is None: CLAN_SPRITE_CACHE[key] = None; return None
    try:    scaled = pygame.transform.smoothscale(raw, (size, size))
    except: scaled = pygame.transform.scale(raw, (size, size))
    if exhausted:
        dark = scaled.copy(); dark.fill((160,160,160,255), special_flags=pygame.BLEND_RGBA_MULT); scaled = dark
    CLAN_SPRITE_CACHE[key] = scaled; return scaled


_SPRITE_CACHE: dict = {}
_CLAN_SPRITE_FILE = {"Tada":"tada","Date":"date","Nori":"nori","Abe":"abe"}

def _load_sprite(owner: str, size: int, darkened: bool):
    key = (owner, size, darkened)
    if key in _SPRITE_CACHE: return _SPRITE_CACHE[key]
    fname = _CLAN_SPRITE_FILE.get(owner)
    if not fname: _SPRITE_CACHE[key] = None; return None
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for folder in ["assets", ""]:
        path = os.path.join(base_dir, folder, fname+".png") if folder else os.path.join(base_dir, fname+".png")
        if os.path.exists(path): break
    else: _SPRITE_CACHE[key] = None; return None
    try:
        raw = pygame.image.load(path).convert_alpha()
        # Scale to target HEIGHT, preserve natural width ratio
        rw, rh = raw.get_size()
        scaled_w = max(1, int(rw * size / max(rh, 1)))
        scaled = pygame.transform.smoothscale(raw, (scaled_w, size))
        if darkened:
            dark = scaled.copy(); dark.fill((160,160,160,255), special_flags=pygame.BLEND_RGBA_MULT); scaled = dark
        _SPRITE_CACHE[key] = scaled; return scaled
    except: _SPRITE_CACHE[key] = None; return None


def _draw_soldier_model(surf, cx, cy, owner, color, t_ms, idx, model_h=52, exhausted=False):
    stagger_y = (idx % 2) * 2
    sprite = _load_sprite(owner, model_h, exhausted)
    if sprite is not None:
        surf.blit(sprite, (cx - sprite.get_width()//2, cy - model_h - stagger_y)); return
    y = cy - stagger_y; skin=(210,180,140); dark=tuple(max(0,c-60) for c in color); light=tuple(min(255,c+50) for c in color)
    if owner == "Tada":
        pygame.draw.ellipse(surf,(100,75,50),(cx-7,y-6,14,7))
        for lx in [-5,-2,2,5]: pygame.draw.line(surf,(80,60,40),(cx+lx,y+1),(cx+lx,y+6),2)
        pygame.draw.ellipse(surf,(110,80,50),(cx+5,y-9,6,5))
        pygame.draw.rect(surf,color,(cx-3,y-14,7,7),border_radius=1)
        pygame.draw.circle(surf,skin,(cx+1,y-17),3); pygame.draw.rect(surf,dark,(cx-2,y-19,7,3))
        pygame.draw.line(surf,light,(cx+4,y-16),(cx+10,y-8),2)
    elif owner == "Date":
        pygame.draw.rect(surf,dark,(cx-4,y-4,4,8)); pygame.draw.rect(surf,dark,(cx+1,y-4,4,8))
        pygame.draw.rect(surf,color,(cx-5,y-13,11,10),border_radius=2)
        pygame.draw.rect(surf,light,(cx-7,y-14,4,4)); pygame.draw.rect(surf,light,(cx+4,y-14,4,4))
        pygame.draw.circle(surf,skin,(cx,y-17),3); pygame.draw.rect(surf,dark,(cx-4,y-21,9,5),border_radius=1)
        pygame.draw.line(surf,(200,200,220),(cx+5,y-20),(cx-2,y+4),2)
    elif owner == "Nori":
        pygame.draw.line(surf,dark,(cx-2,y-2),(cx-3,y+7),2); pygame.draw.line(surf,dark,(cx+2,y-2),(cx+3,y+7),2)
        pygame.draw.rect(surf,color,(cx-3,y-11,7,10),border_radius=1)
        pygame.draw.circle(surf,skin,(cx,y-14),3)
        pygame.draw.polygon(surf,dark,[(cx,y-21),(cx-6,y-12),(cx+6,y-12)])
        pygame.draw.line(surf,(160,140,100),(cx+5,y+8),(cx+5,y-22),2)
        pygame.draw.polygon(surf,(210,210,230),[(cx+5,y-22),(cx+3,y-18),(cx+7,y-18)])
    elif owner == "Abe":
        pygame.draw.rect(surf,dark,(cx-3,y-4,3,8)); pygame.draw.rect(surf,dark,(cx+1,y-4,3,8))
        pygame.draw.rect(surf,color,(cx-4,y-13,9,10),border_radius=2)
        pygame.draw.rect(surf,light,(cx-2,y-12,5,5)); pygame.draw.circle(surf,skin,(cx,y-16),3)
        pygame.draw.circle(surf,dark,(cx,y-18),4); pygame.draw.line(surf,dark,(cx-5,y-15),(cx+5,y-15),2)
        pygame.draw.line(surf,(150,130,90),(cx-5,y+8),(cx-5,y-18),2)
        pygame.draw.polygon(surf,(210,210,230),[(cx-5,y-18),(cx-7,y-14),(cx-3,y-14)])
    else:
        pygame.draw.rect(surf,dark,(cx-3,y-3,3,7)); pygame.draw.rect(surf,dark,(cx+1,y-3,3,7))
        pygame.draw.rect(surf,color,(cx-4,y-12,9,10),border_radius=1)
        pygame.draw.circle(surf,skin,(cx,y-15),3); pygame.draw.rect(surf,dark,(cx-4,y-19,9,4))
        pygame.draw.line(surf,(180,180,200),(cx+4,y-11),(cx+4,y+3),2)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _section(surf, label, x, y, w):
    """Gold ruled line with label."""
    pygame.draw.line(surf, PANEL_LINE, (x, y+7), (x+w, y+7), 1)
    bg = pygame.Surface((len(label)*8+10, 14), pygame.SRCALPHA)
    bg.fill((*PANEL_BG, 255)); surf.blit(bg, (x+6, y))
    surf.blit(FONT_SM.render(label, True, PANEL_LINE), (x+10, y))

def _stat_row(surf, label, value, x, y, w, vcol=WHITE):
    surf.blit(FONT_SM.render(label, True, GRAY), (x, y))
    v = FONT_SM.render(value, True, vcol)
    surf.blit(v, (x+w-v.get_width(), y))

def _pbar(surf, x, y, w, h, frac, col, bg=(38,34,28)):
    pygame.draw.rect(surf, bg,  (x,y,w,h), border_radius=h//2)
    if frac > 0:
        pygame.draw.rect(surf, col, (x,y,max(h,int(w*min(frac,1.0))),h), border_radius=h//2)
    pygame.draw.rect(surf, PANEL_LINE, (x,y,w,h), 1, border_radius=h//2)


# ── Styled button ─────────────────────────────────────────────────────────────
class Button:
    def __init__(self, rect, label, color=BLUE, text_color=WHITE, font=None):
        self.rect=pygame.Rect(rect); self.label=label; self.color=color
        self.hover_color=tuple(min(255,c+45) for c in color)
        self.text_color=text_color; self.font=font; self.enabled=True

    def draw(self, surface):
        f=self.font or FONT_SM; mx,my=pygame.mouse.get_pos()
        hov = self.rect.collidepoint(mx,my) and self.enabled
        col = self.hover_color if hov else self.color
        if not self.enabled: col=(38,35,32)
        pygame.draw.rect(surface, col, self.rect, border_radius=4)
        if self.enabled:
            shine=tuple(min(255,c+60) for c in col)
            pygame.draw.line(surface, shine, (self.rect.x+4,self.rect.y+1),(self.rect.right-4,self.rect.y+1))
        pygame.draw.rect(surface, PANEL_LINE if hov else (55,50,44), self.rect, 1, border_radius=4)
        tc = self.text_color if self.enabled else (80,76,68)
        lbl=f.render(self.label,True,tc); surface.blit(lbl,lbl.get_rect(center=self.rect.center))

    def is_clicked(self, event):
        return (self.enabled and event.type==pygame.MOUSEBUTTONDOWN
                and event.button==1 and self.rect.collidepoint(event.pos))


# ── City sprites ──────────────────────────────────────────────────────────────
_CITY_SPRITE_FILE = {1:"village",2:"fortress",3:"stronghold",4:"castle",5:"citadel"}
_CITY_SPRITE_CACHE: dict = {}

# ── Forest sprite (ambush overlay) ───────────────────────────────────────────
_FOREST_SPRITE: object = None
_FOREST_SPRITE_CACHE: dict = {}

def _load_forest_sprite(size: int):
    """Load forest.png for forest terrain overlay. Cached by size."""
    global _FOREST_SPRITE
    if _FOREST_SPRITE is None:
        import os
        base = os.path.dirname(os.path.abspath(__file__))
        for folder in ["assets", ""]:
            path = os.path.join(base, folder, "forest.png") if folder else os.path.join(base, "forest.png")
            if os.path.exists(path):
                try:    _FOREST_SPRITE = pygame.image.load(path).convert_alpha()
                except: _FOREST_SPRITE = False
                break
        else:
            _FOREST_SPRITE = False
    if not _FOREST_SPRITE:
        return None
    key = size
    if key not in _FOREST_SPRITE_CACHE:
        try:    _FOREST_SPRITE_CACHE[key] = pygame.transform.smoothscale(_FOREST_SPRITE, (size, size))
        except: _FOREST_SPRITE_CACHE[key] = None
    return _FOREST_SPRITE_CACHE[key]

# ── Map background image ──────────────────────────────────────────────────────
_MAP_BG_RAW   = None   # original Surface loaded from map_bg.png
_MAP_BG_CACHE = {}     # (w, h) → scaled Surface

def _draw_map_bg(surf, mw, mh):
    """Draw map_bg.png stretched to fill the map area. Caches scaled version."""
    global _MAP_BG_RAW
    import os
    if _MAP_BG_RAW is None:
        base = os.path.dirname(os.path.abspath(__file__))
        for fname in ["map_bg.png", os.path.join("assets", "map_bg.png")]:
            path = os.path.join(base, fname)
            if os.path.exists(path):
                try:
                    _MAP_BG_RAW = pygame.image.load(path).convert()
                except Exception:
                    _MAP_BG_RAW = False   # mark as unavailable
                break
        else:
            _MAP_BG_RAW = False

    if not _MAP_BG_RAW:
        # Fallback: plain dark background
        pygame.draw.rect(surf, (18, 32, 18), (0, 0, mw, mh))
        return

    key = (mw, mh)
    if key not in _MAP_BG_CACHE:
        _MAP_BG_CACHE[key] = pygame.transform.smoothscale(_MAP_BG_RAW, (mw, mh))
    surf.blit(_MAP_BG_CACHE[key], (0, 0))


def _load_city_sprite(level, size):
    key=(level,size)
    if key in _CITY_SPRITE_CACHE: return _CITY_SPRITE_CACHE[key]
    fname=_CITY_SPRITE_FILE.get(level)
    if not fname: _CITY_SPRITE_CACHE[key]=None; return None
    import os; base=os.path.dirname(os.path.abspath(__file__))
    for folder in ["assets",""]:
        path=os.path.join(base,folder,fname+".png") if folder else os.path.join(base,fname+".png")
        if os.path.exists(path): break
    else: _CITY_SPRITE_CACHE[key]=None; return None
    try:
        raw=pygame.image.load(path).convert_alpha()
        scaled=pygame.transform.smoothscale(raw,(size,size))
        _CITY_SPRITE_CACHE[key]=scaled; return scaled
    except: _CITY_SPRITE_CACHE[key]=None; return None


# ── Clan select ───────────────────────────────────────────────────────────────
def draw_clan_select(surface, clans: dict, hovered: str):
    w, h = surface.get_size()
    surface.fill(PANEL_BG)
    # Warm top glow
    for i in range(70):
        a = int(110*(1-i/70))
        gl=pygame.Surface((w,1),pygame.SRCALPHA); gl.fill((180,100,20,a)); surface.blit(gl,(0,i))

    title=FONT_TL.render("ALL OUT WAR : SHOGUN", True, GOLD_COLOR)
    surface.blit(title, title.get_rect(centerx=w//2, y=52))
    pygame.draw.line(surface, PANEL_LINE, (w//2-title.get_width()//2-20, 94),
                                          (w//2+title.get_width()//2+20, 94), 1)
    sub=FONT_MD.render("Choose your Clan", True, GRAY)
    surface.blit(sub, sub.get_rect(centerx=w//2, y=102))

    cards=list(clans.items()); card_w,card_h=210,182; gap=26
    total_w=len(cards)*card_w+(len(cards)-1)*gap; start_x=(w-total_w)//2; y0=142
    buttons={}
    for i,(name,clan) in enumerate(cards):
        x=start_x+i*(card_w+gap); rect=pygame.Rect(x,y0,card_w,card_h)
        hov=hovered==name
        cs=pygame.Surface((card_w,card_h),pygame.SRCALPHA)
        bg_col=(44,38,30,248) if hov else (28,24,20,230)
        pygame.draw.rect(cs,bg_col,(0,0,card_w,card_h),border_radius=8)
        pygame.draw.rect(cs,clan.color,(0,0,card_w,5),border_radius=8)
        pygame.draw.rect(cs,clan.color if hov else (70,60,45,200),(0,0,card_w,card_h),2,border_radius=8)
        surface.blit(cs,(x,y0))
        spr=_get_sprite(name,60,False)
        if spr: surface.blit(spr,(x+card_w//2-30,y0+10))
        else:   pygame.draw.circle(surface,clan.color,(x+card_w//2,y0+40),28)
        lbl=FONT_LG.render(name,True,HIGHLIGHT if hov else clan.color)
        surface.blit(lbl,lbl.get_rect(centerx=x+card_w//2,y=y0+80))
        for j,s in enumerate([f"Unit  {clan.default_unit}",f"DMG   {clan.default_dmg}",f"Start {clan.start_province}"]):
            t=FONT_SM.render(s,True,(200,195,180) if hov else GRAY)
            surface.blit(t,(x+16,y0+106+j*20))
        buttons[name]=rect

    surface.blit(FONT_SM.render("Click a clan to begin",True,(100,95,80)),
                 FONT_SM.render("Click a clan to begin",True,(100,95,80)).get_rect(centerx=w//2,y=y0+card_h+18))

    # ── Load Saved Game button ────────────────────────────────────────────────
    btn_w, btn_h = 220, 38
    btn_x = w//2 - btn_w//2
    btn_y = y0 + card_h + 46
    load_rect = pygame.Rect(btn_x, btn_y, btn_w, btn_h)
    mx, my = pygame.mouse.get_pos()
    l_hov = load_rect.collidepoint(mx, my)
    l_col = (60, 90, 60) if l_hov else (35, 60, 35)
    pygame.draw.rect(surface, l_col, load_rect, border_radius=6)
    pygame.draw.rect(surface, PANEL_LINE if l_hov else (70, 60, 45), load_rect, 1, border_radius=6)
    ll = FONT_MD.render("📂  Load Saved Game", True, GOLD_COLOR if l_hov else (180, 170, 140))
    surface.blit(ll, ll.get_rect(center=load_rect.center))

    return buttons, load_rect


# ── Main renderer ─────────────────────────────────────────────────────────────
class GameRenderer:

    def __init__(self, surface, gs):
        self.surface=surface; self.gs=gs; self._mode_label=""
        self.btn_next_turn=Button((0,0,286,44),"⚔  END TURN  ⚔",color=ACCENT_RED)
        self.btn_recruit  =Button((0,0,134,30),"Recruit",      color=(50,90,50))
        self.btn_upgrade  =Button((0,0,134,30),"Upgrade City", color=(100,65,20))
        self.btn_attack   =Button((0,0,134,30),"Attack",       color=(130,30,30))
        self.btn_siege    =Button((0,0,134,30),"Siege",        color=(130,30,30))
        self.btn_march    =Button((0,0,134,30),"March",        color=(30,60,110))
        self.btn_join     =Button((0,0,134,30),"Join Army",    color=(30,60,110))
        self.btn_hide     =Button((0,0,278,30),"🌲 Hide in Forest", color=(30,70,30))
        self.slider_x=0; self.slider_y=0; self.slider_w=270
        self.slider_dragging=False; self.tax_slider_value=500
        self._march_anims: dict={}; self._anim_duration_ms=800
        # Turn circle spinner (runs alongside the fade)
        self._spinner_active: bool  = False
        self._spinner_start_ms: int = 0
        self._SPINNER_DURATION_MS   = 2500
        # Map-area fade-in/out (blocks player input during transition)
        # Phase: 0=idle  1=fade_in  2=hold  3=fade_out
        self._map_fade_phase: int     = 0
        self._map_fade_start_ms: int  = 0
        self._MAP_FADE_IN_MS:  int    = 250   # fade to black: 0.25s
        self._MAP_FADE_HOLD_MS: int   = 200   # hold black: 0.2s  (total = 1s)
        self._MAP_FADE_OUT_MS: int    = 550   # reveal new state: 0.55s

    def _panel_x(self): return self.surface.get_width()-PANEL_W
    def _map_w(self):   return self.surface.get_width()-PANEL_W
    def _map_h(self):   return self.surface.get_height()
    def all_buttons(self):
        return [self.btn_next_turn,self.btn_recruit,self.btn_upgrade,
                self.btn_attack,self.btn_siege,self.btn_march,self.btn_join,
                self.btn_hide]

    def begin_turn_animation(self):
        self._pre_turn_pos={}
        for army in self.gs.armies:
            if army.is_alive(): self._pre_turn_pos[id(army)]=self._army_base_px(army)

    def commit_turn_animation(self):
        now=pygame.time.get_ticks(); self._march_anims.clear()
        pre=getattr(self,'_pre_turn_pos',{})
        for army in self.gs.armies:
            if not army.is_alive(): continue
            old=pre.get(id(army))
            if old is None: continue
            new=self._army_base_px(army)
            if old!=new:
                self._march_anims[id(army)]={'sx':old[0],'sy':old[1],'ex':new[0],'ey':new[1],'t':now,'dur':self._anim_duration_ms}

    def is_animating(self):
        now=pygame.time.get_ticks()
        return any(now-v['t']<v['dur'] for v in self._march_anims.values())

    def start_banner(self):
        """Trigger the map fade + spinning arc when a turn starts."""
        self._spinner_active   = True
        self._spinner_start_ms = pygame.time.get_ticks()
        self._map_fade_phase    = 1
        self._map_fade_start_ms = pygame.time.get_ticks()

    def is_fading(self) -> bool:
        """True while the map fade is active (blocks player input)."""
        return self._map_fade_phase != 0

    def advance_map_fade(self):
        """Advance the fade state machine. Call once per frame."""
        if self._map_fade_phase == 0:
            return
        elapsed = pygame.time.get_ticks() - self._map_fade_start_ms
        if self._map_fade_phase == 1 and elapsed >= self._MAP_FADE_IN_MS:
            self._map_fade_phase    = 2
            self._map_fade_start_ms = pygame.time.get_ticks()
        elif self._map_fade_phase == 2 and elapsed >= self._MAP_FADE_HOLD_MS:
            self._map_fade_phase    = 3
            self._map_fade_start_ms = pygame.time.get_ticks()
        elif self._map_fade_phase == 3 and elapsed >= self._MAP_FADE_OUT_MS:
            self._map_fade_phase = 0

    def draw_map_fade(self, screen):
        """Draw the black overlay over ONLY the map area (left of panel) with max opacity 20."""
        if self._map_fade_phase == 0:
            return
            
        elapsed = pygame.time.get_ticks() - self._map_fade_start_ms
        mw = self._map_w()
        sh = screen.get_height()
        
        # We change 255 to 20 to limit the maximum darkness
        MAX_OPACITY = 200

        if self._map_fade_phase == 1:
            # Fades in from 0 to 20
            alpha = int(MAX_OPACITY * min(1.0, elapsed / max(self._MAP_FADE_IN_MS, 1)))
        elif self._map_fade_phase == 2:
            # Stays at 20
            alpha = MAX_OPACITY
        else:
            # Fades out from 20 to 0
            alpha = int(MAX_OPACITY * max(0.0, 1.0 - elapsed / max(self._MAP_FADE_OUT_MS, 1)))

        # Draw only over map area, not the panel
        fade_surf = pygame.Surface((mw, sh))
        fade_surf.set_alpha(alpha)
        fade_surf.fill((0, 0, 0))
        screen.blit(fade_surf, (0, 0))

    def draw_turn_banner(self, screen):
        """No-op — spinner is drawn inside draw_map on the turn circle."""
        pass

    def _army_base_px(self, army):
        if army.next_province and army.km_traveled>0:
            p1=self._scaled_pos(army.province); p2=self._scaled_pos(army.next_province)
            from map import route_km
            seg=route_km(army.province,army.next_province)
            frac=min(1.0,army.km_traveled/seg) if seg>0 else 0.0
            return (int(p1[0]+(p2[0]-p1[0])*frac),int(p1[1]+(p2[1]-p1[1])*frac))
        return self._scaled_pos(army.province)

    def set_mode_label(self, label): self._mode_label=label
    def handle_camera(self, event): return False
    def update_edge_scroll(self, SCROLL_SPEED=6.0): pass

    def _scaled_pos(self, province):
        ox,oy=PROVINCE_POSITIONS[province]; mw=self._map_w(); mh=self._map_h()
        return (int(ox*mw/980), int(oy*mh/720))

    def clamp_camera(self): pass

    def _nr(self):
        return max(28, int(NODE_RADIUS * self._map_w() / 980))

    # ── Map ───────────────────────────────────────────────────────────────────
    def draw_map(self):
        gs=self.gs; surf=self.surface; mw=self._map_w(); mh=self._map_h()
        NR=self._nr(); t_ms=pygame.time.get_ticks()

        # Background — map image stretched to fill map area
        _draw_map_bg(surf, mw, mh)

        # Routes — dark outline + warm fill so they read over the map image
        for a,b in ROUTES:
            pa=self._scaled_pos(a); pb=self._scaled_pos(b)
            pygame.draw.line(surf,(20,16,10),pa,pb,7)   # thick dark shadow
            pygame.draw.line(surf,(110,95,60),pa,pb,3)  # warm road fill
            pygame.draw.line(surf,(145,125,80),pa,pb,1) # bright centre line

        # Animated march dashes
        dash_off=(t_ms//55)%16
        for army in gs.armies:
            if not army.is_marching() or army.exhausted: continue
            path_nodes=[]
            if army.next_province:   path_nodes=[army.province,army.next_province]+army.march_queue[:]
            elif army.march_queue:   path_nodes=[army.province]+army.march_queue[:]
            else: continue
            is_player=army.owner==gs.player_clan_name
            dcol=ORANGE if is_player else (200,90,90)
            for i in range(len(path_nodes)-1):
                p1=self._scaled_pos(path_nodes[i])   if path_nodes[i]   in PROVINCE_POSITIONS else None
                p2=self._scaled_pos(path_nodes[i+1]) if path_nodes[i+1] in PROVINCE_POSITIONS else None
                if not p1 or not p2: continue
                if i==0 and army.next_province and army.km_traveled>0: p1=self._army_base_px(army)
                dx,dy=p2[0]-p1[0],p2[1]-p1[1]; dist=math.hypot(dx,dy)
                if dist==0: continue
                for s in range(int(dist)):
                    if (s+dash_off)%16<8:
                        fx=p1[0]+dx*s/dist; fy=p1[1]+dy*s/dist
                        ex=p1[0]+dx*min(s+1,int(dist))/dist; ey=p1[1]+dy*min(s+1,int(dist))/dist
                        pygame.draw.line(surf,dcol,(int(fx),int(fy)),(int(ex),int(ey)),2)
            if army.next_province and is_player:
                from map import route_km
                seg=route_km(army.province,army.next_province)
                bx,by=self._army_base_px(army)
                surf.blit(FONT_SM.render(f"{army.km_traveled:.0f}/{seg:.0f}km",True,ORANGE),(bx+4,by-16))

        # Highlighted province halos
        siege_targets=getattr(gs,'highlighted_provinces',[])
        for prov in siege_targets:
            pos=self._scaled_pos(prov)
            hl=pygame.Surface((NR*2+30,NR*2+30),pygame.SRCALPHA)
            pygame.draw.circle(hl,(100,200,255,55),(NR+15,NR+15),NR+15)
            pygame.draw.circle(hl,(100,200,255,150),(NR+15,NR+15),NR+15,2)
            surf.blit(hl,(pos[0]-NR-15,pos[1]-NR-15))

        # Province nodes
        for prov in PROVINCE_POSITIONS:
            pos=self._scaled_pos(prov); city=gs.cities.get(prov)
            if city:
                owner=city.owner
                if owner=="Neutral":     name_col=(138,133,115)
                elif owner in gs.clans:  name_col=gs.clans[owner].color
                elif owner=="Rebels":    name_col=(220,60,60)
                else:                    name_col=GRAY
            else: name_col=GRAY

            # Siege ring
            if prov in siege_targets:
                ring=pygame.Surface((NR*2+24,NR*2+24),pygame.SRCALPHA)
                pygame.draw.circle(ring,(255,60,60,200),(NR+12,NR+12),NR+10,3)
                surf.blit(ring,(pos[0]-NR-12,pos[1]-NR-12))

            # City sprite — no circle
            spr=_load_city_sprite(city.city_level if city else 1, NR*2)
            if spr: surf.blit(spr,(pos[0]-NR,pos[1]-NR))
            else:
                pygame.draw.circle(surf,(75,68,50),pos,NR)
                pygame.draw.circle(surf,(95,85,60),pos,NR,2)

            # Selected — pulsing gold ring
            if prov==gs.selected_province:
                pulse=(math.sin(t_ms/300.0)+1)/2
                sel=pygame.Surface((NR*2+20,NR*2+20),pygame.SRCALPHA)
                pygame.draw.circle(sel,(*HIGHLIGHT,int(160+pulse*80)),(NR+10,NR+10),NR+8,3)
                surf.blit(sel,(pos[0]-NR-10,pos[1]-NR-10))

            # Province name with drop shadow
            sh_lbl=FONT_SM.render(prov,True,(0,0,0))
            surf.blit(sh_lbl,sh_lbl.get_rect(centerx=pos[0]+1,y=pos[1]+NR+4))
            surf.blit(FONT_SM.render(prov,True,name_col),
                      FONT_SM.render(prov,True,name_col).get_rect(centerx=pos[0],y=pos[1]+NR+3))



        # ── Forest ambush points ────────────────────────────────────────────────
        forests = getattr(gs, 'forests', {})
        for fp_name, fp in forests.items():
            # Interpolate position on the route scaled to current viewport
            pa = self._scaled_pos(fp.route[0])
            pb = self._scaled_pos(fp.route[1])
            fx = int(pa[0] + (pb[0]-pa[0]) * fp.frac)
            fy = int(pa[1] + (pb[1]-pa[1]) * fp.frac)

            # Pulsing green glow
            pulse_f = (math.sin(t_ms / 700.0 + hash(fp_name) % 8) + 1) / 2
            FR = 24
            fg = pygame.Surface((FR*2+10, FR*2+10), pygame.SRCALPHA)
            fa = int(70 + pulse_f * 60)
            pygame.draw.circle(fg, (25, 110, 25, fa), (FR+5, FR+5), FR+3)
            pygame.draw.circle(fg, (60, 190, 60, int(fa*0.8)), (FR+5, FR+5), FR+3, 2)
            surf.blit(fg, (fx-FR-5, fy-FR-5))

            # Forest sprite or fallback tree shape
            fspr = _load_forest_sprite(FR*2)
            if fspr:
                surf.blit(fspr, (fx-FR, fy-FR))
            else:
                # Draw simple tree shapes as fallback
                pygame.draw.circle(surf, (30, 120, 30), (fx,   fy-8), 14)
                pygame.draw.circle(surf, (45, 150, 45), (fx-11, fy-2), 11)
                pygame.draw.circle(surf, (45, 150, 45), (fx+11, fy-2), 11)
                pygame.draw.rect  (surf, (90, 60, 30),  (fx-3, fy+4, 6, 10))

            # Name label
            flbl = FONT_SM.render(fp_name, True, (80, 200, 80))
            surf.blit(flbl, flbl.get_rect(centerx=fx, y=fy+FR+2))

            # Show hidden army count for player's own armies
            own_hidden = fp.hidden_armies_of(gs.player_clan_name)
            if own_hidden:
                count_txt = FONT_SM.render(f"🌲 {len(own_hidden)} army hiding", True, (140, 255, 100))
                surf.blit(count_txt, count_txt.get_rect(centerx=fx, y=fy+FR+16))

            # Highlight if player army can hide here (idle, at endpoint, not hidden)
            sel = gs.selected_army
            if (sel and sel.owner == gs.player_clan_name
                    and not sel.is_marching()
                    and fp.can_hide(sel)):
                hl = pygame.Surface((FR*2+20, FR*2+20), pygame.SRCALPHA)
                pygame.draw.circle(hl, (100, 255, 100, 100), (FR+10, FR+10), FR+8)
                pygame.draw.circle(hl, (100, 255, 100, 200), (FR+10, FR+10), FR+8, 2)
                surf.blit(hl, (fx-FR-10, fy-FR-10))

        # Armies
        highlighted_armies=getattr(gs,'highlighted_armies',[])
        # Pre-compute which provinces are "near" the player (within 2 hops)
        from map import ADJACENCY as _ADJ
        player_provs = set(gs.player_clan().territories)
        near_provs   = set(player_provs)
        for pp in list(player_provs):
            near_provs.update(_ADJ.get(pp,[]))
            for nb in _ADJ.get(pp,[]):
                near_provs.update(_ADJ.get(nb,[]))

        for army in gs.armies:
            if not army.is_alive(): continue

            is_own   = army.owner == gs.player_clan_name
            # Hidden enemy: skip rendering entirely (fog of war)
            if not is_own and getattr(army,'hidden',False):
                continue
            # "???" for enemy armies NOT near the player
            is_near  = army.province in near_provs
            show_fog = not is_own and not is_near

            ax,ay=self._army_screen_pos(army)
            bob_y=0
            if army.is_marching() and not army.exhausted:
                phase=(id(army)%1000)/1000.0*math.pi*2
                bob_y=int(math.sin(t_ms/300.0+phase)*3)

            # Hidden indicator for OWN armies hiding (only when stationary)
            if is_own and getattr(army,'hidden',False) and not army.is_marching():
                hring=pygame.Surface((NR+20,NR+20),pygame.SRCALPHA)
                pygame.draw.circle(hring,(40,160,40,150),(NR//2+10,NR//2+10),NR//2+8,3)
                surf.blit(hring,(ax-NR//2-10,ay-NR//2-10))

            # Selected pulse ring
            if army==gs.selected_army:
                pulse=(math.sin(t_ms/250.0)+1)/2
                rr=int(NR//2+4+pulse*6); ra=int(80+pulse*120)
                rs=pygame.Surface((rr*2+4,rr*2+4),pygame.SRCALPHA)
                pygame.draw.circle(rs,(*HIGHLIGHT,ra),(rr+2,rr+2),rr,2)
                surf.blit(rs,(ax-rr-2,ay-rr-2))

            # Dust trail
            if army.is_marching() and not army.exhausted and army.next_province:
                p1=self._scaled_pos(army.province); p2=self._scaled_pos(army.next_province)
                from map import route_km
                seg=route_km(army.province,army.next_province)
                frac=min(1.0,army.km_traveled/seg) if seg>0 else 0.0
                cx_=int(p1[0]+(p2[0]-p1[0])*frac); cy_=int(p1[1]+(p2[1]-p1[1])*frac)
                dxn=(p2[0]-p1[0])/max(1,math.hypot(p2[0]-p1[0],p2[1]-p1[1]))
                dyn=(p2[1]-p1[1])/max(1,math.hypot(p2[0]-p1[0],p2[1]-p1[1]))
                for di in range(1,4):
                    da=int(90-di*25); dr=max(1,4-di); drift=(t_ms//120+di*3)%5
                    ds=pygame.Surface((dr*2+2,dr*2+2),pygame.SRCALPHA)
                    pygame.draw.circle(ds,(200,180,140,da),(dr+1,dr+1),dr)
                    surf.blit(ds,(cx_+int(-dxn*di*7+drift-2)-dr,cy_+int(-dyn*di*7+drift-2)-dr))

            # Soldier models
            draw_y=ay+bob_y; clan=gs.clans.get(army.owner); color=clan.color if clan else GRAY
            units=army.total_units(); model_count=max(1,min(10,math.ceil(units/550)))
            draw_col=(tuple(max(0,c-80) for c in color) if army.exhausted
                      else (HIGHLIGHT if army==gs.selected_army else color))
            USE_TWO_ROWS=model_count>5; ROW1=model_count//2 if USE_TWO_ROWS else model_count
            ROW2=model_count-ROW1 if USE_TWO_ROWS else 0
            MODEL_H=max(36,min(52,52-(model_count-1)*2)); MODEL_W=MODEL_H
            MODEL_GAP=max(2,4-model_count//4); ROW_STEP=MODEL_H+2

            if army in highlighted_armies:
                tw2=ROW1*MODEL_W+(ROW1-1)*MODEL_GAP; th2=(2 if USE_TWO_ROWS else 1)*MODEL_H+(1 if USE_TWO_ROWS else 0)*2
                pygame.draw.rect(surf,(255,60,60),(ax-tw2//2-4,draw_y-th2-4,tw2+8,th2+8),2,border_radius=3)

            owner=army.owner; row1_w=ROW1*MODEL_W+(ROW1-1)*MODEL_GAP; row1_x=ax-row1_w//2
            for mi in range(ROW1):
                mx_=row1_x+mi*(MODEL_W+MODEL_GAP)+MODEL_W//2
                _draw_soldier_model(surf,mx_,draw_y,owner,draw_col,t_ms,mi,model_h=MODEL_H,exhausted=army.exhausted)
            if USE_TWO_ROWS:
                row2_w=ROW2*MODEL_W+max(0,ROW2-1)*MODEL_GAP; row2_x=ax-row2_w//2
                for mi in range(ROW2):
                    mx_=row2_x+mi*(MODEL_W+MODEL_GAP)+MODEL_W//2
                    _draw_soldier_model(surf,mx_,draw_y-ROW_STEP,owner,draw_col,t_ms,ROW1+mi,model_h=MODEL_H,exhausted=army.exhausted)

            top_y=draw_y-MODEL_H-(ROW_STEP if USE_TWO_ROWS else 0)
            # Fog of war: distant enemy unit count shows as "???"
            badge_txt = "???" if show_fog else str(units)
            badge_col = (130,120,100) if show_fog else WHITE
            badge=FONT_SM.render(badge_txt,True,badge_col); bxp=ax-badge.get_width()//2
            bb=pygame.Surface((badge.get_width()+6,14),pygame.SRCALPHA); bb.fill((0,0,0,185))
            surf.blit(bb,(bxp-3,draw_y+4)); surf.blit(badge,(bxp,draw_y+5))
            if army.exhausted: surf.blit(FONT_SM.render("✕",True,(220,50,50)),(ax+MODEL_W//2+2,top_y))
            elif army.is_marching():
                beat=(math.sin(t_ms/200.0)+1)/2
                surf.blit(FONT_SM.render("►",True,tuple(int(GOLD_COLOR[i]*(0.6+0.4*beat)) for i in range(3))),(ax+MODEL_W//2+2,top_y))

        # ── Turn circle badge with spinner ───────────────────────────────────
        CX, CY, CR = 62, 44, 38   # centre x, centre y, radius

        # Dark filled circle background
        pygame.draw.circle(surf, (12, 10, 8), (CX, CY), CR)
        # Gold ring
        pygame.draw.circle(surf, PANEL_LINE, (CX, CY), CR, 2)

        # "Turn" small label
        tlbl = FONT_SM.render("TURN", True, GRAY)
        surf.blit(tlbl, tlbl.get_rect(centerx=CX, y=CY - 20))
        # Turn number large
        tnlbl = FONT_LG.render(str(gs.turn), True, GOLD_COLOR)
        surf.blit(tnlbl, tnlbl.get_rect(centerx=CX, centery=CY + 8))

        # ── Red spinning arc during processing ───────────────────────────────
        spinner_active   = getattr(self, '_spinner_active', False)
        spinner_start_ms = getattr(self, '_spinner_start_ms', 0)
        spinner_dur      = getattr(self, '_SPINNER_DURATION_MS', 2500)
        if spinner_active:
            sp_elapsed = t_ms - spinner_start_ms
            if sp_elapsed >= spinner_dur:
                self._spinner_active = False
            else:
                # Arc sweeps 270° around the circle, rotating clockwise
                # Speed: full rotation in ~800ms
                rotation  = (sp_elapsed / 800.0) * 360.0
                arc_span  = 270   # degrees the arc covers
                start_deg = rotation % 360
                end_deg   = (start_deg + arc_span) % 360

                # Draw arc using gfxdraw for anti-aliased look, fallback to lines
                ARC_R = CR + 6
                ARC_W = 4
                arc_surf = pygame.Surface((ARC_R*2+ARC_W*2, ARC_R*2+ARC_W*2), pygame.SRCALPHA)
                ac = ARC_R + ARC_W   # centre in arc_surf
                # Draw arc as a series of short thick lines along the circumference
                steps = 80
                start_r = math.radians(start_deg - 90)   # offset so 0° = top
                span_r  = math.radians(arc_span)
                for i in range(steps + 1):
                    frac = i / steps
                    angle = start_r + span_r * frac
                    # Fade alpha: bright in middle, dim at tails
                    tail_fade = min(frac * 4, 1.0, (1.0 - frac) * 4)
                    a = int(255 * tail_fade)
                    px = int(ac + ARC_R * math.cos(angle))
                    py = int(ac + ARC_R * math.sin(angle))
                    if 0 <= px < arc_surf.get_width() and 0 <= py < arc_surf.get_height():
                        pygame.draw.circle(arc_surf, (220, 50, 50, a), (px, py), ARC_W//2 + 1)
                surf.blit(arc_surf, (CX - ac, CY - ac))

        # Mode label
        lbl=getattr(self,'_mode_label','')
        if lbl:
            lw=FONT_MD.size(f"[ {lbl} ]")[0]+22
            mb=pygame.Surface((lw,26),pygame.SRCALPHA)
            pygame.draw.rect(mb,(0,0,0,185),(0,0,lw,26),border_radius=4)
            pygame.draw.rect(mb,HIGHLIGHT,(0,0,lw,26),1,border_radius=4)
            surf.blit(mb,(mw//2-lw//2,6))
            surf.blit(FONT_MD.render(f"[ {lbl} ]",True,HIGHLIGHT),
                      FONT_MD.render(f"[ {lbl} ]",True,HIGHLIGHT).get_rect(centerx=mw//2,centery=19))

    # ── Panel ─────────────────────────────────────────────────────────────────
    def draw_panel(self):
        gs=self.gs; surf=self.surface; px=self._panel_x(); pw=PANEL_W; sh=self.surface.get_height()
        player=gs.player_clan(); city=gs.cities.get(gs.selected_province) if gs.selected_province else None
        mx=px+12; cw=pw-24

        # Panel bg + border
        pygame.draw.rect(surf,PANEL_BG,(px,0,pw,sh))
        pygame.draw.line(surf,PANEL_LINE,(px,0),(px,sh),2)
        pygame.draw.rect(surf,ACCENT_RED,(px,0,pw,4))

        def T(s,x,y,col=WHITE,f=None):
            (f or FONT_SM).render(str(s),True,col)
            surf.blit((f or FONT_SM).render(str(s),True,col),(x,y))

        y=10

        # ── Clan header ───────────────────────────────────────────────────────
        T(player.name, mx, y, player.color, FONT_LG); 
        spr=_get_sprite(player.name,34,False)
        if spr: surf.blit(spr,(px+pw-46,y))
        y+=26

        upkeep=sum(a.maintenance_cost() for a in gs.armies if a.owner==gs.player_clan_name and a.is_alive())
        tax_total=sum(gs.cities[p].tax_income() for p in player.territories if p in gs.cities)
        net=tax_total-upkeep; sign="+" if net>=0 else ""

        # Treasury big line
        gv=FONT_MD.render(f"{player.gold:,} G",True,GOLD_COLOR)
        T("Treasury",mx,y,GRAY); surf.blit(gv,(px+pw-gv.get_width()-12,y-1)); y+=18
        for lbl,val,col in [("Tax / turn",f"+{tax_total} G",GREEN),
                             ("Upkeep / turn",f"−{upkeep} G",RED),
                             ("Net / turn",f"{sign}{net} G",GREEN if net>=0 else RED),
                             ("Territories",str(len(player.territories)),WHITE)]:
            _stat_row(surf,lbl,val,mx,y,cw,col); y+=16
        if player.debt>0:
            db=pygame.Surface((cw,17),pygame.SRCALPHA); db.fill((180,30,30,55)); surf.blit(db,(mx,y))
            T(f"⚠ In debt: {player.debt} G",mx+3,y+1,RED); y+=18
        y+=4

        # ── Province ─────────────────────────────────────────────────────────
        _section(surf,"PROVINCE",mx,y,cw); y+=15
        if city and gs.selected_province:
            owner_col=(player.color if city.owner==player.name else
                       ((220,55,55) if city.owner=="Rebels" else
                        ((180,50,50) if city.owner!="Neutral" else GRAY)))
            T(gs.selected_province,mx,y,HIGHLIGHT,FONT_LG); y+=22
            for lbl,val,col in [("City",city.name[:18],WHITE),("Owner",city.owner,owner_col),("Level",city.label(),GOLD_COLOR)]:
                _stat_row(surf,lbl,val,mx,y,cw,col); y+=15
            rage=city.rage_level; rc=RED if rage>=5 else (ORANGE if rage>=4 else (GOLD_COLOR if rage>=3 else GREEN))
            T("Rage",mx,y,GRAY); _pbar(surf,mx+68,y+3,cw-70,9,rage/6,rc); T(f"{rage}/6",px+pw-28,y,rc); y+=16
            if city.resistance_turns>0: T(f"Resistance: {city.resistance_turns}t",mx,y,ORANGE); y+=14
        else:
            T("Click a province or army",mx,y+3,(70,66,58)); y+=16

        # ── Army ─────────────────────────────────────────────────────────────
        _section(surf,"ARMY",mx,y,cw); y+=15
        if gs.selected_army:
            army=gs.selected_army
            status=("EXHAUSTED" if army.exhausted else (f"→ {army.march_queue[-1]}" if army.is_marching() else "Idle"))
            sc=RED if army.exhausted else (ORANGE if army.is_marching() else GREEN)
            for lbl,val,col in [("Owner",army.owner,WHITE),("Units",str(army.total_units()),WHITE),
                                 ("Power",str(int(army.total_power())),GOLD_COLOR),("Status",status[:20],sc)]:
                _stat_row(surf,lbl,val,mx,y,cw,col); y+=15
            if army.siege_target and army.is_marching():
                from map import route_km as rkm
                km_info=f" {army.km_traveled:.0f}/{rkm(army.province,army.next_province):.0f}km" if army.next_province else ""
                T(f"SIEGE→{army.siege_target} ({army.turns_to_arrive()}t){km_info}",mx,y,RED); y+=14
            elif army.is_marching():
                dest=army.march_queue[-1] if army.march_queue else army.next_province
                T(f"Marching→{dest} ({army.turns_to_arrive()}t)",mx,y,ORANGE); y+=14
        else:
            T("No army selected",mx,y,(70,66,58)); y+=15



        # ── Tax slider ───────────────────────────────────────────────────────
        _section(surf,"TAX",mx,y,cw); y+=14
        self.slider_y=y; self._draw_slider(surf,px,mx,cw,city); y+=44

        # ── Actions ──────────────────────────────────────────────────────────
        _section(surf,"ACTIONS",mx,y,cw); y+=14
        own_selected=bool(city and city.owner==player.name)
        pa=gs.selected_army; pas=pa is not None and pa.owner==player.name
        eaa=bool(pa.adjacent_enemy_armies(gs.armies,gs.player_clan_name)) if pas else False
        self.btn_recruit.enabled=own_selected and bool(city and city.can_queue_recruit())
        self.btn_upgrade.enabled=own_selected and bool(city and city.can_queue_upgrade())
        am=pas and pa.is_marching()
        if am: self.btn_march.label="Cancel March"; self.btn_march.color=(110,55,20); self.btn_march.enabled=True
        else:  self.btn_march.label="March"; self.btn_march.color=(30,60,110); self.btn_march.enabled=pas and not pa.moved_this_turn and not pa.exhausted
        self.btn_attack.enabled=pas and eaa and not pa.exhausted
        # Siege valid vs enemy clans AND rebel cities
        sb = pas and (pa.siege_target is not None or pa.exhausted or am)
        self.btn_siege.enabled = pas and not sb
        self.btn_join.enabled=pas and self._friendly_army_same_province() and not pa.exhausted

        BW=(cw-10)//2; BH=30
        for row_btns in [[self.btn_recruit,self.btn_upgrade],[self.btn_attack,self.btn_siege],[self.btn_march,self.btn_join]]:
            for i,btn in enumerate(row_btns):
                btn.rect.x=mx+i*(BW+10); btn.rect.y=y; btn.rect.width=BW; btn.rect.height=BH; btn.draw(surf)
            y+=BH+6
        # Hide button — correctly reflects army's current forest state
        forests = getattr(gs, 'forests', {})
        sel_army = gs.selected_army if pas else None
        army_is_hidden  = bool(sel_army and getattr(sel_army, 'hidden', False))
        army_is_marching= bool(sel_army and sel_army.is_marching())
        # can_hide checks: not already hidden, not marching, at route endpoint
        near_forest = (bool(sel_army) and not army_is_marching and not army_is_hidden
                       and any(fp.can_hide(sel_army) for fp in forests.values()))

        if army_is_hidden and army_is_marching:
            # Army left forest and started marching — show as normal marching
            self.btn_hide.enabled = False
            self.btn_hide.label   = "🌲 Left Forest (marching)"
            self.btn_hide.color   = (38, 35, 32)
        elif army_is_hidden:
            # Stationary and hidden — can reveal
            self.btn_hide.enabled = True
            self.btn_hide.label   = "🌲 Reveal Army  [Hidden]"
            self.btn_hide.color   = (20, 110, 20)
        elif near_forest:
            # Idle at a forest route endpoint — can hide
            self.btn_hide.enabled = True
            self.btn_hide.label   = "🌲 Hide in Forest"
            self.btn_hide.color   = (35, 80, 35)
        else:
            # Not near a forest or already marching
            self.btn_hide.enabled = False
            self.btn_hide.label   = "🌲 Hide in Forest"
            self.btn_hide.color   = (38, 35, 32)
        self.btn_hide.rect.x=mx; self.btn_hide.rect.y=y; self.btn_hide.rect.width=cw; self.btn_hide.rect.height=BH
        self.btn_hide.draw(surf); y+=BH+6

        # ── Event log ────────────────────────────────────────────────────────
        log_top=y+4; log_bot=sh-56
        _section(surf,"EVENT LOG",mx,log_top,cw); log_y=log_top+15
        log_h=log_bot-log_y
        if log_h>8:
            lb=pygame.Surface((cw,log_h),pygame.SRCALPHA)
            lb.fill((10,8,6,185)); pygame.draw.rect(lb,(50,44,34,180),(0,0,cw,log_h),1,border_radius=4)
            surf.blit(lb,(mx,log_y))
        lh=14; max_lines=max(1,log_h//lh)
        for i,msg in enumerate(gs.log_messages[-max_lines:]):
            if log_y+i*lh>log_bot-2: break
            mc=((225,80,80) if "🔥" in msg or "REBELLION" in msg or "eliminated" in msg else
                (ORANGE      if "⚠" in msg or "debt" in msg.lower() else
                 (120,195,90) if "✓" in msg or "conquered" in msg.lower() or "claimed" in msg.lower() else
                 (PANEL_LINE  if "──" in msg else (182,175,160))))
            surf.blit(FONT_SM.render(msg[:44],True,mc),(mx+4,log_y+i*lh+2))

        # ── Next turn ────────────────────────────────────────────────────────
        nt_y=sh-50
        gw=pygame.Surface((cw+4,48),pygame.SRCALPHA)
        pygame.draw.rect(gw,(180,40,40,35),(0,0,cw+4,48),border_radius=6); surf.blit(gw,(mx-2,nt_y-2))
        self.btn_next_turn.rect.x=mx; self.btn_next_turn.rect.y=nt_y
        self.btn_next_turn.rect.width=cw; self.btn_next_turn.rect.height=44
        self.btn_next_turn.draw(surf)

    def _draw_slider(self, surf, px, mx, cw, city):
        gs=self.gs; sy=self.slider_y; sx=mx; sw=cw
        self.slider_x=sx; self.slider_w=sw
        # Use the city's actual tax range (scales with city level)
        if city and city.owner==gs.player_clan_name:
            t_min=city.tax_min(); t_max=city.tax_max()
            val=city.tax_level
            # Clamp val to current range in case city was recently upgraded
            val=max(t_min, min(t_max, val))
            self.tax_slider_value=val
        else:
            t_min=500; t_max=1000; val=self.tax_slider_value
        frac=(val-t_min)/max(1,(t_max-t_min))
        surf.blit(FONT_SM.render("Tax",True,GRAY),(sx,sy))
        vl=FONT_SM.render(f"{val} G",True,GOLD_COLOR); surf.blit(vl,(sx+sw-vl.get_width(),sy))
        ty=sy+17; pygame.draw.rect(surf,(38,34,28),(sx,ty,sw,8),border_radius=4)
        fc=GREEN if frac<0.5 else (ORANGE if frac<0.75 else RED)
        if frac>0: pygame.draw.rect(surf,fc,(sx,ty,max(8,int(sw*frac)),8),border_radius=4)
        pygame.draw.rect(surf,PANEL_LINE,(sx,ty,sw,8),1,border_radius=4)
        tx=sx+int(frac*sw)
        pygame.draw.circle(surf,GOLD_COLOR,(tx,ty+4),8); pygame.draw.circle(surf,GOLD_DARK,(tx,ty+4),8,2)
        surf.blit(FONT_SM.render(f"{t_min}",True,(78,74,66)),(sx,ty+11))
        rm=FONT_SM.render(f"{t_max}",True,(78,74,66)); surf.blit(rm,(sx+sw-rm.get_width(),ty+11))

    def handle_slider(self, event):
        sx=self.slider_x; sy=self.slider_y+17; sw=self.slider_w
        if event.type==pygame.MOUSEBUTTONDOWN and event.button==1:
            if abs(event.pos[1]-sy)<16 and sx<=event.pos[0]<=sx+sw: self.slider_dragging=True
        if event.type==pygame.MOUSEBUTTONUP and event.button==1: self.slider_dragging=False
        if event.type==pygame.MOUSEMOTION and self.slider_dragging:
            gs=self.gs
            if gs.selected_province:
                city=gs.cities.get(gs.selected_province)
                if city and city.owner==gs.player_clan_name:
                    t_min=city.tax_min(); t_max=city.tax_max()
                    frac=max(0.0,min(1.0,(event.pos[0]-sx)/sw))
                    new_val=int(t_min+frac*(t_max-t_min))
                    city.tax_level=new_val; self.tax_slider_value=new_val
            else:
                frac=max(0.0,min(1.0,(event.pos[0]-sx)/sw))
                self.tax_slider_value=int(500+frac*500)

    def province_at(self, pos):
        mw=self._map_w(); hit_r=NODE_RADIUS*mw//980+10
        for prov in PROVINCE_POSITIONS:
            sp=self._scaled_pos(prov); dx=pos[0]-sp[0]; dy=pos[1]-sp[1]
            if dx*dx+dy*dy<=hit_r**2: return prov
        return None

    def army_at(self, pos):
        for army in self.gs.armies:
            if not army.is_alive(): continue
            ax,ay=self._army_screen_pos(army); dx=pos[0]-ax; dy=pos[1]-ay
            if dx*dx+dy*dy<=300: return army
        return None

    def _friendly_army_same_province(self):
        gs=self.gs
        if not gs.selected_army: return False
        same=gs.get_armies_at(gs.selected_army.province)
        return len([a for a in same if a.owner==gs.player_clan_name])>1

    def _army_screen_pos(self, army):
        gs=self.gs; FLAG_GAP=4; now=pygame.time.get_ticks()
        anim=self._march_anims.get(id(army))
        if anim:
            el=now-anim['t']; t=min(1.0,el/max(1,anim['dur'])); t=t*t*(3-2*t)
            bx=int(anim['sx']+(anim['ex']-anim['sx'])*t); by=int(anim['sy']+(anim['ey']-anim['sy'])*t)
            if el>=anim['dur']: del self._march_anims[id(army)]
            return (bx, by-self._nr()-FLAG_H//2-4)
        if army.next_province and army.km_traveled>0:
            p1=self._scaled_pos(army.province); p2=self._scaled_pos(army.next_province)
            from map import route_km
            seg=route_km(army.province,army.next_province); frac=min(1.0,army.km_traveled/seg) if seg>0 else 0.0
            bx=int(p1[0]+(p2[0]-p1[0])*frac); by=int(p1[1]+(p2[1]-p1[1])*frac)
            same_seg=[a for a in gs.armies if a.is_alive() and a.province==army.province and a.next_province==army.next_province]
            idx=same_seg.index(army) if army in same_seg else 0
            return (bx, by-self._nr()-FLAG_H//2-4-idx*(FLAG_H+2))
        bx,by=self._scaled_pos(army.province)
        all_here=[a for a in gs.armies if a.is_alive() and a.province==army.province and not a.next_province]
        count=len(all_here); idx=all_here.index(army) if army in all_here else 0
        total_w=count*FLAG_W+(count-1)*FLAG_GAP; start_x=bx-total_w//2+FLAG_W//2
        return (start_x+idx*(FLAG_W+FLAG_GAP), by-self._nr()-FLAG_H//2-4)

    def _progress_bar(self, surf, x, y, w, h, done, total, color):
        _pbar(surf, x, y, w, h, done/max(total,1), color)

    def draw_queue_overlay(self):
        gs=self.gs; surf=self.surface; mw=self._map_w(); mh=self._map_h()
        items=[]
        for prov,city in gs.cities.items():
            if city.owner!=gs.player_clan_name: continue
            if city.upgrade_turns_left>0:
                tl=city.city_level+1; nxt=city.CITY_LEVEL_CONFIG.get(tl,{}).get("label","?")
                items.append({"type":"upgrade","label":nxt,"sublabel":prov[:8],"turns_left":city.upgrade_turns_left,"turns_total":city.UPGRADE_TURNS,"color":ORANGE,"target_level":tl})
            for turns_left,soldier in city.recruit_queue:
                items.append({"type":"recruit","label":soldier.name[:10],"sublabel":prov[:8],"turns_left":turns_left,"turns_total":city.RECRUIT_TURNS,"color":GREEN,"units":soldier.unit,"owner":gs.player_clan_name})
        if not items: return
        CARD_W=80; CARD_H=100; CARD_GAP=6; TRAY_PAD=8
        MC=min(len(items),(mw-20)//(CARD_W+CARD_GAP))
        tw=MC*(CARD_W+CARD_GAP)-CARD_GAP+TRAY_PAD*2; th=CARD_H+TRAY_PAD*2+18
        tx=12; ty=mh-th-12
        ts=pygame.Surface((tw,th),pygame.SRCALPHA)
        pygame.draw.rect(ts,(15,12,10,220),(0,0,tw,th),border_radius=8)
        pygame.draw.rect(ts,PANEL_LINE,(0,0,tw,th),1,border_radius=8); surf.blit(ts,(tx,ty))
        surf.blit(FONT_SM.render("Production",True,PANEL_LINE),(tx+TRAY_PAD,ty+2))
        for i,item in enumerate(items[:MC]):
            cx=tx+TRAY_PAD+i*(CARD_W+CARD_GAP); cy=ty+TRAY_PAD+16
            col=item["color"]; frac=1.0-item["turns_left"]/max(item["turns_total"],1); is_up=item["type"]=="upgrade"
            cs=pygame.Surface((CARD_W,CARD_H),pygame.SRCALPHA)
            pygame.draw.rect(cs,(22,18,14,245),(0,0,CARD_W,CARD_H),border_radius=6)
            pygame.draw.rect(cs,col,(0,0,CARD_W,4),border_radius=6)
            pygame.draw.rect(cs,(col[0]//3,col[1]//3,col[2]//3,160),(0,0,CARD_W,CARD_H),1,border_radius=6)
            surf.blit(cs,(cx,cy))
            ART_H=48; acx=cx+CARD_W//2; acy=cy+6
            if is_up:
                spr=_load_city_sprite(item.get("target_level",1),ART_H)
                if spr: surf.blit(spr,(acx-ART_H//2,acy))
            else:
                spr=_load_sprite(item.get("owner",""),ART_H,False)
                if spr: surf.blit(spr,(acx-ART_H//2,acy))
                surf.blit(FONT_SM.render(str(item.get("units","")),True,WHITE),(cx+3,cy+7))
            pygame.draw.line(surf,(55,48,36),(cx+4,cy+58),(cx+CARD_W-4,cy+58),1)
            lbl=FONT_SM.render(item["label"][:10],True,WHITE); surf.blit(lbl,lbl.get_rect(centerx=cx+CARD_W//2,y=cy+61))
            sub=FONT_SM.render(item["sublabel"],True,GRAY); surf.blit(sub,sub.get_rect(centerx=cx+CARD_W//2,y=cy+74))
            _pbar(surf,cx+5,cy+CARD_H-14,CARD_W-10,6,frac,col)
            tlt=FONT_SM.render(f"{item['turns_left']}t",True,col); surf.blit(tlt,(cx+CARD_W-tlt.get_width()-3,cy+61))

    def draw(self):
        self.draw_map()
        self.draw_panel()
        self.draw_queue_overlay()