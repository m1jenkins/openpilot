"""
Mad Max tune: the one file to edit when playing with the Civic's steering feel.

Applies to the 2022+ Honda Civic platform (HONDA_CIVIC_2022), which includes the 2024 Civic Si 6MT.
Changes take effect at the start of the next drive (CarParams are built when the car turns on).

What this tunes
---------------
The Civic steers with sunnypilot's PID lateral controller by default. The numbers below are
multipliers on the gains sunnypilot ships for this car (opendbc/car/honda/interface.py):

  kp  proportional gain  - how hard it corrects the error between desired and actual wheel angle.
                           Higher = snappier, tighter line. Too high = twitchy / ping-pong in the lane.
  ki  integral gain      - how much it leans on a persistent error, e.g. a long sweeper or crowned road.
                           Higher = holds the line better mid-corner. Too high = slow wobble, overshoot on exit.
  kf  feedforward gain   - torque applied up front for the curve the model wants, before any error builds.
                           Higher = turns in earlier and harder. Too high = cuts the inside on corner exit.

Change one thing at a time, in small steps (0.05), and drive the same stretch of road to compare.

What this does NOT do
---------------------
- If you turn on "Neural Network Lateral Control (NNLC)" or "Enforce Torque Lateral Control" in
  Settings > Steering, the car no longer uses PID and this file is skipped. Tune those from the UI.
- It cannot raise the steering torque or rate limits. Those are enforced by the panda safety firmware
  and by openpilot's ~3 m/s^2 lateral acceleration cap, and this fork leaves them alone. In a tight,
  fast corner sunnypilot will run out of authority and you have to steer.

Every value is clamped to MIN_SCALE..MAX_SCALE. If this file fails to load, the car falls back to
stock sunnypilot values and logs "madmax:" to the device log.
"""

# "stock" = exactly what sunnypilot ships. Start here or at "sport", then work up.
ACTIVE_PROFILE = "sport"

PROFILES = {
  "stock": {"kp": 1.00, "ki": 1.00, "kf": 1.00},
  "sport": {"kp": 1.15, "ki": 1.10, "kf": 1.10},
  "madmax": {"kp": 1.30, "ki": 1.20, "kf": 1.20},
}

# Hard guard rails against typos, e.g. 12 instead of 1.2.
MIN_SCALE = 0.5
MAX_SCALE = 1.5
