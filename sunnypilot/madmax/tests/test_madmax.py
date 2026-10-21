import pytest

from opendbc.car.honda.interface import CarInterface as HondaCarInterface
from opendbc.car.honda.values import CAR as HONDA
from opendbc.car.toyota.interface import CarInterface as ToyotaCarInterface
from opendbc.car.toyota.values import CAR as TOYOTA
from openpilot.sunnypilot.madmax import tune
from openpilot.sunnypilot.madmax.apply import apply_madmax_tune


def civic_cp():
  return HondaCarInterface.get_non_essential_params(HONDA.HONDA_CIVIC_2022)


def pid_gains(CP):
  pid = CP.lateralTuning.pid
  return list(pid.kpV), list(pid.kiV), pid.kf


@pytest.fixture
def profile(monkeypatch):
  def set_profile(**scales):
    monkeypatch.setitem(tune.PROFILES, "test", scales)
    monkeypatch.setattr(tune, "ACTIVE_PROFILE", "test")
  return set_profile


def test_scales_civic_pid_gains(profile):
  profile(kp=1.2, ki=1.1, kf=1.3)
  CP = civic_cp()
  kp_v, ki_v, kf = pid_gains(CP)

  apply_madmax_tune(CP)

  new_kp_v, new_ki_v, new_kf = pid_gains(CP)
  assert new_kp_v == pytest.approx([v * 1.2 for v in kp_v])
  assert new_ki_v == pytest.approx([v * 1.1 for v in ki_v])
  assert new_kf == pytest.approx(kf * 1.3)


def test_stock_profile_is_unchanged(profile):
  profile(kp=1.0, ki=1.0, kf=1.0)
  CP = civic_cp()
  before = pid_gains(CP)

  apply_madmax_tune(CP)

  assert pid_gains(CP) == before


def test_out_of_range_scales_are_clamped(profile):
  profile(kp=12.0, ki=0.0, kf=1.0)
  CP = civic_cp()
  kp_v, ki_v, _ = pid_gains(CP)

  apply_madmax_tune(CP)

  new_kp_v, new_ki_v, _ = pid_gains(CP)
  assert new_kp_v == pytest.approx([v * tune.MAX_SCALE for v in kp_v])
  assert new_ki_v == pytest.approx([v * tune.MIN_SCALE for v in ki_v])


def test_non_finite_scale_falls_back_to_stock(profile):
  profile(kp=float("nan"), ki=float("inf"), kf=1.0)
  CP = civic_cp()
  before = pid_gains(CP)

  apply_madmax_tune(CP)

  assert pid_gains(CP) == before


def test_unknown_profile_is_ignored(monkeypatch):
  monkeypatch.setattr(tune, "ACTIVE_PROFILE", "does-not-exist")
  CP = civic_cp()
  before = pid_gains(CP)

  apply_madmax_tune(CP)

  assert pid_gains(CP) == before


def test_skipped_when_torque_control_active(profile):
  profile(kp=1.5, ki=1.5, kf=1.5)
  CP = civic_cp()
  HondaCarInterface.configure_torque_tune(CP.carFingerprint, CP.lateralTuning)
  torque_before = (CP.lateralTuning.torque.latAccelFactor, CP.lateralTuning.torque.friction)

  apply_madmax_tune(CP)

  assert CP.lateralTuning.which() == 'torque'
  assert (CP.lateralTuning.torque.latAccelFactor, CP.lateralTuning.torque.friction) == torque_before


def test_other_platforms_untouched(profile):
  profile(kp=1.5, ki=1.5, kf=1.5)
  CP = ToyotaCarInterface.get_non_essential_params(TOYOTA.TOYOTA_RAV4)
  before = CP.to_bytes()

  apply_madmax_tune(CP)

  assert CP.to_bytes() == before
