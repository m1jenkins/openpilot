"""
Mad Max gear readout: the 6MT's position (clutch, 1st-6th, reverse) in carStateSP.madmaxGearMT.

The 2022+ Civic DBC already decodes GEARBOX_ALT_2 (0x1DD) GEAR_MT, but stock sunnypilot never reads it.
This is a raw readout for logs and the UI. Nothing in control uses it, and carState.gearShifter is untouched.

Values: 0 = clutch, 1-6 = gear, 14 = reverse, -1 = unavailable. Anything else is an undocumented GEAR_MT
value (neutral may turn up as one), passed through as-is.

Guards, so a readout can never fault the car:
- It only runs when the car sent 0x1DD while fingerprinting (HondaFlagsSP.MADMAX_GEARBOX_MT, set in the Honda interface).
- It has its own CAN parser. card never checks that parser's can_valid, and 0x1DD has no alive or counter checks.
  Checksums are still verified, so a corrupted frame is dropped.
- Any error turns the readout off for the rest of the drive instead of stopping card.
"""
import math

from opendbc.can import CANParser
from opendbc.car import Bus, structs
from opendbc.car.can_definitions import CanData
from opendbc.car.honda.hondacan import CanBus
from opendbc.car.honda.values import DBC
from opendbc.sunnypilot.car.honda.values_ext import HondaFlagsSP
from openpilot.common.swaglog import cloudlog

GEAR_MSG = "GEARBOX_ALT_2"
GEAR_UNAVAILABLE = -1
STALE_CYCLES = 100  # 1 s at card's 100 Hz


class GearReader:
  def __init__(self, CP: structs.CarParams):
    # NaN frequency: no alive check
    self.parser: CANParser | None = CANParser(DBC[CP.carFingerprint][Bus.pt], [(GEAR_MSG, math.nan)], CanBus(CP).pt)
    self.address = self.parser.dbc.name_to_msg[GEAR_MSG].address
    self.parser.message_states[self.address].ignore_counter = True

    self.gear = GEAR_UNAVAILABLE
    self.cycles_since_update = STALE_CYCLES

  def update(self, can_packets: list[tuple[int, list[CanData]]]) -> int:
    if self.parser is None:
      return GEAR_UNAVAILABLE

    try:
      if self.address in self.parser.update(can_packets):
        self.gear = int(self.parser.vl[self.address]["GEAR_MT"])
        self.cycles_since_update = 0
      else:
        self.cycles_since_update = min(self.cycles_since_update + 1, STALE_CYCLES)
    except Exception:
      cloudlog.exception("madmax: gear readout failed, off for the rest of this drive")
      self.parser = None
      return GEAR_UNAVAILABLE

    return self.gear if self.cycles_since_update < STALE_CYCLES else GEAR_UNAVAILABLE


def create_gear_reader(CP: structs.CarParams, CP_SP: structs.CarParamsSP) -> GearReader | None:
  # CP_SP.flags bits mean different things for each brand
  if CP.brand != "honda" or not CP_SP.flags & HondaFlagsSP.MADMAX_GEARBOX_MT:
    return None

  cloudlog.warning("madmax: car sends 0x1DD, gear readout on")
  return GearReader(CP)
