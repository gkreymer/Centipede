# Centipede

Arcade-style Centipede game built with Pygame.

The project is centered around a single main source file, `Centipede.py`, plus a few image assets used for the attract screen and game-over presentation. The current version is styled to feel closer to the original arcade game, with pixel sprites, CRT-style scanlines, a retro HUD, attract mode, and arcade-inspired scoring and enemy behavior.

## Files

- `Centipede.py`: Main game code, gameplay loop, rendering, audio generation, and input handling.
- `centipede_logo.png`: Title/logo image used on the attract screen.
- `Game Over.jpg`: Image used on the game-over screen.
- `centipede_logo_2.png` and `centipede_logo_original.png`: Alternate source logo images kept in the project folder.

## Requirements

- Python 3.10+
- `pygame`

Install Pygame with:

```powershell
python -m pip install pygame
```

## How To Run

From the `centipede` project folder:

```powershell
python .\Centipede.py
```

If your Python launcher is configured differently, this also works:

```powershell
py .\Centipede.py
```

## Controls

- `Enter`: Start game or restart after game over
- `Alt+Enter`: Toggle fullscreen
- `Esc`: Quit
- `F1`: Cycle control mode between mouse, keyboard, and gamepad
- Mouse mode: Move with mouse, fire with left click
- Keyboard mode: Move with `WASD` or arrow keys, fire with `Space`
- Gamepad mode: Move with left stick, fire with `Space` on keyboard or mouse click unless expanded later

## Gameplay Notes

- You control the bug blaster in the lower player area.
- The centipede moves across the field, drops one row when blocked, and reverses direction.
- Poisoned mushrooms make centipede heads dive downward.
- Shooting a centipede segment creates a mushroom where that segment was destroyed.
- Fleas appear when the player area gets too sparse with mushrooms.
- Scorpions poison mushrooms.
- Spiders roam the lower playfield and eat mushrooms.
- Extra lives are awarded every `12,000` points.
- Damaged and poisoned mushrooms are restored after losing a life, with a small score bonus.

## Scoring

- Centipede head: `100`
- Centipede body: `10`
- Spider: `300`, `600`, or `900` depending on position
- Flea: `200`
- Scorpion: `1000`
- Destroyed mushroom: `1`

## Code Structure

`Centipede.py` is organized into a few main parts:

- Constants and configuration: Logical resolution, colors, speeds, scoring, and level tables.
- Sound synthesis: Procedurally generated retro sound effects using `pygame.mixer`.
- Sprite and helper utilities: Pixel sprite generation, glow effects, text helpers, and sprite bank creation.
- Entity classes: `Player`, `Bullet`, `Mushroom`, `Centipede`, `Spider`, `Scorpion`, `Flea`, and visual effects.
- `CentipedeGame`: Main game state manager for attract mode, gameplay, rendering, HUD, collision handling, and progression.

## Visual Style

The current build includes:

- Pixel-art enemy and player sprites
- CRT overlay and vignette effect
- Starfield-style backdrop
- Retro score bar / HUD
- Attract screen with logo and scoring legend
- Hit flashes and small screen-shake effects

## Assets

The game expects these files to remain in the same folder as `Centipede.py`:

- `centipede_logo.png`
- `Game Over.jpg`

If those files are missing, the game will still run, but it will fall back to text or omit the related art.

## Notes For Future Editing

- Most gameplay tuning can be adjusted near the top of `Centipede.py` in the constants and `LEVEL_TABLE`.
- Sprite appearance is defined in the sprite-bank helper section.
- HUD and attract-screen presentation are handled inside the `CentipedeGame` drawing methods.
- If you later want a standard project readme name, this file can be renamed from `READNE.md` to `README.md`.

## Author

**Developer:**  Gregory I. Kreymer  
**Initial Release:**  March 25, 2026