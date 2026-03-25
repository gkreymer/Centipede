import os
import sys
import math
import random
import array

import pygame

# ---------- AUDIO PRE-INIT (mono, 16-bit) ----------
pygame.mixer.pre_init(44100, -16, 1, 512)
pygame.init()
pygame.font.init()

# ---------- CONFIG / CONSTANTS ----------

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# Higher-res portrait playfield (~HD width)
WIDTH, HEIGHT = 720, 960       # logical game resolution
FPS = 60

SEGMENT_SIZE = 24              # grid cell size
MUSHROOM_SIZE = SEGMENT_SIZE
PIXEL_SCALE = max(1, SEGMENT_SIZE // 8)

PLAYER_SPEED = 4
BULLET_SPEED = -13

GRID_COLS = WIDTH // SEGMENT_SIZE
GRID_ROWS = (HEIGHT - 80) // SEGMENT_SIZE  # leave room for HUD at bottom

PLAYER_AREA_HEIGHT = 220  # bottom zone where player can move
HUD_BAR_HEIGHT = 56

MUSHROOM_HP = 4
INITIAL_CENTIPEDE_LENGTH = 12
EXTRA_LIFE_SCORE = 12000
MUSHROOM_RESTORE_BONUS = 5
READY_FRAMES = FPS * 2

# Centipede speeds are based on "grid cells per second" from the article:
# Odd levels & 9+ ~15 cells/sec, even (<=8) ~7.5 cells/sec. We'll convert
# to pixels/frame given SEGMENT_SIZE and FPS.
# (level, cells_per_second, mushroom_density, spawn_mult)
LEVEL_TABLE = [
    (1,  15.0, 0.06, 1.0),
    (2,   7.5, 0.07, 1.05),
    (3,  15.0, 0.08, 1.1),
    (4,   7.5, 0.09, 1.2),
    (5,  15.0, 0.10, 1.3),
    (6,   7.5, 0.11, 1.4),
    (7,  15.0, 0.12, 1.6),
    (8,   7.5, 0.13, 1.8),
    (9,  15.0, 0.14, 2.0),
    (10, 15.0, 0.15, 2.2),
    (11, 15.0, 0.16, 2.4),
    (12, 15.0, 0.16, 2.6),
]

CENTIPEDE_MAX_EXTRA_SPEED = 1.5  # extra px/frame when very short

SPIDER_SPEED_MIN = 2.0
SPIDER_SPEED_MAX = 4.0

SPIDER_SIZE = 40  # larger sprite

SCORPION_SPEED = 3  # ~one "original pixel per frame" scaled to our width
SCORPION_WIDTH = SEGMENT_SIZE * 3
SCORPION_HEIGHT = SEGMENT_SIZE * 2

# Flea: original ~2 px/frame on a 240px tall playfield -> crosses in ~2s.
# Our height is 960, so ~8 px/frame keeps roughly same feel.
FLEA_SPEED = 8.0
FLEA_MIN_MUSHROOMS_PLAYER_AREA = 5
FLEA_MUSHROOM_CHANCE_PER_ROW = 0.4

# Spawn bases; scaled by spawn_mult from level table
SPIDER_SPAWN_BASE = 0.003
SCORPION_SPAWN_BASE = 0.0015
FLEA_SPAWN_BASE = 0.01

# Scores (roughly arcade-like)
HEAD_SCORE = 100
BODY_SCORE = 10
SPIDER_SCORE_LOW = 300
SPIDER_SCORE_MID = 600
SPIDER_SCORE_HIGH = 900
FLEA_SCORE = 200
SCORPION_SCORE = 1000
MUSHROOM_DESTROY_SCORE = 1

# Colors (tuned to resemble the arcade palette a bit more)
BLACK   = (0, 0, 0)
WHITE   = (255, 255, 255)
GREEN   = (0, 255, 0)
RED     = (255, 0, 0)
BLUE    = (0, 160, 255)
YELLOW  = (255, 255, 0)
PURPLE  = (190, 0, 190)
GRAY    = (120, 120, 120)
BROWN   = (139, 69, 19)
CYAN    = (0, 220, 220)
ORANGE  = (255, 165, 0)
POISON_PURPLE = (255, 0, 255)
DARK_BLUE = (10, 40, 90)
DARK_ORANGE = (200, 110, 40)
DARK_CYAN = (0, 140, 140)

# Inspired by arcade colors
CENTI_BODY_GREEN = (60, 240, 60)
CENTI_OUTLINE = (0, 90, 0)
CENTI_HEAD_RED = (250, 80, 80)
MUSHROOM_CAP_PURPLE = (190, 40, 190)
MUSHROOM_CAP_DARK = (120, 20, 120)
MUSHROOM_STEM = (230, 220, 200)
MUSHROOM_SPOT = (255, 240, 220)
HUD_GREEN = (110, 255, 120)
HUD_RED = (255, 90, 90)
HUD_GOLD = (255, 220, 80)
HUD_DIM = (30, 70, 30)
STAR_COLORS = [
    (70, 240, 90),
    (255, 120, 90),
    (255, 220, 100),
    (110, 180, 255),
]

FONT_SMALL = pygame.font.SysFont("consolas", 18, bold=True)
FONT_MED   = pygame.font.SysFont("consolas", 24, bold=True)
FONT_LARGE = pygame.font.SysFont("consolas", 40, bold=True)
FONT_TITLE = pygame.font.SysFont("consolas", 54, bold=True)

# Idle timeout before going back to attract mode (ms)
IDLE_TIMEOUT_MS = 45000


# ---------- SOUND GENERATION ----------

def generate_tone(
    freq,
    duration,
    volume=0.5,
    waveform="sine",
    attack=0.01,
    release=0.04,
):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    buf = array.array("h")
    max_amp = int(32767 * volume)

    for i in range(n_samples):
        t = i / sample_rate

        # Envelope
        env = 1.0
        if t < attack:
            env = t / max(attack, 1e-6)
        elif t > duration - release:
            env = max(0.0, (duration - t) / max(release, 1e-6))

        # Waveform
        phase = 2 * math.pi * freq * t
        if waveform == "sine":
            sample = math.sin(phase)
        elif waveform == "triangle":
            sample = 2 / math.pi * math.asin(math.sin(phase))
        elif waveform == "square":
            sample = 1.0 if math.sin(phase) >= 0 else -1.0
        elif waveform == "noise":
            sample = random.uniform(-1.0, 1.0)
        else:
            sample = math.sin(phase)

        value = int(max_amp * env * sample)
        buf.append(value)

    return pygame.mixer.Sound(buffer=buf)


def generate_gliss(start_freq, end_freq, duration, volume=0.5, waveform="sine"):
    sample_rate = 44100
    n_samples = int(sample_rate * duration)
    buf = array.array("h")
    max_amp = int(32767 * volume)

    for i in range(n_samples):
        t = i / sample_rate
        # Linear interpolation of frequency
        freq = start_freq + (end_freq - start_freq) * (i / max(1, n_samples - 1))

        # Simple envelope
        attack = duration * 0.05
        release = duration * 0.15
        env = 1.0
        if t < attack:
            env = t / max(attack, 1e-6)
        elif t > duration - release:
            env = max(0.0, (duration - t) / max(release, 1e-6))

        phase = 2 * math.pi * freq * t
        if waveform == "sine":
            sample = math.sin(phase)
        elif waveform == "triangle":
            sample = 2 / math.pi * math.asin(math.sin(phase))
        else:
            sample = math.sin(phase)

        value = int(max_amp * env * sample)
        buf.append(value)

    return pygame.mixer.Sound(buffer=buf)


# ---------- HELPER CLASSES ----------

def clamp(value, low, high):
    return max(low, min(high, value))


def lerp(start, end, t):
    return start + (end - start) * t


def make_pixel_sprite(pattern, palette, scale=1):
    width = max(len(row) for row in pattern)
    height = len(pattern)
    sprite = pygame.Surface((width * scale, height * scale), pygame.SRCALPHA)
    for y, row in enumerate(pattern):
        for x, char in enumerate(row):
            color = palette.get(char)
            if color:
                pygame.draw.rect(
                    sprite,
                    color,
                    (x * scale, y * scale, scale, scale),
                )
    return sprite


def make_glow(sprite, color, alpha=88, scale_factor=1.35):
    mask = pygame.mask.from_surface(sprite)
    glow = mask.to_surface(setcolor=(*color, alpha), unsetcolor=(0, 0, 0, 0))
    glow = glow.convert_alpha()
    glow_w = max(glow.get_width(), int(glow.get_width() * scale_factor))
    glow_h = max(glow.get_height(), int(glow.get_height() * scale_factor))
    return pygame.transform.smoothscale(glow, (glow_w, glow_h))


def make_asset_from_sprite(sprite, glow_color, alpha=88, scale_factor=1.35):
    return {
        "sprite": sprite,
        "glow": make_glow(sprite, glow_color, alpha=alpha, scale_factor=scale_factor),
    }


def draw_asset(surface, asset, position, centered=False):
    sprite = asset["sprite"]
    glow = asset["glow"]
    if centered:
        x = int(position[0] - sprite.get_width() / 2)
        y = int(position[1] - sprite.get_height() / 2)
    else:
        x, y = int(position[0]), int(position[1])

    glow_x = x - (glow.get_width() - sprite.get_width()) // 2
    glow_y = y - (glow.get_height() - sprite.get_height()) // 2
    surface.blit(glow, (glow_x, glow_y))
    surface.blit(sprite, (x, y))


def blit_text(surface, font, text, color, position, align="topleft", shadow=BLACK):
    shadow_surf = font.render(text, True, shadow)
    text_surf = font.render(text, True, color)

    text_rect = text_surf.get_rect()
    setattr(text_rect, align, position)

    shadow_rect = text_rect.copy()
    shadow_rect.move_ip(2, 2)

    surface.blit(shadow_surf, shadow_rect)
    surface.blit(text_surf, text_rect)
    return text_rect


SPRITE_BANK = None


def get_sprite_bank():
    global SPRITE_BANK
    if SPRITE_BANK is not None:
        return SPRITE_BANK

    player_pattern = [
        "...GG...",
        "..GYYG..",
        ".GGYYGG.",
        "GGYYYYGG",
        "GGYYYYGG",
        ".GG..GG.",
        "..G..G..",
        "..G..G..",
    ]
    body_patterns = [
        [
            "..GGGG..",
            ".GGYYGG.",
            "GGGGGGGG",
            "GYGGGGYG",
            "GGGGGGGG",
            ".GGYYGG.",
            ".Y....Y.",
            "Y......Y",
        ],
        [
            "..GGGG..",
            ".GGYYGG.",
            "GGGGGGGG",
            "GGYGGYGG",
            "GGGGGGGG",
            ".YGGGGY.",
            "Y......Y",
            ".Y....Y.",
        ],
    ]
    head_patterns = [
        [
            "..RRRR..",
            ".RRYYRR.",
            "RRRRRRRR",
            "RWRRRRWR",
            "RRRRRRRR",
            ".RRYYRR.",
            ".Y.RR.Y.",
            "Y......Y",
        ],
        [
            "..RRRR..",
            ".RRYYRR.",
            "RRRRRRRR",
            "RRWRRWRR",
            "RRRRRRRR",
            ".YRRRRY.",
            "Y......Y",
            ".Y....Y.",
        ],
    ]
    mushroom_patterns = {
        4: [
            "..PPPP..",
            ".PPWWPP.",
            "PPPPPPPP",
            ".PPPPPP.",
            "...SS...",
            "..SSSS..",
            "..S..S..",
            "........",
        ],
        3: [
            "...PPP..",
            ".PPWWPP.",
            "PPPPPPP.",
            ".PPPPP..",
            "...SS...",
            "..SSSS..",
            "..S..S..",
            "........",
        ],
        2: [
            "...PP...",
            "..PWWP..",
            ".PPPPP..",
            "...PPP..",
            "...SS...",
            "..SS....",
            "..S.....",
            "........",
        ],
        1: [
            "...P....",
            "..PWP...",
            "...PP...",
            "...P....",
            "...SS...",
            "...SS...",
            "...S....",
            "........",
        ],
    }
    bullet_pattern = [
        "Y",
        "W",
        "W",
        "Y",
    ]
    spider_patterns = [
        [
            "B......B",
            ".BB..BB.",
            "BBBBBBBB",
            ".BWWWWB.",
            "BBBBBBBB",
            "B.BBB.BB",
            ".B.BB.B.",
            "B......B",
        ],
        [
            ".B....B.",
            "B.B..B.B",
            "BBBBBBBB",
            ".BWWWWB.",
            "BBBBBBBB",
            ".BB..BB.",
            "B.BBB.B.",
            ".B....B.",
        ],
    ]
    scorpion_pattern = [
        "RRROOOOORRR",
        "RROOOOOOOOR",
        "ROOYYOOYYOO",
        "..OOOOOOOO..",
        "...OO..OO...",
        "...O....O...",
        "..Y......Y..",
        ".Y........Y.",
    ]
    flea_patterns = [
        [
            "...CC...",
            "..CCCC..",
            ".CCWWCC.",
            "..CCCC..",
            "...CC...",
            "..CCCC..",
            ".CCCCCC.",
            "..C..C..",
            "..C..C..",
            ".C....C.",
        ],
        [
            "...CC...",
            "..CWWC..",
            ".CCCCCC.",
            "..CCCC..",
            "...CC...",
            ".CCCCCC.",
            "..CCCC..",
            "..C..C..",
            ".C....C.",
            "C......C",
        ],
    ]

    player_palette = {"G": GREEN, "Y": HUD_GOLD}
    body_palette = {"G": CENTI_BODY_GREEN, "Y": HUD_GOLD}
    head_palette = {"R": CENTI_HEAD_RED, "Y": HUD_GOLD, "W": WHITE}
    mushroom_palette = {"P": MUSHROOM_CAP_PURPLE, "W": MUSHROOM_SPOT, "S": MUSHROOM_STEM}
    poison_palette = {"P": POISON_PURPLE, "W": WHITE, "S": (220, 200, 255)}
    bullet_palette = {"Y": YELLOW, "W": WHITE}
    spider_palette = {"B": BLUE, "W": WHITE}
    scorpion_palette = {"R": DARK_ORANGE, "O": ORANGE, "Y": HUD_GOLD}
    flea_palette = {"C": CYAN, "W": WHITE}

    bank = {}

    player_sprite = make_pixel_sprite(player_pattern, player_palette, scale=PIXEL_SCALE)
    bank["player"] = make_asset_from_sprite(player_sprite, GREEN, alpha=95, scale_factor=1.4)
    bank["life"] = make_asset_from_sprite(
        make_pixel_sprite(player_pattern, player_palette, scale=2),
        GREEN,
        alpha=72,
        scale_factor=1.5,
    )
    bullet_sprite = make_pixel_sprite(bullet_pattern, bullet_palette, scale=3)
    bank["bullet"] = make_asset_from_sprite(bullet_sprite, YELLOW, alpha=108, scale_factor=1.8)

    bank["mushroom"] = {}
    bank["poison_mushroom"] = {}
    for hp, pattern in mushroom_patterns.items():
        mush_sprite = make_pixel_sprite(pattern, mushroom_palette, scale=PIXEL_SCALE)
        poison_sprite = make_pixel_sprite(pattern, poison_palette, scale=PIXEL_SCALE)
        bank["mushroom"][hp] = make_asset_from_sprite(
            mush_sprite,
            MUSHROOM_CAP_PURPLE,
            alpha=80,
            scale_factor=1.45,
        )
        bank["poison_mushroom"][hp] = make_asset_from_sprite(
            poison_sprite,
            POISON_PURPLE,
            alpha=88,
            scale_factor=1.5,
        )

    bank["centipede_body"] = {"right": [], "left": [], "down": []}
    bank["centipede_head"] = {"right": [], "left": [], "down": []}
    for pattern in body_patterns:
        right = make_pixel_sprite(pattern, body_palette, scale=PIXEL_SCALE)
        left = pygame.transform.flip(right, True, False)
        down = pygame.transform.rotate(right, -90)
        bank["centipede_body"]["right"].append(
            make_asset_from_sprite(right, CENTI_BODY_GREEN, alpha=90, scale_factor=1.35)
        )
        bank["centipede_body"]["left"].append(
            make_asset_from_sprite(left, CENTI_BODY_GREEN, alpha=90, scale_factor=1.35)
        )
        bank["centipede_body"]["down"].append(
            make_asset_from_sprite(down, CENTI_BODY_GREEN, alpha=90, scale_factor=1.35)
        )
    for pattern in head_patterns:
        right = make_pixel_sprite(pattern, head_palette, scale=PIXEL_SCALE)
        left = pygame.transform.flip(right, True, False)
        down = pygame.transform.rotate(right, -90)
        bank["centipede_head"]["right"].append(
            make_asset_from_sprite(right, CENTI_HEAD_RED, alpha=95, scale_factor=1.38)
        )
        bank["centipede_head"]["left"].append(
            make_asset_from_sprite(left, CENTI_HEAD_RED, alpha=95, scale_factor=1.38)
        )
        bank["centipede_head"]["down"].append(
            make_asset_from_sprite(down, CENTI_HEAD_RED, alpha=95, scale_factor=1.38)
        )

    bank["spider"] = []
    for pattern in spider_patterns:
        spider_sprite = make_pixel_sprite(pattern, spider_palette, scale=5)
        bank["spider"].append(make_asset_from_sprite(spider_sprite, BLUE, alpha=88, scale_factor=1.32))

    scorpion_sprite = make_pixel_sprite(scorpion_pattern, scorpion_palette, scale=6)
    bank["scorpion"] = {
        "right": make_asset_from_sprite(scorpion_sprite, ORANGE, alpha=88, scale_factor=1.25),
        "left": make_asset_from_sprite(
            pygame.transform.flip(scorpion_sprite, True, False),
            ORANGE,
            alpha=88,
            scale_factor=1.25,
        ),
    }

    bank["flea"] = []
    for pattern in flea_patterns:
        flea_sprite = make_pixel_sprite(pattern, flea_palette, scale=3)
        bank["flea"].append(make_asset_from_sprite(flea_sprite, CYAN, alpha=86, scale_factor=1.3))

    SPRITE_BANK = bank
    return SPRITE_BANK

class Mushroom:
    def __init__(self, grid_x, grid_y):
        self.grid_x = grid_x
        self.grid_y = grid_y
        self.hp = MUSHROOM_HP
        self.poisoned = False
        self.update_rect()

    def update_rect(self):
        self.rect = pygame.Rect(
            self.grid_x * MUSHROOM_SIZE,
            self.grid_y * MUSHROOM_SIZE,
            MUSHROOM_SIZE,
            MUSHROOM_SIZE,
        )

    def hit(self):
        self.hp -= 1
        return self.hp <= 0

    def draw(self, surface):
        bank = get_sprite_bank()
        asset_key = "poison_mushroom" if self.poisoned else "mushroom"
        asset = bank[asset_key][clamp(self.hp, 1, MUSHROOM_HP)]
        draw_asset(surface, asset, self.rect.topleft)


class Player:
    def __init__(self):
        sprite = get_sprite_bank()["player"]["sprite"]
        self.width = sprite.get_width()
        self.height = sprite.get_height()
        self.x = WIDTH // 2
        self.y = HEIGHT - PLAYER_AREA_HEIGHT // 2
        self.speed = PLAYER_SPEED
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.update_rect()

    def update_rect(self):
        self.rect.midbottom = (int(self.x), int(self.y))

    def _clamp(self):
        min_y = HEIGHT - PLAYER_AREA_HEIGHT + 12
        max_y = HEIGHT - 10
        self.y = clamp(self.y, min_y, max_y)
        self.x = clamp(self.x, self.width // 2, WIDTH - self.width // 2)

    def update_mouse(self, mx, my):
        self.x = mx
        self.y = my
        self._clamp()
        self.update_rect()

    def update_keyboard(self, keys):
        dx = dy = 0
        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            dx -= self.speed
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            dx += self.speed
        if keys[pygame.K_w] or keys[pygame.K_UP]:
            dy -= self.speed
        if keys[pygame.K_s] or keys[pygame.K_DOWN]:
            dy += self.speed
        self.x += dx
        self.y += dy
        self._clamp()
        self.update_rect()

    def move_by(self, dx, dy):
        self.x += dx
        self.y += dy
        self._clamp()
        self.update_rect()

    def draw(self, surface):
        draw_asset(surface, get_sprite_bank()["player"], self.rect.topleft)


class Bullet:
    def __init__(self, x, y):
        sprite = get_sprite_bank()["bullet"]["sprite"]
        self.width = sprite.get_width()
        self.height = sprite.get_height()
        self.x = x
        self.y = y
        self.speed = BULLET_SPEED
        self.rect = pygame.Rect(0, 0, self.width, self.height)
        self.update_rect()

    def update_rect(self):
        self.rect.center = (int(self.x), int(self.y))

    def update(self):
        self.y += self.speed
        self.update_rect()

    def off_screen(self):
        return self.rect.bottom < 0

    def draw(self, surface):
        draw_asset(surface, get_sprite_bank()["bullet"], self.rect.center, centered=True)


class CentipedeSegment:
    def __init__(self, x, y):
        self.size = SEGMENT_SIZE
        self.x = x
        self.y = y
        self.rect = pygame.Rect(int(self.x), int(self.y), self.size, self.size)

    def set_position(self, x, y):
        self.x = x
        self.y = y
        self.update_rect()

    def update_rect(self):
        self.rect.topleft = (int(round(self.x)), int(round(self.y)))

    def draw(self, surface, head=False, frame=0, index=0, direction=1, vertical=False):
        bank = get_sprite_bank()
        family = "centipede_head" if head else "centipede_body"
        orientation = "down" if vertical else ("right" if direction >= 0 else "left")
        asset = bank[family][orientation][(frame // 6 + index) % 2]
        draw_asset(surface, asset, self.rect.topleft)


class Centipede:
    def __init__(
        self,
        length,
        head_x,
        head_y,
        direction=1,
        base_speed=1.1,
        max_extra_speed=CENTIPEDE_MAX_EXTRA_SPEED,
        cells=None,
        next_cells=None,
        progress=0.0,
        dive=False,
        initial_length=None,
    ):
        self.direction = 1 if direction >= 0 else -1
        self.base_speed = base_speed
        self.max_extra_speed = max_extra_speed
        self.initial_length = initial_length or max(1, length)
        self.speed = self.base_speed
        self.dive = dive
        self.progress = progress

        if cells is None:
            head_col = int(round(head_x / SEGMENT_SIZE))
            head_row = int(round(head_y / SEGMENT_SIZE))
            cells = [
                (head_col - i * self.direction, head_row)
                for i in range(length)
            ]

        self.cells = list(cells)
        self.next_cells = list(next_cells) if next_cells is not None else list(self.cells)
        self.segments = [CentipedeSegment(0, 0) for _ in self.cells]

        self.recalc_speed()
        if self.cells and self.next_cells == self.cells:
            self._prepare_next_cells([])
        self.sync_segment_positions()

    def is_empty(self):
        return len(self.cells) == 0

    def _ensure_segments(self):
        if len(self.segments) != len(self.cells):
            self.segments = [CentipedeSegment(0, 0) for _ in self.cells]

    def recalc_speed(self):
        if not self.cells:
            return
        if self.initial_length <= 1:
            self.speed = self.base_speed + self.max_extra_speed
            return
        fraction = (self.initial_length - len(self.cells)) / (self.initial_length - 1)
        extra = self.max_extra_speed * max(0.0, fraction)
        self.speed = self.base_speed + extra

    def _bottom_limit_row(self):
        return (HEIGHT - SEGMENT_SIZE - PLAYER_AREA_HEIGHT // 2) // SEGMENT_SIZE

    def _head_target_cell(self, mushrooms):
        head_col, head_row = self.cells[0]
        bottom_row = self._bottom_limit_row()
        mushroom_map = {(m.grid_x, m.grid_y): m for m in mushrooms}

        if self.dive:
            if head_row < bottom_row:
                return head_col, min(bottom_row, head_row + 1)
            self.dive = False

        next_col = head_col + self.direction
        hit_edge = next_col < 0 or next_col >= GRID_COLS
        hit_mushroom = mushroom_map.get((next_col, head_row))

        if hit_mushroom and hit_mushroom.poisoned:
            self.dive = True
            return head_col, min(bottom_row, head_row + 1)

        if hit_edge or hit_mushroom:
            self.direction *= -1
            if head_row >= bottom_row:
                return head_col, head_row
            return head_col, min(bottom_row, head_row + 1)

        return next_col, head_row

    def _prepare_next_cells(self, mushrooms):
        if not self.cells:
            self.next_cells = []
            return
        next_head = self._head_target_cell(mushrooms)
        self.next_cells = [next_head] + self.cells[:-1]

    def sync_segment_positions(self):
        self._ensure_segments()
        for idx, seg in enumerate(self.segments):
            cur_col, cur_row = self.cells[idx]
            if idx < len(self.next_cells):
                next_col, next_row = self.next_cells[idx]
            else:
                next_col, next_row = cur_col, cur_row
            seg.set_position(
                lerp(cur_col, next_col, self.progress) * SEGMENT_SIZE,
                lerp(cur_row, next_row, self.progress) * SEGMENT_SIZE,
            )

    def update(self, mushrooms):
        if not self.cells:
            return

        self.recalc_speed()
        self.progress += self.speed / SEGMENT_SIZE

        while self.progress >= 1.0 and self.cells:
            self.cells = list(self.next_cells)
            self.progress -= 1.0
            self._prepare_next_cells(mushrooms)

        self.sync_segment_positions()

    def handle_bullet_collision(self, bullet, mushrooms, score_ref):
        for i, seg in enumerate(self.segments):
            if not bullet.rect.colliderect(seg.rect):
                continue

            grid_x = clamp(int(round(seg.x / MUSHROOM_SIZE)), 0, GRID_COLS - 1)
            grid_y = clamp(int(round(seg.y / MUSHROOM_SIZE)), 0, GRID_ROWS - 1)
            if not any(m.grid_x == grid_x and m.grid_y == grid_y for m in mushrooms):
                mushrooms.append(Mushroom(grid_x, grid_y))

            score_ref[0] += HEAD_SCORE if i == 0 else BODY_SCORE

            tail_cells = self.cells[i + 1:]
            tail_next = self.next_cells[i + 1:] if i + 1 < len(self.next_cells) else []

            self.cells = self.cells[:i]
            self.next_cells = self.next_cells[:i]
            self.segments = self.segments[:i]
            self.recalc_speed()
            self.sync_segment_positions()

            new_centipede = None
            if tail_cells:
                new_centipede = Centipede(
                    0,
                    0,
                    0,
                    direction=self.direction,
                    base_speed=self.base_speed,
                    max_extra_speed=self.max_extra_speed,
                    cells=tail_cells,
                    next_cells=tail_next if tail_next else list(tail_cells),
                    progress=self.progress,
                    dive=self.dive,
                    initial_length=len(tail_cells),
                )

            return True, new_centipede
        return False, None

    def draw(self, surface, frame=0):
        for idx, seg in enumerate(self.segments):
            cur = self.cells[idx]
            nxt = self.next_cells[idx] if idx < len(self.next_cells) else cur
            vertical = cur[0] == nxt[0] and cur[1] != nxt[1]
            if nxt[0] == cur[0]:
                direction = self.direction
            else:
                direction = 1 if nxt[0] > cur[0] else -1
            seg.draw(
                surface,
                head=(idx == 0),
                frame=frame,
                index=idx,
                direction=direction,
                vertical=vertical,
            )


class Spider:
    def __init__(self):
        sprite = get_sprite_bank()["spider"][0]["sprite"]
        self.size = sprite.get_width()
        self.y = HEIGHT - PLAYER_AREA_HEIGHT - 60 + random.randint(-40, 40)
        self.y = clamp(self.y, 0, HEIGHT - PLAYER_AREA_HEIGHT - self.size)
        self.rect = pygame.Rect(0, self.y, self.size, self.size)

        if random.random() < 0.5:
            self.x = -self.size
            self.vx = random.uniform(SPIDER_SPEED_MIN, SPIDER_SPEED_MAX)
        else:
            self.x = WIDTH
            self.vx = -random.uniform(SPIDER_SPEED_MIN, SPIDER_SPEED_MAX)

        vy_mag = random.uniform(2.0, 3.8)
        self.vy = vy_mag if random.random() < 0.5 else -vy_mag

    def update(self):
        self.x += self.vx
        self.y += self.vy

        top_band = HEIGHT - PLAYER_AREA_HEIGHT - 140
        bottom_band = HEIGHT - PLAYER_AREA_HEIGHT - 10

        if self.y < top_band:
            self.y = top_band
            self.vy = abs(self.vy)
        elif self.y > bottom_band:
            self.y = bottom_band
            self.vy = -abs(self.vy)

        # Slight randomization of vertical speed to approximate irregular zig-zag
        if random.random() < 0.03:
            vy_mag = random.uniform(2.0, 3.8)
            self.vy = vy_mag if self.vy >= 0 else -vy_mag

        self.rect.topleft = (int(self.x), int(self.y))

    def off_screen(self):
        return self.x < -self.size - 10 or self.x > WIDTH + 10

    def draw(self, surface):
        asset = get_sprite_bank()["spider"][(pygame.time.get_ticks() // 90) % 2]
        draw_asset(surface, asset, self.rect.topleft)


class Scorpion:
    def __init__(self):
        sprite = get_sprite_bank()["scorpion"]["right"]["sprite"]
        self.width = sprite.get_width()
        self.height = sprite.get_height()

        mid_row = random.randint(4, GRID_ROWS - 10)
        self.y = mid_row * SEGMENT_SIZE

        if random.random() < 0.5:
            self.x = -self.width
            self.vx = SCORPION_SPEED
        else:
            self.x = WIDTH
            self.vx = -SCORPION_SPEED

        self.rect = pygame.Rect(int(self.x), int(self.y), self.width, self.height)

    def update(self, mushrooms):
        self.x += self.vx
        self.rect.topleft = (int(self.x), int(self.y))

        for m in mushrooms:
            if self.rect.colliderect(m.rect):
                m.poisoned = True

    def off_screen(self):
        return self.x < -self.width - 10 or self.x > WIDTH + 10

    def draw(self, surface):
        orientation = "right" if self.vx > 0 else "left"
        draw_asset(surface, get_sprite_bank()["scorpion"][orientation], self.rect.topleft)


class Flea:
    """
    Drops straight down; when mushrooms in player area are low,
    fleas appear and leave mushrooms behind them in columns.
    """
    def __init__(self):
        sprite = get_sprite_bank()["flea"][0]["sprite"]
        self.width = sprite.get_width()
        self.height = sprite.get_height()
        self.size = SEGMENT_SIZE
        grid_x = random.randint(0, GRID_COLS - 1)
        self.x = grid_x * SEGMENT_SIZE
        self.y = -self.height
        self.vy = FLEA_SPEED
        self.hp = 2  # two hits, like the original
        self.rect = pygame.Rect(int(self.x), int(self.y), self.width, self.height)
        self.last_grid_y = -1

    def update(self, mushrooms):
        self.y += self.vy
        self.rect.topleft = (int(self.x), int(self.y))

        grid_x = self.rect.centerx // MUSHROOM_SIZE
        grid_y = self.rect.centery // MUSHROOM_SIZE

        if grid_y != self.last_grid_y and 0 <= grid_y < GRID_ROWS:
            self.last_grid_y = grid_y
            if random.random() < FLEA_MUSHROOM_CHANCE_PER_ROW:
                for m in mushrooms:
                    if m.grid_x == grid_x and m.grid_y == grid_y:
                        break
                else:
                    mushrooms.append(Mushroom(grid_x, grid_y))

    def hit(self):
        self.hp -= 1
        return self.hp <= 0

    def off_screen(self):
        return self.y > HEIGHT + self.height

    def draw(self, surface):
        asset = get_sprite_bank()["flea"][(pygame.time.get_ticks() // 100) % 2]
        draw_asset(surface, asset, self.rect.topleft)


class FlashEffect:
    def __init__(self, x, y, color, life=10, radius=14):
        self.x = x
        self.y = y
        self.color = color
        self.life = life
        self.max_life = life
        self.radius = radius

    def update(self):
        self.life -= 1
        self.radius += 1.25
        return self.life > 0

    def draw(self, surface):
        alpha = int(255 * (self.life / max(1, self.max_life)))
        size = max(24, int(self.radius * 3))
        temp = pygame.Surface((size, size), pygame.SRCALPHA)
        center = size // 2
        pygame.draw.circle(temp, (*self.color, alpha), (center, center), int(self.radius), 2)
        pygame.draw.circle(temp, (*WHITE, alpha // 2), (center, center), max(2, int(self.radius * 0.35)), 1)
        surface.blit(temp, (self.x - center, self.y - center))


# ---------- GAME LOGIC ----------

class CentipedeGame:
    def __init__(self):
        self.logical_size = (WIDTH, HEIGHT)
        self.display_size = self.logical_size
        self.surface = pygame.Surface(self.logical_size)

        self.fullscreen = False
        self.screen = pygame.display.set_mode(self.logical_size)
        pygame.display.set_caption("Centipede Arcade-ish Clone")
        self.update_scale_factors()

        self.clock = pygame.time.Clock()
        self.running = True

        self.control_mode = "mouse"

        pygame.joystick.init()
        if pygame.joystick.get_count() > 0:
            self.joystick = pygame.joystick.Joystick(0)
            self.joystick.init()
        else:
            self.joystick = None

        self.high_score = 0
        self.mode = "attract"  # "attract" or "game"
        self.last_input_ms = pygame.time.get_ticks()
        self.frame_count = 0
        self.effects = []
        self.screen_shake_frames = 0
        self.screen_shake_strength = 0
        self.game_over_image = None

        self.init_sounds()
        self.create_crt_overlay()
        self.load_title_image()
        self.create_playfield_layers()
        self.init_state_for_game()
        self.setup_attract()

    def update_scale_factors(self):
        dw, dh = self.display_size
        lw, lh = self.logical_size

        if lw == 0 or lh == 0:
            self.scale = 1.0
            self.render_size = self.logical_size
            self.render_offset = (0, 0)
            return

        scale = min(dw / lw, dh / lh)
        if scale <= 0:
            scale = 1.0

        self.scale = scale
        scaled_w = int(lw * scale)
        scaled_h = int(lh * scale)
        self.render_size = (scaled_w, scaled_h)

        offset_x = (dw - scaled_w) // 2
        offset_y = (dh - scaled_h) // 2
        self.render_offset = (offset_x, offset_y)

    def get_logical_mouse_pos(self):
        mx, my = pygame.mouse.get_pos()
        ox, oy = self.render_offset
        mx -= ox
        my -= oy
        if self.scale != 0:
            mx /= self.scale
            my /= self.scale
        return mx, my

    def init_sounds(self):
        try:
            self.snd_shoot = generate_tone(
                freq=1800,
                duration=0.07,
                volume=0.35,
                waveform="triangle",
                attack=0.002,
                release=0.03,
            )
            self.snd_hit_segment = generate_tone(
                freq=900,
                duration=0.06,
                volume=0.4,
                waveform="sine",
                attack=0.003,
                release=0.04,
            )
            self.snd_hit_spider = generate_tone(
                freq=700,
                duration=0.09,
                volume=0.45,
                waveform="triangle",
                attack=0.004,
                release=0.06,
            )
            self.snd_hit_flea = generate_tone(
                freq=750,
                duration=0.08,
                volume=0.4,
                waveform="sine",
                attack=0.003,
                release=0.05,
            )
            self.snd_hit_scorpion = generate_gliss(
                start_freq=1000,
                end_freq=1500,
                duration=0.12,
                volume=0.4,
                waveform="triangle",
            )
            self.snd_death = generate_gliss(
                start_freq=700,
                end_freq=120,
                duration=0.4,
                volume=0.6,
                waveform="sine",
            )
            self.snd_level_start = generate_gliss(
                start_freq=600,
                end_freq=1200,
                duration=0.25,
                volume=0.4,
                waveform="sine",
            )
            self.snd_march = generate_tone(
                freq=260,
                duration=0.04,
                volume=0.18,
                waveform="square",
                attack=0.003,
                release=0.02,
            )
        except Exception:
            self.snd_shoot = None
            self.snd_hit_segment = None
            self.snd_hit_spider = None
            self.snd_hit_flea = None
            self.snd_hit_scorpion = None
            self.snd_death = None
            self.snd_level_start = None
            self.snd_march = None

        self.last_march_cell = None

    def create_crt_overlay(self):
        self.crt_overlay = pygame.Surface(self.logical_size, pygame.SRCALPHA)
        for y in range(0, HEIGHT, 4):
            pygame.draw.line(self.crt_overlay, (0, 0, 0, 34), (0, y), (WIDTH, y))
        for inset in range(20):
            alpha = min(90, 4 + inset * 3)
            pygame.draw.rect(
                self.crt_overlay,
                (0, 0, 0, alpha),
                pygame.Rect(inset, inset, WIDTH - inset * 2, HEIGHT - inset * 2),
                1,
            )
        pygame.draw.line(
            self.crt_overlay,
            (40, 120, 40, 20),
            (0, HUD_BAR_HEIGHT + 1),
            (WIDTH, HUD_BAR_HEIGHT + 1),
            2,
        )

    def load_title_image(self):
        self.title_image = None
        try:
            img = pygame.image.load(os.path.join(SCRIPT_DIR, "centipede_logo.png")).convert_alpha()
            max_width = int(WIDTH * 0.85)
            scale = min(max_width / img.get_width(), 1.0)
            new_size = (int(img.get_width() * scale), int(img.get_height() * scale))
            self.title_image = pygame.transform.smoothscale(img, new_size)
        except Exception as e:
            print("Could not load centipede_logo.png:", e)
            self.title_image = None

        try:
            game_over = pygame.image.load(os.path.join(SCRIPT_DIR, "Game Over.jpg")).convert()
            scale = min((WIDTH * 0.62) / game_over.get_width(), 1.0)
            size = (int(game_over.get_width() * scale), int(game_over.get_height() * scale))
            self.game_over_image = pygame.transform.scale(game_over, size)
        except Exception:
            self.game_over_image = None

    def create_playfield_layers(self):
        rng = random.Random(1981)
        self.playfield_backdrop = pygame.Surface(self.logical_size)
        self.playfield_backdrop.fill((0, 0, 3))

        hud_panel = pygame.Surface((WIDTH, HUD_BAR_HEIGHT), pygame.SRCALPHA)
        hud_panel.fill((0, 12, 0, 230))
        pygame.draw.line(hud_panel, HUD_GREEN, (0, HUD_BAR_HEIGHT - 2), (WIDTH, HUD_BAR_HEIGHT - 2), 2)
        self.playfield_backdrop.blit(hud_panel, (0, 0))

        for _ in range(160):
            x = rng.randrange(0, WIDTH)
            y = rng.randrange(HUD_BAR_HEIGHT + 2, HEIGHT - 10)
            color = rng.choice(STAR_COLORS)
            self.playfield_backdrop.set_at((x, y), color)
            if rng.random() < 0.28 and x + 1 < WIDTH:
                glow_color = tuple(min(255, c + 35) for c in color)
                self.playfield_backdrop.set_at((x + 1, y), glow_color)

        player_top = HEIGHT - PLAYER_AREA_HEIGHT
        player_area = pygame.Surface((WIDTH, PLAYER_AREA_HEIGHT), pygame.SRCALPHA)
        player_area.fill((0, 20, 8, 26))
        for row in range(0, PLAYER_AREA_HEIGHT, SEGMENT_SIZE):
            alpha = 18 if (row // SEGMENT_SIZE) % 2 == 0 else 10
            pygame.draw.line(player_area, (30, 90, 35, alpha), (0, row), (WIDTH, row), 1)
        self.playfield_backdrop.blit(player_area, (0, player_top))

        for x in range(0, WIDTH, SEGMENT_SIZE):
            color = HUD_GOLD if (x // SEGMENT_SIZE) % 2 == 0 else HUD_GREEN
            pygame.draw.line(
                self.playfield_backdrop,
                color,
                (x, player_top),
                (min(WIDTH, x + SEGMENT_SIZE // 2), player_top),
                2,
            )

    def init_state_for_game(self):
        self.player = Player()
        self.bullets = []
        self.mushrooms = []
        self.centipedes = []
        self.spiders = []
        self.scorpions = []
        self.fleas = []
        self.effects = []
        self.level = 1
        self.score = 0
        self.lives = 3
        self.next_extra_life_score = EXTRA_LIFE_SCORE
        self.ready_timer = READY_FRAMES
        self.game_over = False

    def level_params(self, level):
        idx = min(max(level, 1), len(LEVEL_TABLE)) - 1
        _, cells_per_second, mush_density, spawn_mult = LEVEL_TABLE[idx]
        speed_px_per_frame = cells_per_second * SEGMENT_SIZE / FPS
        return speed_px_per_frame, mush_density, spawn_mult

    def level_centipede_length(self):
        cycle = (self.level - 1) % INITIAL_CENTIPEDE_LENGTH
        return max(1, INITIAL_CENTIPEDE_LENGTH - cycle)

    def detached_head_count(self):
        return (self.level - 1) % INITIAL_CENTIPEDE_LENGTH

    def reset_game_full(self):
        self.init_state_for_game()
        self.generate_mushrooms()
        self.spawn_initial_centipede()
        if self.snd_level_start:
            self.snd_level_start.play()

    def advance_level(self):
        self.level += 1
        self.player = Player()
        self.bullets = []
        self.mushrooms = []
        self.centipedes = []
        self.spiders = []
        self.scorpions = []
        self.fleas = []
        self.effects = []
        self.ready_timer = READY_FRAMES
        self.generate_mushrooms()
        self.spawn_initial_centipede()
        if self.snd_level_start:
            self.snd_level_start.play()

    def setup_attract(self):
        self.attract_angle = 0.0
        self.effects = []
        self.attract_mushrooms = []
        for row in range(4, GRID_ROWS - 4):
            for col in range(GRID_COLS):
                if random.random() < 0.03:
                    self.attract_mushrooms.append(Mushroom(col, row))

        length = 10
        head_x = (length - 1) * SEGMENT_SIZE
        head_y = SEGMENT_SIZE * 3
        speed_px, _, _ = self.level_params(1)
        self.attract_centipede = Centipede(
            length=length,
            head_x=head_x,
            head_y=head_y,
            direction=1,
            base_speed=0.7 * speed_px,
            max_extra_speed=0.3,
        )
        self.attract_player = Player()
        self.attract_player.y = HEIGHT - PLAYER_AREA_HEIGHT // 2
        self.attract_player.update_rect()
        self.attract_bullets = []

        self.attract_last_shot_ms = pygame.time.get_ticks()
        self.attract_shot_interval_ms = 540

    def update_attract(self):
        self.attract_angle += 0.03
        self.update_effects()

        now = pygame.time.get_ticks()
        osc_center = WIDTH // 2
        osc_ampl = WIDTH // 3
        self.attract_player.x = int(osc_center + osc_ampl * math.sin(self.attract_angle * 0.7))
        self.attract_player.y = HEIGHT - PLAYER_AREA_HEIGHT // 2
        self.attract_player.update_rect()

        if now - self.attract_last_shot_ms > self.attract_shot_interval_ms:
            self.attract_last_shot_ms = now
            if len(self.attract_bullets) == 0:
                b = Bullet(self.attract_player.x, self.attract_player.y - 10)
                self.attract_bullets.append(b)
                if self.snd_shoot:
                    self.snd_shoot.play()

        for b in self.attract_bullets[:]:
            b.update()
            if b.off_screen():
                self.attract_bullets.remove(b)

        if self.attract_centipede and not self.attract_centipede.is_empty():
            self.attract_centipede.update(self.attract_mushrooms)
        else:
            length = 10
            head_x = (length - 1) * SEGMENT_SIZE
            head_y = SEGMENT_SIZE * 3
            speed_px, _, _ = self.level_params(1)
            self.attract_centipede = Centipede(
                length=length,
                head_x=head_x,
                head_y=head_y,
                direction=1,
                base_speed=0.7 * speed_px,
                max_extra_speed=0.3,
            )

        for b in self.attract_bullets[:]:
            if self.attract_centipede and not self.attract_centipede.is_empty():
                hit, new_cent = self.attract_centipede.handle_bullet_collision(
                    b, self.attract_mushrooms, [0]
                )
                if hit:
                    if self.snd_hit_segment:
                        self.snd_hit_segment.play()
                    self.spawn_flash(b.rect.centerx, b.rect.centery, HUD_GREEN, life=12, radius=12)
                    if new_cent and not new_cent.is_empty():
                        pass
                    if b in self.attract_bullets:
                        self.attract_bullets.remove(b)

    def generate_mushrooms(self):
        self.mushrooms.clear()
        _, density, _ = self.level_params(self.level)
        for row in range(2, GRID_ROWS - 2):
            for col in range(GRID_COLS):
                if random.random() < density:
                    self.mushrooms.append(Mushroom(col, row))

    def spawn_initial_centipede(self):
        length = self.level_centipede_length()
        centipede_speed, _, _ = self.level_params(self.level)
        self.centipedes.clear()

        main_row = 0 if self.level == 1 else random.randint(0, 3)
        main_direction = 1 if self.level % 2 else -1
        if main_direction > 0:
            head_x = (length - 1) * SEGMENT_SIZE
        else:
            head_x = WIDTH - SEGMENT_SIZE - (length - 1) * SEGMENT_SIZE
        self.centipedes.append(
            Centipede(
                length=length,
                head_x=head_x,
                head_y=(main_row + 2) * SEGMENT_SIZE,
                direction=main_direction,
                base_speed=centipede_speed,
                max_extra_speed=CENTIPEDE_MAX_EXTRA_SPEED,
            )
        )

        detached_heads = self.detached_head_count()
        for idx in range(detached_heads):
            direction = 1 if idx % 2 == 0 else -1
            row = idx % 4
            head_x = 0 if direction > 0 else WIDTH - SEGMENT_SIZE
            self.centipedes.append(
                Centipede(
                    length=1,
                    head_x=head_x,
                    head_y=(row + 2) * SEGMENT_SIZE,
                    direction=direction,
                    base_speed=centipede_speed + 0.9,
                    max_extra_speed=CENTIPEDE_MAX_EXTRA_SPEED + 0.6,
                )
            )

        self.last_march_cell = None

    def spawn_spider(self):
        self.spiders.append(Spider())

    def spawn_scorpion(self):
        self.scorpions.append(Scorpion())

    def spawn_flea(self):
        self.fleas.append(Flea())

    def spawn_flash(self, x, y, color, life=10, radius=14):
        self.effects.append(FlashEffect(x, y, color, life=life, radius=radius))

    def update_effects(self):
        self.effects = [effect for effect in self.effects if effect.update()]

    def draw_effects(self, surface):
        for effect in self.effects:
            effect.draw(surface)

    def start_shake(self, frames=8, strength=4):
        self.screen_shake_frames = max(self.screen_shake_frames, frames)
        self.screen_shake_strength = max(self.screen_shake_strength, strength)

    def check_extra_life(self):
        gained = False
        while self.score >= self.next_extra_life_score:
            self.lives += 1
            self.next_extra_life_score += EXTRA_LIFE_SCORE
            gained = True
        if gained:
            self.spawn_flash(WIDTH - 80, HUD_BAR_HEIGHT // 2, HUD_GOLD, life=18, radius=18)
            self.start_shake(6, 3)

    def restore_mushrooms_after_death(self):
        restored = 0
        for mushroom in self.mushrooms:
            if mushroom.poisoned or mushroom.hp < MUSHROOM_HP:
                mushroom.poisoned = False
                mushroom.hp = MUSHROOM_HP
                restored += 1
        if restored:
            self.score += restored * MUSHROOM_RESTORE_BONUS
            self.check_extra_life()

    def run(self):
        while self.running:
            self.clock.tick(FPS)
            self.frame_count += 1
            self.handle_events()

            if self.mode == "attract":
                self.update_attract()
            else:
                self.update_game()

            self.draw()

        pygame.quit()
        sys.exit()

    def toggle_fullscreen(self):
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            info = pygame.display.Info()
            self.display_size = (info.current_w, info.current_h)
            self.screen = pygame.display.set_mode(self.display_size, pygame.FULLSCREEN)
        else:
            self.display_size = self.logical_size
            self.screen = pygame.display.set_mode(self.logical_size)
        self.update_scale_factors()

    def cycle_control_mode(self):
        if self.control_mode == "mouse":
            self.control_mode = "keyboard"
        elif self.control_mode == "keyboard":
            self.control_mode = "gamepad"
        else:
            self.control_mode = "mouse"

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                self.last_input_ms = pygame.time.get_ticks()

                if event.key == pygame.K_ESCAPE:
                    self.running = False
                elif event.key == pygame.K_RETURN:
                    # ALT+Enter toggles fullscreen, plain Enter controls start/restart
                    if event.mod & pygame.KMOD_ALT:
                        self.toggle_fullscreen()
                    else:
                        if self.mode == "attract":
                            self.mode = "game"
                            self.reset_game_full()
                        elif self.game_over:
                            self.mode = "game"
                            self.reset_game_full()
                elif event.key == pygame.K_F1:
                    self.cycle_control_mode()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.last_input_ms = pygame.time.get_ticks()
                if (
                    event.button == 1
                    and self.mode == "game"
                    and not self.game_over
                    and self.ready_timer == 0
                ):
                    if len(self.bullets) == 0:
                        bullet = Bullet(self.player.x, self.player.y - 10)
                        self.bullets.append(bullet)
                        if self.snd_shoot:
                            self.snd_shoot.play()
                elif event.button == 1 and self.mode == "attract":
                    self.mode = "game"
                    self.reset_game_full()
            elif event.type == pygame.MOUSEMOTION:
                self.last_input_ms = pygame.time.get_ticks()

        if self.mode == "game" and not self.game_over and self.ready_timer == 0:
            keys = pygame.key.get_pressed()
            if keys[pygame.K_SPACE]:
                if len(self.bullets) == 0:
                    bullet = Bullet(self.player.x, self.player.y - 10)
                    self.bullets.append(bullet)
                    if self.snd_shoot:
                        self.snd_shoot.play()

    def update_game(self):
        self.update_effects()

        if self.game_over:
            now = pygame.time.get_ticks()
            if now - self.last_input_ms > IDLE_TIMEOUT_MS:
                self.mode = "attract"
                self.setup_attract()
            return

        now = pygame.time.get_ticks()
        if now - self.last_input_ms > IDLE_TIMEOUT_MS:
            self.mode = "attract"
            self.setup_attract()
            return

        if self.ready_timer > 0:
            self.ready_timer -= 1
            return

        # Player movement
        if self.control_mode == "mouse":
            mx_log, my_log = self.get_logical_mouse_pos()
            self.player.update_mouse(mx_log, my_log)
        elif self.control_mode == "keyboard":
            keys = pygame.key.get_pressed()
            self.player.update_keyboard(keys)
        elif self.control_mode == "gamepad" and self.joystick:
            axis_x = self.joystick.get_axis(0)
            axis_y = self.joystick.get_axis(1)
            deadzone = 0.15
            if abs(axis_x) < deadzone:
                axis_x = 0
            if abs(axis_y) < deadzone:
                axis_y = 0
            dx = axis_x * self.player.speed * 1.3
            dy = axis_y * self.player.speed * 1.3
            self.player.move_by(dx, dy)
        else:
            mx_log, my_log = self.get_logical_mouse_pos()
            self.player.update_mouse(mx_log, my_log)

        # Bullets
        for b in self.bullets[:]:
            b.update()
            if b.off_screen():
                self.bullets.remove(b)

        # Centipedes
        for c in self.centipedes:
            c.update(self.mushrooms)
        self.centipedes = [c for c in self.centipedes if not c.is_empty()]

        # Centipede "march" sound keyed to head grid column
        if self.centipedes and self.centipedes[0].segments and self.snd_march:
            head = self.centipedes[0].segments[0]
            cell_x = head.rect.x // SEGMENT_SIZE
            if self.last_march_cell is None or cell_x != self.last_march_cell:
                self.snd_march.play()
                self.last_march_cell = cell_x

        # Spawns
        _, _, spawn_mult = self.level_params(self.level)

        if len(self.spiders) < 1 and random.random() < SPIDER_SPAWN_BASE * spawn_mult:
            self.spawn_spider()

        if len(self.scorpions) < 1 and random.random() < SCORPION_SPAWN_BASE * spawn_mult:
            self.spawn_scorpion()

        mushrooms_in_player_area = sum(
            1 for m in self.mushrooms if m.rect.bottom > HEIGHT - PLAYER_AREA_HEIGHT
        )
        if mushrooms_in_player_area < FLEA_MIN_MUSHROOMS_PLAYER_AREA:
            if len(self.fleas) < 2 and random.random() < FLEA_SPAWN_BASE * spawn_mult:
                self.spawn_flea()

        # Spider updates + mushroom cleanup
        for s in self.spiders[:]:
            s.update()
            if s.off_screen():
                self.spiders.remove(s)
            else:
                # Spider eats mushrooms it passes over, mostly near bottom rows
                for m in self.mushrooms[:]:
                    if s.rect.colliderect(m.rect):
                        self.mushrooms.remove(m)

        # Scorpions
        for sc in self.scorpions[:]:
            sc.update(self.mushrooms)
            if sc.off_screen():
                self.scorpions.remove(sc)

        # Fleas
        for f in self.fleas[:]:
            f.update(self.mushrooms)
            if f.off_screen():
                self.fleas.remove(f)

        # Bullet vs mushrooms
        for b in self.bullets[:]:
            hit_any = False
            for m in self.mushrooms[:]:
                if b.rect.colliderect(m.rect):
                    hit_any = True
                    destroyed = m.hit()
                    if destroyed:
                        self.mushrooms.remove(m)
                        self.score += MUSHROOM_DESTROY_SCORE
                    self.spawn_flash(m.rect.centerx, m.rect.centery, MUSHROOM_CAP_PURPLE, life=8, radius=10)
                    if self.snd_hit_segment:
                        self.snd_hit_segment.play()
                    break
            if hit_any and b in self.bullets:
                self.bullets.remove(b)

        # Bullet vs centipede segments
        score_ref = [self.score]
        for b in self.bullets[:]:
            bullet_hit = False
            for c in self.centipedes[:]:
                hit, new_cent = c.handle_bullet_collision(b, self.mushrooms, score_ref)
                if hit:
                    bullet_hit = True
                    if self.snd_hit_segment:
                        self.snd_hit_segment.play()
                    self.spawn_flash(b.rect.centerx, b.rect.centery, HUD_GREEN, life=12, radius=13)
                    if new_cent and not new_cent.is_empty():
                        self.centipedes.append(new_cent)
                    if c.is_empty() and c in self.centipedes:
                        self.centipedes.remove(c)
                    break
            if bullet_hit and b in self.bullets:
                self.bullets.remove(b)
        self.score = score_ref[0]

        if self.score > self.high_score:
            self.high_score = self.score

        # Bullet vs spiders
        for b in self.bullets[:]:
            for s in self.spiders[:]:
                if b.rect.colliderect(s.rect):
                    if s.rect.y < HEIGHT - PLAYER_AREA_HEIGHT - 80:
                        pts = SPIDER_SCORE_LOW
                    elif s.rect.y < HEIGHT - PLAYER_AREA_HEIGHT - 30:
                        pts = SPIDER_SCORE_MID
                    else:
                        pts = SPIDER_SCORE_HIGH
                    self.score += pts
                    if self.snd_hit_spider:
                        self.snd_hit_spider.play()
                    self.spawn_flash(s.rect.centerx, s.rect.centery, BLUE, life=14, radius=16)
                    self.start_shake(4, 2)
                    if s in self.spiders:
                        self.spiders.remove(s)
                    if b in self.bullets:
                        self.bullets.remove(b)
                    break

        # Bullet vs fleas
        for b in self.bullets[:]:
            for f in self.fleas[:]:
                if b.rect.colliderect(f.rect):
                    dead = f.hit()
                    if self.snd_hit_flea:
                        self.snd_hit_flea.play()
                    self.spawn_flash(f.rect.centerx, f.rect.centery, CYAN, life=10, radius=12)
                    if dead:
                        self.score += FLEA_SCORE
                        if f in self.fleas:
                            self.fleas.remove(f)
                    if b in self.bullets:
                        self.bullets.remove(b)
                    break

        # Bullet vs scorpions
        for b in self.bullets[:]:
            for sc in self.scorpions[:]:
                if b.rect.colliderect(sc.rect):
                    self.score += SCORPION_SCORE
                    if self.snd_hit_scorpion:
                        self.snd_hit_scorpion.play()
                    self.spawn_flash(sc.rect.centerx, sc.rect.centery, ORANGE, life=16, radius=18)
                    self.start_shake(5, 3)
                    if sc in self.scorpions:
                        self.scorpions.remove(sc)
                    if b in self.bullets:
                        self.bullets.remove(b)
                    break

        if self.score > self.high_score:
            self.high_score = self.score
        self.check_extra_life()

        # Player vs hostiles
        for c in self.centipedes:
            for seg in c.segments:
                if self.player.rect.colliderect(seg.rect):
                    self.lose_life()
                    return

        for s in self.spiders:
            if self.player.rect.colliderect(s.rect):
                self.lose_life()
                return

        for f in self.fleas:
            if self.player.rect.colliderect(f.rect):
                self.lose_life()
                return

        for sc in self.scorpions:
            if self.player.rect.colliderect(sc.rect):
                self.lose_life()
                return

        # Level complete?
        if not self.centipedes:
            self.advance_level()

    def lose_life(self):
        self.lives -= 1
        self.spawn_flash(self.player.rect.centerx, self.player.rect.centery, HUD_RED, life=20, radius=22)
        self.start_shake(12, 8)
        if self.snd_death:
            self.snd_death.play()

        self.restore_mushrooms_after_death()

        if self.lives <= 0:
            self.game_over = True
            return

        self.bullets.clear()
        self.spiders.clear()
        self.scorpions.clear()
        self.fleas.clear()
        self.centipedes.clear()
        self.effects.clear()
        self.player = Player()
        self.ready_timer = READY_FRAMES
        self.spawn_initial_centipede()

    def update_mouse_visibility(self):
        if self.mode == "game" and not self.game_over:
            pygame.mouse.set_visible(False)
        else:
            pygame.mouse.set_visible(True)

    def draw_hud(self, surface):
        pygame.draw.rect(surface, (0, 0, 0), (0, 0, WIDTH, HUD_BAR_HEIGHT))
        pygame.draw.line(surface, HUD_GREEN, (0, HUD_BAR_HEIGHT - 2), (WIDTH, HUD_BAR_HEIGHT - 2), 2)

        blit_text(surface, FONT_SMALL, "1UP", HUD_RED, (20, 7))
        blit_text(surface, FONT_MED, f"{self.score:06d}", WHITE, (20, 24))
        blit_text(surface, FONT_SMALL, "HIGH SCORE", HUD_GOLD, (WIDTH // 2, 7), align="midtop")
        blit_text(surface, FONT_MED, f"{self.high_score:06d}", WHITE, (WIDTH // 2, 24), align="midtop")
        blit_text(surface, FONT_SMALL, f"WAVE {self.level:02d}", HUD_GREEN, (WIDTH - 170, 8))
        blit_text(surface, FONT_SMALL, f"CTRL {self.control_mode.upper()}  F1", BLUE, (WIDTH - 170, 30))

        life_asset = get_sprite_bank()["life"]
        for i in range(max(0, self.lives - 1)):
            draw_asset(surface, life_asset, (WIDTH - 36 - i * 28, 12))

        player_top = HEIGHT - PLAYER_AREA_HEIGHT
        for x in range(0, WIDTH, SEGMENT_SIZE):
            color = HUD_GOLD if (x // SEGMENT_SIZE) % 2 == 0 else HUD_GREEN
            pygame.draw.line(surface, color, (x, player_top), (min(WIDTH, x + SEGMENT_SIZE // 2), player_top), 2)

    def draw_ready_banner(self, surface):
        if self.ready_timer <= 0 or self.game_over:
            return
        pulse = (self.ready_timer // 10) % 2 == 0
        blit_text(surface, FONT_MED, "PLAYER 1", HUD_RED, (WIDTH // 2, HEIGHT // 2 - 54), align="center")
        if pulse:
            blit_text(surface, FONT_LARGE, "READY", HUD_GOLD, (WIDTH // 2, HEIGHT // 2), align="center")

    def draw_game_over(self, surface):
        panel = pygame.Surface((WIDTH - 110, 240), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 185))
        pygame.draw.rect(panel, HUD_RED, panel.get_rect(), 2)
        panel_rect = panel.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        surface.blit(panel, panel_rect)

        if self.game_over_image:
            image_rect = self.game_over_image.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 48))
            surface.blit(self.game_over_image, image_rect)

        blit_text(surface, FONT_LARGE, "GAME OVER", HUD_RED, (WIDTH // 2, HEIGHT // 2 - 8), align="center")
        blit_text(surface, FONT_MED, "PRESS ENTER TO RESTART", WHITE, (WIDTH // 2, HEIGHT // 2 + 42), align="center")

    def draw_game(self):
        surf = self.surface
        surf.blit(self.playfield_backdrop, (0, 0))

        for m in self.mushrooms:
            m.draw(surf)

        for c in self.centipedes:
            c.draw(surf, frame=self.frame_count)

        for s in self.spiders:
            s.draw(surf)
        for sc in self.scorpions:
            sc.draw(surf)
        for f in self.fleas:
            f.draw(surf)

        self.player.draw(surf)
        for b in self.bullets:
            b.draw(surf)

        self.draw_effects(surf)
        self.draw_hud(surf)
        self.draw_ready_banner(surf)

        if self.game_over:
            self.draw_game_over(surf)

        surf.blit(self.crt_overlay, (0, 0))

    def draw_attract(self):
        surf = self.surface
        surf.blit(self.playfield_backdrop, (0, 0))

        for m in self.attract_mushrooms:
            m.draw(surf)

        if self.attract_centipede and not self.attract_centipede.is_empty():
            self.attract_centipede.draw(surf, frame=self.frame_count)
        self.attract_player.draw(surf)
        for b in self.attract_bullets:
            b.draw(surf)
        self.draw_effects(surf)

        bob = int(math.sin(self.attract_angle) * 8)

        if self.title_image:
            title_rect = self.title_image.get_rect(
                center=(WIDTH // 2, 170 + bob)
            )
            surf.blit(self.title_image, title_rect)
        else:
            blit_text(surface=surf, font=FONT_TITLE, text="CENTIPEDE", color=GREEN, position=(WIDTH // 2, 170 + bob), align="center")

        blit_text(surf, FONT_MED, f"HIGH SCORE {self.high_score:06d}", WHITE, (WIDTH // 2, 300), align="center")
        blit_text(surf, FONT_SMALL, "EXTRA BLASTER EVERY 12000", HUD_GOLD, (WIDTH // 2, 336), align="center")

        legend_panel = pygame.Surface((WIDTH - 110, 350), pygame.SRCALPHA)
        legend_panel.fill((0, 0, 0, 178))
        pygame.draw.rect(legend_panel, HUD_GREEN, legend_panel.get_rect(), 2)
        legend_rect = legend_panel.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 150))
        surf.blit(legend_panel, legend_rect)

        entries = [
            (get_sprite_bank()["centipede_head"]["right"][0], "CENTIPEDE HEAD    100"),
            (get_sprite_bank()["spider"][0], "SPIDER      300 600 900"),
            (get_sprite_bank()["flea"][0], "FLEA              200"),
            (get_sprite_bank()["scorpion"]["right"], "SCORPION         1000"),
        ]
        legend_y = legend_rect.top + 38
        for asset, label in entries:
            draw_asset(surf, asset, (legend_rect.left + 34, legend_y - 12))
            blit_text(surf, FONT_MED, label, WHITE, (legend_rect.left + 120, legend_y))
            legend_y += 72

        blit_text(surf, FONT_SMALL, "MOVE  MOUSE / KEYBOARD / GAMEPAD", HUD_GREEN, (WIDTH // 2, legend_rect.bottom - 70), align="center")
        blit_text(surf, FONT_SMALL, "SHOOT  CLICK OR SPACE", HUD_GREEN, (WIDTH // 2, legend_rect.bottom - 44), align="center")
        pulse_color = HUD_GOLD if (self.frame_count // 20) % 2 == 0 else WHITE
        blit_text(surf, FONT_MED, "PRESS ENTER OR CLICK TO START", pulse_color, (WIDTH // 2, legend_rect.bottom - 12), align="center")

        surf.blit(self.crt_overlay, (0, 0))

    def draw(self):
        self.update_mouse_visibility()

        if self.mode == "attract":
            self.draw_attract()
        else:
            self.draw_game()

        shake_x = 0
        shake_y = 0
        if self.screen_shake_frames > 0:
            shake_x = random.randint(-self.screen_shake_strength, self.screen_shake_strength)
            shake_y = random.randint(-self.screen_shake_strength, self.screen_shake_strength)
            self.screen_shake_frames -= 1

        self.screen.fill(BLACK)
        if self.display_size == self.logical_size:
            self.screen.blit(self.surface, (shake_x, shake_y))
        else:
            scaled = pygame.transform.scale(self.surface, self.render_size)
            ox, oy = self.render_offset
            self.screen.blit(scaled, (ox + shake_x, oy + shake_y))

        pygame.display.flip()


if __name__ == "__main__":
    game = CentipedeGame()
    game.run()
