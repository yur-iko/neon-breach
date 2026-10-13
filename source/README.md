# Neon Breach

A compact, fully local, first-person arena shooter for Windows 11 x64. Built in
Python with Panda3D. All models, arenas, effects and sounds are generated from
the included source; the font is bundled. No account, server, network connection
or Python installation is needed to play.

## Play

Double-click **NeonBreach.exe**. Keep the `_internal` folder beside the executable.
If using the ZIP, extract the entire archive before launching it. The game opens
in fullscreen at your monitor's desktop resolution. **F11** or **Alt+Enter** toggles
fullscreen; the **Display** button in Settings does the same. The chosen mode is
saved for the next launch. Windowed mode starts at 1280 x 720 and supports Windows
maximize and resizing. Fullscreen is borderless and does not change the monitor's
resolution. A Windows graphics driver with OpenGL support is required. The Python
runtime and required native libraries are included.

Choose **New Run**, read the field manual, then choose **Deploy**. Deploy and
Resume capture the mouse; **Escape** pauses and releases it. Switching away from
the game pauses combat automatically. A saved run adds **Continue** to the menu.

## Controls

| Input | Action |
|---|---|
| W A S D | Move |
| Mouse | Look |
| Shift | Sprint |
| Left mouse | Fire (hold for repeated fire) |
| Right mouse | Aim / zoom |
| Q | Equipped weapon's special ability |
| R | Reload |
| 1–5 or mouse wheel | Switch unlocked weapons |
| Escape | Pause, release mouse / resume from pause menu |
| F11 or Alt+Enter | Fullscreen / windowed (saved automatically) |

Reserve energy cells are unlimited; magazines still require reloading. There is
no jumping: the arenas use flat floors and solid cover. Weapon switching cancels
the current reload. Abilities have individual cooldowns and use no ammunition.

## The campaign

Clear ten increasingly busy stages across Relay Yard, Foundry and Ion Garden.
Enemies arrive from marked pads and approach around cover. Hunters close to melee
range; Rangers fire aimed bolts; crystalline Flankers move quickly and weave;
Heavies have more armor and slower, stronger bolts. Glowing enemies are preparing
an attack. The final Warden alternates an outward projectile ring with an aimed
fan, attacking faster below half health.

Earn salvage for eliminations and stage completion. Between stages, spend it on
15 capped upgrade tracks. Player upgrades improve health, armor, movement, damage,
reloads, magazine size, cooldowns and healing on kills. Weapon upgrades add pistol
piercing, shotgun pellets and knockback, longer rifle overdrive, extra railgun
chains, larger blasts, longer solar fields and better accuracy. Costs rise with
rank. Unspent salvage carries forward. Health, ammunition and abilities refill
at each new stage.

| Stage unlocked | Weapon | Primary | Q ability |
|---:|---|---|---|
| 1 | Arc Pistol | Accurate single shot | Lance Shot: powerful piercing beam |
| 2 | Breaker | Nine-pellet close-range spread | Repulsor: wide damage and knockback cone |
| 3 | Pulse Rifle | Rapid automatic fire | Overdrive: faster fire without ammo cost |
| 5 | Needle | Heavy piercing rail shot | Arc Network: chains damage to nearby visible targets |
| 7 | Sunforge | Explosive projectile | Solar Well: explosion followed by a burning, slowing field |

Solid cover blocks hitscan shots, enemy bolts, explosions and field damage.
Keep moving, use cover to interrupt ranged attacks, and aim at the bodies of
smaller Flankers. The run is designed around 15–30 minutes, but actual time depends
on aim, movement, upgrade choices and retries; a full human run has not been timed.

## Saving and resetting

Default save folder: `%LOCALAPPDATA%\NeonBreach`.

- `run.json`: campaign checkpoint and purchased upgrades.
- `settings.json`: mouse sensitivity, effects volume, and display mode.
- `error.log`: created only if an unhandled error occurs.

Saves are written atomically at the start of a stage, after stage completion, and
after each purchase. Continue and Retry restore the **start of the current stage**,
including its starting salvage; partially completed combat is not saved. Upgrade
screens are saved immediately. A finished campaign clears Continue.

Choose **New Run** and confirm to replace campaign progress. To reset everything,
close the game and delete the two JSON files from the save folder. Missing or
malformed data is handled by showing a fresh-start option. Settings can be changed
from the main menu or pause menu.

For a portable save location, launch from PowerShell with:

```powershell
.\NeonBreach.exe --save-dir .\saves
```

## Source and rebuilding

The `source` folder contains the complete project. Python 3.12 x64 is recommended
for rebuilding; it is not needed for playing. From that folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe make_audio.py
.\.venv\Scripts\python.exe -m unittest -v test_game
.\.venv\Scripts\python.exe main.py
.\.venv\Scripts\python.exe -m PyInstaller --noconfirm NeonBreach.spec
```

`build.ps1` performs these steps and copies documentation and notices. The built
game is in `source\dist\NeonBreach`. Dependency installation needs the internet
unless the wheels are already cached; the resulting game does not.

- `content.py`: weapons, upgrades, enemy stats and arena layouts.
- `simulation.py`: combat, navigation, collision, progression and save validation.
- `visuals.py`: procedural geometry, actors, projectiles and visual effects.
- `main.py`: Windows application, input, menus, HUD, audio and rendering checks.
- `make_audio.py`: deterministic original WAV generation.
- `test_game.py`: gameplay regression suite.
- `NeonBreach.spec`: portable executable build definition.
- `assets`: original generated sounds and the licensed Rajdhani font.
- `licenses`: third-party license texts and source links.

## Validation tools

Run the gameplay suite as shown above. The executable also includes a diagnostic
mode that writes screenshots and a machine-readable report, then exits:

```powershell
.\NeonBreach.exe --offscreen --offline-check --save-dir .\qa-saves --smoke-test .\qa-output
```

Use a separate save folder for diagnostics. `--offline-check` blocks Python socket
connections, name resolution and socket binding for that process. It does not
disable the system's network adapter or independently sandbox native C++ calls.
The game itself contains no networking code or remote asset references.

See `VALIDATION.md` for the checks actually performed, measurements and limits.
See `CREDITS.md` and `licenses` for component attribution.
