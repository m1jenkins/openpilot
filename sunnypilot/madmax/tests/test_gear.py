import pytest

from opendbc.can import CANPacker
from opendbc.car import Bus, gen_empty_fingerprint, structs
from opendbc.car.honda.interface import CarInterface as HondaCarInterface
from opendbc.car.honda.values import CAR as HONDA, DBC
from opendbc.car.toyota.interface import CarInterface as ToyotaCarInterface
from opendbc.car.toyota.values import CAR as TOYOTA
from opendbc.sunnypilot.car.honda.values_ext import HondaFlagsSP
from openpilot.sunnypilot.madmax.gear import GEAR_MSG, GEAR_UNAVAILABLE, STALE_CYCLES, create_gear_reader

TransmissionType = structs.CarParams.TransmissionType

GEARBOX_ALT_2 = 0x1DD
GEARBOX_AUTO = 0x1A3


def civic_params(*pt_addrs: int):
  fingerprint = gen_empty_fingerprint()
  for addr in pt_addrs:
    fingerprint[0][addr] = 8
  CP = HondaCarInterface.get_params(HONDA.HONDA_CIVIC_2022, fingerprint, [], False, False, False)
  CP_SP = HondaCarInterface.get_params_sp(CP, HONDA.HONDA_CIVIC_2022, fingerprint, [], False, False, False)
  return CP, CP_SP


@pytest.fixture
def reader():
  CP, CP_SP = civic_params(GEARBOX_ALT_2)
  return create_gear_reader(CP, CP_SP)


@pytest.fixture
def frames():
  packer = CANPacker(DBC[HONDA.HONDA_CIVIC_2022][Bus.pt])
  t = 0

  def make(gear: int, **values):
    nonlocal t
    t += 10_000_000
    return [(t, [packer.make_can_msg(GEAR_MSG, 0, {"GEAR_MT": gear, **values})])]
  return make


def test_flag_set_on_manual_with_gear_message():
  CP, CP_SP = civic_params(GEARBOX_ALT_2)
  assert CP.transmissionType == TransmissionType.manual
  assert CP_SP.flags & HondaFlagsSP.MADMAX_GEARBOX_MT
  assert create_gear_reader(CP, CP_SP) is not None


def test_off_without_gear_message_in_fingerprint():
  CP, CP_SP = civic_params()
  assert not CP_SP.flags & HondaFlagsSP.MADMAX_GEARBOX_MT
  assert create_gear_reader(CP, CP_SP) is None


def test_off_on_automatic():
  CP, CP_SP = civic_params(GEARBOX_ALT_2, GEARBOX_AUTO)
  assert CP.transmissionType == TransmissionType.automatic
  assert not CP_SP.flags & HondaFlagsSP.MADMAX_GEARBOX_MT


def test_other_brands_ignore_the_flag_bit():
  CP = ToyotaCarInterface.get_non_essential_params(TOYOTA.TOYOTA_RAV4)
  CP_SP = ToyotaCarInterface.get_non_essential_params_sp(CP, TOYOTA.TOYOTA_RAV4)
  CP_SP.flags |= HondaFlagsSP.MADMAX_GEARBOX_MT.value
  assert create_gear_reader(CP, CP_SP) is None


def test_unavailable_until_first_frame(reader):
  assert reader.update([]) == GEAR_UNAVAILABLE


@pytest.mark.parametrize("gear", [0, 1, 3, 6, 14, 15])
def test_reads_gear(reader, frames, gear):
  assert reader.update(frames(gear)) == gear


def test_goes_stale_when_frames_stop(reader, frames):
  assert reader.update(frames(3)) == 3
  for _ in range(STALE_CYCLES - 1):
    assert reader.update([]) == 3
  assert reader.update([]) == GEAR_UNAVAILABLE


def test_bad_checksum_dropped(reader, frames):
  [(t, [(addr, dat, bus)])] = frames(4)
  bad = dat[:7] + bytes([dat[7] ^ 0x0F])  # CHECKSUM is the low nibble of byte 7
  assert reader.update([(t, [(addr, bad, bus)])]) == GEAR_UNAVAILABLE


def test_counter_errors_ignored(reader, frames):
  # a frozen counter would invalidate a normally parsed message after a few frames
  for gear in (1, 2, 3, 4, 5, 6, 5, 4):
    assert reader.update(frames(gear, COUNTER=0)) == gear


def test_other_buses_ignored(reader):
  packer = CANPacker(DBC[HONDA.HONDA_CIVIC_2022][Bus.pt])
  addr, dat, _ = packer.make_can_msg(GEAR_MSG, 0, {"GEAR_MT": 2})
  assert reader.update([(10_000_000, [(addr, dat, 2)])]) == GEAR_UNAVAILABLE


def test_error_turns_readout_off(reader, frames, monkeypatch):
  assert reader.update(frames(2)) == 2

  def fail(*args, **kwargs):
    raise ValueError("boom")
  monkeypatch.setattr(reader.parser, "update", fail)

  assert reader.update(frames(3)) == GEAR_UNAVAILABLE
  assert reader.parser is None
  assert reader.update(frames(3)) == GEAR_UNAVAILABLE
