"""
Power Validation Module for Solar Stringing Optimization

This module provides real-time power validation during the stringing process.
It ensures that inverter power capacity is not exceeded as strings are assigned
to MPPTs and inverters.

Usage:
    validator = PowerValidator(inverter_specs, panel_specs, temp_data)
    result = validator.validate_string_assignment(string_panels, current_inverter_power)
    
    if result["valid"]:
        # Continue with current string
    else:
        # Split string and reassign
        split_at = result["recommended_split_index"]
"""

from typing import List, Dict, Any, Tuple
from dataclasses import dataclass


class PowerValidator:
    """
    Validates power capacity during string assignment.
    
    Ensures that adding a string to an MPPT/inverter doesn't exceed
    the inverter's rated AC power capacity (accounting for optimal DC/AC ratio).
    """
    
    def __init__(self, inverter_specs, panel_specs_sample, temperature_data,
                 target_dc_ac_ratio: float = 1.25, max_dc_ac_ratio: float = 1.5):
        """
        Initialize power validator.
        
        Args:
            inverter_specs: Inverter specifications
            panel_specs_sample: Sample panel spec to calculate power
            temperature_data: Temperature data for voltage calculation
            target_dc_ac_ratio: Target DC/AC ratio (default 1.25)
            max_dc_ac_ratio: Maximum acceptable DC/AC ratio (default 1.5)
        """
        self.inverter_specs = inverter_specs
        self.panel_sample = panel_specs_sample
        self.temp_data = temperature_data
        self.target_dc_ac_ratio = target_dc_ac_ratio
        self.max_dc_ac_ratio = max_dc_ac_ratio
        
        # Calculate power per panel at operating temperature
        temp_coeff_vmpp = 0.00446  # V/°C per panel
        temp_diff_hot = temperature_data.max_temp_c - 25.0
        vmpp_hot = panel_specs_sample.vmpp_stc * (1 + temp_coeff_vmpp * temp_diff_hot)
        self.power_per_panel = vmpp_hot * panel_specs_sample.impp_stc
        
        # Calculate inverter power limits
        self.inverter_ac_power = inverter_specs.rated_ac_power_w or 0
        self.target_dc_power_per_inverter = self.inverter_ac_power * target_dc_ac_ratio
        self.max_dc_power_per_inverter = self.inverter_ac_power * max_dc_ac_ratio
        
    def calculate_string_power(self, num_panels: int) -> float:
        """Calculate DC power for a string with given number of panels."""
        return num_panels * self.power_per_panel
    
    def validate_string_assignment(self, 
                                  string_panel_count: int,
                                  current_inverter_dc_power: float) -> Dict[str, Any]:
        """
        Validate if adding a string to an inverter exceeds power limits.
        
        Args:
            string_panel_count: Number of panels in the proposed string
            current_inverter_dc_power: Current DC power already assigned to inverter
            
        Returns:
            Dictionary with validation result:
            {
                "valid": bool,
                "string_power_W": float,
                "new_total_power_W": float,
                "new_dc_ac_ratio": float,
                "exceeds_target": bool,
                "exceeds_max": bool,
                "recommended_split_index": int (if invalid),
                "reason": str
            }
        """
        string_power = self.calculate_string_power(string_panel_count)
        new_total_power = current_inverter_dc_power + string_power
        new_dc_ac_ratio = (new_total_power / self.inverter_ac_power) if self.inverter_ac_power > 0 else 0
        
        exceeds_target = new_total_power > self.target_dc_power_per_inverter
        exceeds_max = new_total_power > self.max_dc_power_per_inverter
        
        result = {
            "valid": not exceeds_max,
            "string_power_W": round(string_power, 2),
            "new_total_power_W": round(new_total_power, 2),
            "new_dc_ac_ratio": round(new_dc_ac_ratio, 2),
            "exceeds_target": exceeds_target,
            "exceeds_max": exceeds_max,
            "inverter_capacity_remaining_W": round(self.max_dc_power_per_inverter - current_inverter_dc_power, 2)
        }
        
        if exceeds_max:
            # Calculate recommended split point (aim for 50% or what fits in remaining capacity)
            remaining_capacity = self.max_dc_power_per_inverter - current_inverter_dc_power
            max_panels_that_fit = int(remaining_capacity / self.power_per_panel)
            
            # Recommend split at 50% of string or max that fits, whichever is smaller
            recommended_split = min(string_panel_count // 2, max_panels_that_fit)
            
            result["valid"] = False
            result["recommended_split_index"] = max(1, recommended_split)  # At least 1 panel
            result["reason"] = f"String would exceed max DC/AC ratio ({new_dc_ac_ratio:.2f} > {self.max_dc_ac_ratio})"
            result["action"] = "SPLIT_STRING" if recommended_split > 0 else "NEW_INVERTER"
        elif exceeds_target:
            result["reason"] = f"Exceeds target ratio but acceptable ({new_dc_ac_ratio:.2f} vs target {self.target_dc_ac_ratio})"
            result["action"] = "CONTINUE"
        else:
            result["reason"] = f"Within optimal range ({new_dc_ac_ratio:.2f})"
            result["action"] = "CONTINUE"
        
        return result
    
    def suggest_new_inverter_needed(self, current_inverter_dc_power: float) -> bool:
        """
        Check if a new inverter should be started.
        
        Args:
            current_inverter_dc_power: Current DC power on inverter
            
        Returns:
            True if new inverter should be started
        """
        return current_inverter_dc_power >= self.max_dc_power_per_inverter
    
    def calculate_optimal_panels_for_remaining_capacity(self, current_inverter_dc_power: float) -> int:
        """
        Calculate how many more panels can fit in current inverter optimally.
        
        Args:
            current_inverter_dc_power: Current DC power on inverter
            
        Returns:
            Number of panels that can be added
        """
        remaining_capacity = self.max_dc_power_per_inverter - current_inverter_dc_power
        return int(remaining_capacity / self.power_per_panel)
    
    def validate_full_system(self, inverter_assignments: Dict[str, float]) -> Dict[str, Any]:
        """
        Validate complete system with multiple inverters.
        
        Args:
            inverter_assignments: Dict mapping inverter_id to total DC power
            
        Returns:
            Validation summary for all inverters
        """
        results = {}
        all_valid = True
        
        for inv_id, dc_power in inverter_assignments.items():
            dc_ac_ratio = (dc_power / self.inverter_ac_power) if self.inverter_ac_power > 0 else 0
            
            if dc_ac_ratio <= self.target_dc_ac_ratio:
                status = "OPTIMAL"
                valid = True
            elif dc_ac_ratio <= self.max_dc_ac_ratio:
                status = "ACCEPTABLE"
                valid = True
            else:
                status = "OVERSIZED"
                valid = False
                all_valid = False
            
            results[inv_id] = {
                "dc_power_W": round(dc_power, 2),
                "ac_power_W": self.inverter_ac_power,
                "dc_ac_ratio": round(dc_ac_ratio, 2),
                "status": status,
                "valid": valid
            }
        
        return {
            "all_valid": all_valid,
            "inverters": results,
            "total_inverters": len(inverter_assignments),
            "optimal_count": sum(1 for r in results.values() if r["status"] == "OPTIMAL"),
            "acceptable_count": sum(1 for r in results.values() if r["status"] == "ACCEPTABLE"),
            "oversized_count": sum(1 for r in results.values() if r["status"] == "OVERSIZED")
        }


def create_power_validator(inverter_specs, panel_specs_sample, temperature_data,
                          target_ratio: float = 1.25, max_ratio: float = 1.5) -> PowerValidator:
    """
    Factory function to create a PowerValidator instance.
    
    Args:
        inverter_specs: Inverter specifications
        panel_specs_sample: Sample panel for power calculation
        temperature_data: Temperature data
        target_ratio: Target DC/AC ratio (default 1.25)
        max_ratio: Maximum DC/AC ratio (default 1.5)
        
    Returns:
        PowerValidator instance
    """
    return PowerValidator(
        inverter_specs, 
        panel_specs_sample, 
        temperature_data,
        target_ratio,
        max_ratio
    )

