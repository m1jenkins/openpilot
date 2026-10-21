# Mad Max: sunnypilot for the 2024 Civic Si 6MT

A personal fork of [sunnypilot](https://github.com/sunnypilot/sunnypilot) for tweaking how the Civic feels on twisty roads.

| | |
|---|---|
| Based on | sunnypilot `release-tizi` (v2026.002.002), the recommended release. `release-mici` is the same commit |
| Runs on | comma 3X and comma four. The comma three (C3) needs a different base, `staging-tici` |
| Car | `HONDA_CIVIC_2022` platform. The Si is detected as a manual: no gearbox message, reverse read from the reverse light |
| Branch | `madmax`. Everything Mad Max adds sits on top of the tag `madmax-base`, the untouched sunnypilot release |

## What's different from stock sunnypilot

The fork adds one thing: [`sunnypilot/madmax/tune.py`](sunnypilot/madmax/tune.py), a single file of steering-gain profiles (`stock`, `sport`, `madmax`). It ships set to `sport`.

- The profiles scale the PID steering gains sunnypilot already uses for the Civic: **kp** (correction), **ki** (holding a long corner) and **kf** (turn-in feedforward). Each value is clamped to 0.5–1.5× stock.
- The tune only applies to `HONDA_CIVIC_2022`, and only when the PID controller is active. If you turn on NNLC or Torque control in the UI, the tune is skipped.
- If `tune.py` has a mistake, the car still starts on stock sunnypilot values and the device log records a `madmax:` line.

Nothing else changes. The panda safety firmware, steering torque and rate limits, the lateral-acceleration cap, driver monitoring and the car's AEB/ACC behave exactly as in stock sunnypilot.

## Reality check for twisty roads

- **Steering authority is capped.** openpilot limits commanded cornering to about 3 m/s² (≈0.3 g). sunnypilot's data for this car says full EPS torque is worth about 2.5 m/s². Spirited cornering goes well past both, so in a tight or fast corner sunnypilot will run wide, show "Turn Exceeds Steering Limit", and you steer. Tuning changes how crisp it feels *inside* that envelope. It can't make it a canyon carver, and this fork does not raise those limits.
- **The manual means you drive the pedals.** sunnypilot can't see the clutch. Speed control is Honda's own ACC (`pcmCruise`), so the clutch and ACC behave as they do stock. Leave **Developer → sunnypilot Longitudinal Control (Alpha)** off on this car. sunnypilot's own warning says it may disable AEB, it takes over the camera's ACC messages, and it's untested with a clutch.
- The best combination for back roads is **MADS**. Steering assist runs on its own, toggled with the LKAS button, while you handle the throttle, clutch and shifting.

## Install on the comma device

**Option A: URL install.** The comma installer only finds repos named `openpilot`.

1. On GitHub, rename `m1jenkins/SunnyPilot_MadMax` to `openpilot` (repo **Settings → General → Repository name**). GitHub redirects the old URL, so your local clone keeps working.
2. On the device, uninstall the current software (**Settings → Software → Uninstall**). At setup, choose **Custom Software** and enter:
   ```
   installer.comma.ai/m1jenkins/madmax
   ```

**Option B: SSH.** This keeps the repo name.

1. **Settings → Developer**: enable SSH and add your GitHub username (it pulls your SSH keys).
2. Then run:
   ```bash
   ssh comma@<device-ip>
   cd /data && mv openpilot openpilot.bak
   git clone -b madmax --depth 1 https://github.com/m1jenkins/SunnyPilot_MadMax.git openpilot
   sudo reboot
   ```

This branch is prebuilt, so the device doesn't compile anything. Python edits like `tune.py` take effect as-is.

## The tuning loop

1. Edit `sunnypilot/madmax/tune.py`: change `ACTIVE_PROFILE` or the numbers.
2. Commit and `git push origin madmax`.
3. On the device, go to **Settings → Software → Download → CHECK**, then install. The new tune applies from the next drive.

Change one value at a time in steps of about 0.05, and drive the same stretch of road each time. Edit on GitHub or here, not on the device: the updater runs `git reset --hard` and `git clean`, which wipes local edits on the device.

| Symptom | Try |
|---|---|
| Lazy turn-in, drifts to the outside early in the corner | kf up |
| Wanders or is slow to correct on straights | kp up |
| Slowly loses the line through a long sweeper | ki up |
| Twitchy, or ping-pongs in the lane | kp down |
| Cuts the inside or overshoots on corner exit | kf or ki down |

## Device settings worth playing with (no code needed)

| Where | Setting | Notes |
|---|---|---|
| Steering | **MADS** → Customize MADS → *Steering Mode on Brake Pedal* | *Pause* lets go while you brake into a corner and comes back after. If the car only supports limited MADS, the screen says so |
| Steering | **Neural Network Lateral Control (NNLC)** | sunnypilot has a model trained on `HONDA_CIVIC_2022` data. It's a good A/B test against the Mad Max PID. `tune.py` is skipped while it's on |
| Steering | **Enforce Torque Lateral Control** → Customize Torque Params → *Manual Real-Time Tuning* | Adjust while you drive. **Lateral Acceleration Factor** (this car's stock value is 2.5): lower means more torque per corner, so more aggressive. **Friction** (stock 0.15): higher means crisper initial response, but it gets notchy. `tune.py` is skipped while it's on |
| Models | **Live Learning Steer Delay** | Leave it on. It learns the car's real steering lag. If it's off, **Adjust Software Delay** sets the lag manually |
| Cruise | **Intelligent Cruise Button Management (ICBM) (Alpha)** + **Smart Cruise Control – Vision** | Makes the stock ACC slow down for curves ahead by pressing the cruise buttons for you. It's the opposite of spirited, but handy on a long drive |

## Keeping up with sunnypilot releases

```bash
powershell -ExecutionPolicy Bypass -File sunnypilot\madmax\sync_upstream.ps1
```

This fetches the latest `release-tizi` and replays your commits on top. It stops if there are conflicts, and it never pushes. Afterwards run `git push --force-with-lease origin madmax` and `git push --force origin madmax-base`. The force push is normal for release-based forks, and the device updater handles it.

## Repo notes

- `origin` is your GitHub repo. `upstream` is sunnypilot, set to fetch-only and limited to `release-tizi`, so a stray `git fetch upstream` doesn't pull every branch.
- `main` on GitHub still holds the original "Initial commit". Set **madmax** as the default branch in the GitHub repo settings.
- This clone sits in OneDrive, which syncs about 4,000 files and the `.git` folder. If OneDrive acts up, move the folder outside OneDrive (for example `C:\dev`).
- Tests: `pytest sunnypilot/madmax` needs a sunnypilot dev environment (Ubuntu/WSL). They can't run on plain Windows.
