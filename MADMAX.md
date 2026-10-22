# Mad Max: sunnypilot for the 2024 Civic Si 6MT

A personal fork of [sunnypilot](https://github.com/sunnypilot/sunnypilot) for tweaking how the Civic feels on twisty roads.

| | |
|---|---|
| Based on | sunnypilot `release-mici` (v2026.002.002), the recommended comma four release. `release-tizi` (comma 3X) is the same commit |
| Device | comma four (also runs on a comma 3X) |
| Car | `HONDA_CIVIC_2022` platform. The Si is detected as a manual: no gearbox message, reverse read from the reverse light |
| Repo / branch | `m1jenkins/openpilot`, branch `madmax`. Everything Mad Max adds sits on top of the tag `madmax-base`, the untouched sunnypilot release |

## What's different from stock sunnypilot

The fork adds one thing: [`sunnypilot/madmax/tune.py`](sunnypilot/madmax/tune.py), a single file of steering-gain profiles (`stock`, `sport`, `madmax`). It ships set to `sport`.

- The profiles scale the PID steering gains sunnypilot already uses for the Civic: **kp** (correction), **ki** (holding a long corner) and **kf** (turn-in feedforward). Each value is clamped to 0.5–1.5× stock.
- The tune only applies to `HONDA_CIVIC_2022`, and only when the PID controller is active. If you turn on NNLC or Torque control, the tune is skipped.
- If `tune.py` has a mistake, the car still starts on stock sunnypilot values and the device log records a `madmax:` line.

Nothing else changes. The panda safety firmware, steering torque and rate limits, the lateral-acceleration cap, driver monitoring and the car's AEB/ACC behave exactly as in stock sunnypilot.

## Reality check for twisty roads

- **Steering authority is capped.** openpilot limits commanded cornering to about 3 m/s² (≈0.3 g). sunnypilot's data for this car says full EPS torque is worth about 2.5 m/s². Spirited cornering goes well past both, so in a tight or fast corner sunnypilot will run wide, show "Turn Exceeds Steering Limit", and you steer. Tuning changes how crisp it feels *inside* that envelope. It can't make it a canyon carver, and this fork does not raise those limits.
- **The manual means you drive the pedals.** sunnypilot can't see the clutch. Speed control is Honda's own ACC (`pcmCruise`), so the clutch and ACC behave as they do stock. Leave **developer → alpha longitudinal** off on this car. The device's own warning says it may disable AEB, it takes over the camera's ACC messages, and it's untested with a clutch.
- The best combination for back roads is **MADS** (on by default). Steering assist runs on its own, toggled with the LKAS button, while you handle the throttle, clutch and shifting.

## Install on the comma four

**Option A: URL install.**

1. On the device, open **settings → device → uninstall sunnypilot**.
2. At setup, choose custom software and enter:
   ```
   installer.comma.ai/m1jenkins/madmax
   ```

**Option B: SSH.**

1. Open **settings → developer**: turn on SSH, then set **SSH keys** to your GitHub username.
2. Then run:
   ```bash
   ssh comma@<device-ip>
   cd /data && mv openpilot openpilot.bak
   git clone -b madmax --depth 1 https://github.com/m1jenkins/openpilot.git openpilot
   sudo reboot
   ```

This branch is prebuilt, so the device doesn't compile anything. Python edits like `tune.py` take effect as-is.

## The tuning loop

1. Edit `sunnypilot/madmax/tune.py`: change `ACTIVE_PROFILE` or the numbers.
2. Commit and `git push origin madmax`.
3. On the device, tap **settings → device → update sunnypilot**. The new tune applies from the next drive.

Change one value at a time in steps of about 0.05, and drive the same stretch of road each time. Edit here or on GitHub, not in `/data/openpilot` on the device: the updater runs `git reset --hard` and `git clean`, which wipes local code edits.

| Symptom | Try |
|---|---|
| Lazy turn-in, drifts to the outside early in the corner | kf up |
| Wanders or is slow to correct on straights | kp up |
| Slowly loses the line through a long sweeper | ki up |
| Twitchy, or ping-pongs in the lane | kp down |
| Cuts the inside or overshoots on corner exit | kf or ki down |

## sunnypilot settings on the comma four

The comma four's screen only shows openpilot's basics (driving personality, experimental mode, models, sunnylink, developer). sunnypilot's steering settings exist, but they aren't on the screen. There are two ways to change them:

- **sunnylink:** pair the device (**settings → sunnylink → pair**). sunnylink can read and write the device's settings remotely. Use **backup settings** first.
- **SSH:** settings live in params. Run these from `/data/openpilot`:
  ```bash
  python3 -c "from openpilot.common.params import Params as P; print(P().get('MadsSteeringMode'))"   # read
  python3 -c "from openpilot.common.params import Params as P; P().put_bool('NeuralNetworkLateralControl', True)"  # on/off
  python3 -c "from openpilot.common.params import Params as P; P().put('TorqueParamsOverrideLatAccelFactor', 2.2)"  # number
  ```

Params survive updates. Most take effect on the next drive; the real-time torque values change live.

| Param | Values | What it does on the Civic |
|---|---|---|
| `Mads` | bool, default on | Steering assist independent of cruise, toggled with the LKAS button |
| `MadsSteeringMode` | `0` remain active, `1` pause, `2` disengage | What steering does when you press the brake. `1` lets go while you brake into a corner and comes back after |
| `NeuralNetworkLateralControl` | bool, default off | Data-trained steering model. sunnypilot ships one for `HONDA_CIVIC_2022`. A good A/B test against the Mad Max PID. Skips `tune.py` |
| `EnforceTorqueControl` | bool, default off | Switches the Civic from PID to the torque controller. Skips `tune.py` |
| `CustomTorqueParams` + `TorqueParamsOverrideEnabled` | bool | Both on (with `EnforceTorqueControl`) means the two values below are used live while driving |
| `TorqueParamsOverrideLatAccelFactor` | float, Civic stock 2.5 | Lower means more torque per corner, so more aggressive |
| `TorqueParamsOverrideFriction` | float, Civic stock 0.15 | Higher means crisper initial response, but it gets notchy |
| `LagdToggle` | bool, default on | Learns the car's real steering lag. Leave it on |

If you want these in a file instead, `tune.py` can grow a section that sets them at startup. Ask for it.

## Keeping up with sunnypilot releases

```bash
powershell -ExecutionPolicy Bypass -File sunnypilot\madmax\sync_upstream.ps1
```

This fetches the latest `release-mici` and replays your commits on top. It stops if there are conflicts, and it never pushes. Afterwards run `git push --force-with-lease origin madmax` and `git push --force origin madmax-base`. The force push is normal for release-based forks, and the device updater handles it.

## Repo notes

- `origin` is `m1jenkins/openpilot`, a GitHub fork of sunnypilot. `upstream` is sunnypilot, set to fetch-only and limited to `release-mici`, so a stray `git fetch upstream` doesn't pull every branch.
- The old `m1jenkins/SunnyPilot_MadMax` repo is unused, and you can delete it on GitHub.
- This clone sits in OneDrive, which syncs about 4,000 files and the `.git` folder, and competes with git for upload bandwidth. Consider moving it outside OneDrive (for example `C:\dev`).
- Tests: `pytest sunnypilot/madmax` needs a sunnypilot dev environment (Ubuntu/WSL). They can't run on plain Windows.
