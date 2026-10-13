# Validation record

Build date: 13 October 2026. Platform: Windows 11 x64, build 26200. Python 3.12.14,
Panda3D 1.10.16, PyInstaller 6.22.0. Graphics: Intel Iris Xe, OpenGL 4.6,
driver 32.0.101.6737. Render size: 1280 x 720.

## Automated gameplay checks

**28 tests passed.** The recorded test output is in `qa/regression-results.txt`.
The tests cover all five primary weapons and five abilities; pistol and rail
piercing; shotgun push; rifle overdrive at zero ammo; rail chaining; launcher
explosions and solar fields; field slowing; wall occlusion; swept projectile
collision; damage, armor, healing and death; reload and switching; all upgrade
costs and caps; ten-stage progression and all weapon unlocks; checkpoint and shop
round trips; malformed and invalid saves; player collision; enemy telegraphs;
navigation from all spawn points in all arenas; and navigation for all enemy
body sizes.

The campaign-loop unit test exercises completion and reward transitions with
direct test damage. It does not represent a human completing the campaign.

## Packaged rendering and integration

The bundled executable completed **9 scripted integration checks** with exit
code 0: new-game checkpoint, movement, pause freezing, stage-clear upgrade bay,
purchase persistence, stage-2 unlock/refill, death, retry, and final victory.
Screenshots cover the menu, tutorial, play, pause, upgrades, settings, death,
victory, all three arena layouts, and later weapon models. Screenshots were
inspected for layout, visibility and clipping. See `qa/smoke-report.json`.

In a 240-frame offscreen rendering check with twelve enemies, the packaged game
took 1.5759 seconds, averaging **152.3 rendered frames/second** on the Intel Iris Xe.
This short scripted measurement runs without display synchronization and is not
a sustained gameplay benchmark or a promise of performance on other laptops.

## Native window checks

### Fullscreen update

The original F11 shortcut entered fullscreen during reproduction, but Windows
maximize was disabled and the display preference was never restored. The update
uses borderless desktop fullscreen by default, enables resizing/maximize in
windowed mode, adds a Display button in Settings and Alt+Enter, saves display mode,
and updates the camera and UI aspect ratio when the window changes size.

Direct native checks verified startup fullscreen, the Settings display button,
F11, Alt+Enter from a maximized window, return to windowed mode, and Windows
maximize. The rebuilt executable in `D:\Coding\FPS-Game` restored the saved
windowed preference, switched to fullscreen, displayed the playable first-person
view and HUD, paused/released the mouse, and reopened in saved fullscreen mode.
The updated build also passed all 28 gameplay tests and all nine packaged
integration checks. Tests used separate saves; existing player progress was not
modified. Multi-monitor configurations were not available for testing.

The source and packaged game were launched in a normal Windows window. Direct UI
interaction exercised New Run, the field manual, Deploy, first-person view, enemy
attacks, the death screen, Escape pause, mouse release, and closing the app.
The delivered executable also reopened an existing stage checkpoint through
Continue. Direct input confirmed that Q activated Lance Shot and started its
cooldown, and that primary fire reduced the pistol magazine from 12 to 11.
The sandboxed Python session could not reliably recenter the pointer; the native
executable launched outside that sandbox maintained a stable view. Cursor
confinement and a short capture warmup were added for menu transitions.
The close-window handler was corrected so closing the native window terminates
the process and saves settings. Alt+F4 on the final delivered executable was
directly tested, and its process exited with code 0.

The automated input tool is unsuitable for a sustained mouse-and-keyboard FPS
playthrough. Subjective gun feel, audio quality, a complete human run, and the
15–30 minute pacing target have not been validated by human playtesting.

## Offline and save checks

The packaged integration run used `--offline-check` with a fresh save directory.
This denied Python socket connections, DNS lookup, datagram sends and socket
binding throughout execution. The game loads its assets and runtime locally and
contains no networking code, CDN references, account flow or downloads.
The host network adapter was not disabled, and this check does not independently
block native engine networking APIs. No such APIs are used by the game.

The delivered executable also completed all nine integration checks with
`C:\Windows` as its working directory, `PATH` restricted to Windows system folders,
and `PYTHONPATH` / `PYTHONHOME` removed. This verified that the delivered runtime
and assets are independent of the development directory.

Temporary-file tests verify save files can be reopened by a fresh Storage and Game
instance, including stage, salvage, weapon, ranks and shop state. Invalid saves
are rejected and missing saves start cleanly. Combat saves are stage checkpoints;
individual enemy positions and partial-stage rewards are intentionally reset on
Continue or Retry. Settings persistence is handled separately.

## Scope and remaining limits

- This is a compact arena campaign with three reusable layouts and ten stages.
- Environment geometry is flat-floor low-poly architecture; jumping, multiplayer,
  destructible cover, controller input and arbitrary key remapping are not included.
- The Windows executable is unsigned. It bundles Python and all required game
  libraries; a working Windows graphics driver is still required.
- Development dependency installation uses the internet. Playing does not.
- Hardware compatibility beyond this Windows 11 / Intel Iris Xe machine has not
  been tested.

The final delivery sizes and SHA-256 inventory are recorded in `PACKAGE-SIZES.json`
and `SHA256SUMS.txt` beside the executable. Relocation checks are recorded separately
in `qa/relocation-check.json`.
