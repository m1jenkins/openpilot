"""
Applies the Mad Max profile from tune.py to CarParams, before they are published to controlsd.
"""
import math

from opendbc.car import structs
from opendbc.car.honda.values import CAR
from openpilot.common.swaglog import cloudlog
from openpilot.sunnypilot.madmax import tune

SUPPORTED_PLATFORMS = (CAR.HONDA_CIVIC_2022,)


def _get_scales(profile: dict) -> dict[str, float]:
  scales = {}
  for gain in ("kp", "ki", "kf"):
    value = float(profile.get(gain, 1.0))
    clamped = min(max(value, tune.MIN_SCALE), tune.MAX_SCALE) if math.isfinite(value) else 1.0
    if clamped != value:
      cloudlog.warning(f"madmax: {gain}={value} out of range, clamped to {clamped}")
    scales[gain] = clamped
  return scales


def apply_madmax_tune(CP: structs.CarParams) -> None:
  if CP.carFingerprint not in SUPPORTED_PLATFORMS:
    return

  profile = tune.PROFILES.get(tune.ACTIVE_PROFILE)
  if profile is None:
    cloudlog.warning(f"madmax: unknown profile {tune.ACTIVE_PROFILE!r}, using stock sunnypilot values")
    return

  lat_tuning = CP.lateralTuning.which()
  if lat_tuning != 'pid':
    cloudlog.warning(f"madmax: {lat_tuning} lateral control is active (NNLC/Torque toggle), PID profile skipped")
    return

  # compute everything before writing, so a bad value can't leave a half-applied tune
  scales = _get_scales(profile)
  pid = CP.lateralTuning.pid
  kp_v = [v * scales["kp"] for v in pid.kpV]
  ki_v = [v * scales["ki"] for v in pid.kiV]
  kf = pid.kf * scales["kf"]

  pid.kpV = kp_v
  pid.kiV = ki_v
  pid.kf = kf

  cloudlog.warning(f"madmax: applied profile {tune.ACTIVE_PROFILE!r}: kpV={kp_v} kiV={ki_v} kf={kf}")
