"""
Dataclasses for Solar Stringing Optimizer
"""

from dataclasses import dataclass
from typing import Tuple

@dataclass
class PanelSpecs:
    """Panel specifications"""
    panel_id: str
    voc_stc: float
    isc_stc: float
    vmpp_stc: float
    impp_stc: float
    roof_plane_id: str
    center_coords: Tuple[float, float]


@dataclass
class InverterSpecs:
    """Inverter specifications"""
    inverter_id: str
    max_dc_voltage: float
    mppt_min_voltage: float
    mppt_max_voltage: float
    max_dc_current_per_mppt: float
    max_dc_current_per_string: float
    number_of_mppts: int
    startup_voltage: float
    max_short_circuit_current_per_mppt: float = None
    rated_ac_power_w: float = None
    number_of_inverters: int = 1


@dataclass
class TemperatureData:
    """Temperature data"""
    min_temp_c: float
    max_temp_c: float
    avg_high_temp_c: float
    avg_low_temp_c: float
