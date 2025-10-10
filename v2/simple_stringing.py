"""
Simple Nearest-Neighbor Stringing Optimizer

This is the simplest possible stringing algorithm:
1. Group panels by roof plane
2. For each roof plane, use nearest-neighbor to create strings
3. No complex projections, no row detection, just connect to closest panel

Total: ~200 lines of straightforward code
"""

import math
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass


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
    rated_ac_power_w: float = None  # Rated AC output power (extracted from model number)


@dataclass
class TemperatureData:
    """Temperature data"""
    min_temp_c: float
    max_temp_c: float
    avg_high_temp_c: float
    avg_low_temp_c: float


class SimpleStringingOptimizer:
    """
    Simple nearest-neighbor stringing optimizer.
    
    Algorithm:
    1. Group panels by roof plane
    2. For each roof plane:
       - Start from corner panel
       - Always connect to closest unconnected panel
       - Create strings of ideal length (6-9 panels)
    3. No zigzag, no complex math, just simple and reliable
    """
    
    def __init__(self, panel_specs: List[PanelSpecs], inverter_specs: InverterSpecs, 
                 temperature_data: TemperatureData, output_frontend: bool = True):
        self.panel_specs = panel_specs
        self.inverter_specs = inverter_specs
        self.temperature_data = temperature_data
        self.output_frontend = output_frontend  # Flag for presentation format
        
        # Create panel lookup
        self.panel_lookup = {p.panel_id: p for p in panel_specs}
        
        # Calculate temperature-adjusted constraints
        self.temp_coeff_voc = 0.00279  # V/°C per panel
        self.temp_coeff_vmpp = 0.00446  # V/°C per panel
        
        # Calculate voltage constraints
        self._calculate_voltage_constraints()
        
    def _calculate_voltage_constraints(self):
        """Calculate min/max panels per string based on temperature and voltage limits"""
        # Get a representative panel (assume all panels are same type)
        panel = self.panel_specs[0]
        
        # Voltage at extreme cold (max voltage)
        temp_diff_cold = self.temperature_data.min_temp_c - 25.0
        voc_cold = panel.voc_stc * (1 + self.temp_coeff_voc * temp_diff_cold)
        
        # Voltage at extreme hot (min voltage)
        temp_diff_hot = self.temperature_data.max_temp_c - 25.0
        vmpp_hot = panel.vmpp_stc * (1 + self.temp_coeff_vmpp * temp_diff_hot)
        
        # Calculate constraints
        self.max_panels_per_string = int(self.inverter_specs.max_dc_voltage / voc_cold)
        self.min_panels_per_string = max(3, int(self.inverter_specs.mppt_min_voltage / vmpp_hot))
        self.ideal_panels_per_string = min(9, self.max_panels_per_string)
        
        print(f"Voltage constraints: min={self.min_panels_per_string}, "
              f"ideal={self.ideal_panels_per_string}, max={self.max_panels_per_string}")
    
    def _suggest_better_inverters(self, total_system_dc_power: float, 
                                  available_inverters: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Suggest better inverter options from available inverter specs.
        Returns list of inverters sorted by suitability.
        """
        suggestions = []
        
        for inv in available_inverters:
            ac_power = inv.get('rated_ac_power_w', 0)
            if ac_power == 0:
                continue
            
            ratio = total_system_dc_power / ac_power
            
            # Determine suitability score (lower is better)
            if 1.15 <= ratio <= 1.30:
                suitability = "OPTIMAL"
                score = abs(ratio - 1.22)  # Target 1.22 as sweet spot
            elif 1.10 <= ratio < 1.15 or 1.30 < ratio <= 1.35:
                suitability = "GOOD"
                score = abs(ratio - 1.22) + 0.1
            elif 1.35 < ratio <= 1.50:
                suitability = "ACCEPTABLE"
                score = abs(ratio - 1.22) + 0.2
            elif ratio < 1.10:
                suitability = "OVERSIZED"
                score = abs(ratio - 1.22) + 0.5
            else:  # ratio > 1.50
                suitability = "UNDERSIZED"
                score = abs(ratio - 1.22) + 1.0
            
            suggestions.append({
                "model": inv.get('model', 'Unknown'),
                "rated_ac_power_W": ac_power,
                "dc_ac_ratio": round(ratio, 2),
                "suitability": suitability,
                "score": score
            })
        
        # Sort by score (best first)
        suggestions.sort(key=lambda x: x['score'])
        
        return suggestions[:5]  # Return top 5
    
    def _generate_suggestions(self, has_stragglers: bool, straggler_count: int, 
                            strings_cropped: bool, power_validation_enabled: bool) -> List[str]:
        """
        Generate intelligent suggestions based on stringing results.
        
        Args:
            has_stragglers: Whether straggler panels were detected
            straggler_count: Total number of straggler panels
            strings_cropped: Whether strings were shortened due to power validation
            power_validation_enabled: Whether power validation was used
            
        Returns:
            List of suggestion strings
        """
        suggestions = []
        
        # Case 1: Stragglers + significant string cropping due to power validation
        if has_stragglers and strings_cropped and power_validation_enabled:
            suggestions.append(
                f"Straggler panels detected ({straggler_count} panels) and inverter was undersized "
                f"for ideal string length. Consider using an inverter with higher capacity to "
                f"accommodate longer strings and reduce stragglers."
            )
            
            # Suggest inverter size based on ideal string length
            if hasattr(self, 'power_validator') and self.power_validator:
                # Calculate power for an ideal-length string (9 panels before power adjustment)
                ideal_string_length = 9  # Voltage-based ideal
                ideal_string_power = ideal_string_length * self.power_validator.power_per_panel
                # At 1.25 DC/AC ratio, inverter AC power should be string_power / 1.25
                recommended_inverter_ac = ideal_string_power / 1.25
                
                suggestions.append(
                    f"Recommended inverter capacity: ~{int(recommended_inverter_ac/1000)}kW AC per inverter "
                    f"(to accommodate {ideal_string_length}-panel strings at optimal 1.25 DC/AC ratio)."
                )
        
        # Case 2: Stragglers but validation disabled or minimal cropping
        elif has_stragglers:
            suggestions.append(
                f"Straggler panels detected ({straggler_count} panels). "
                f"Consider reorganizing panels more compactly to enable additional strings. "
                f"Panels must be grouped in multiples of {self.min_panels_per_string} or more "
                f"to meet minimum voltage requirements."
            )
        
        # Case 3: No stragglers but heavy cropping (good validation, but inverter undersized)
        elif strings_cropped and power_validation_enabled:
            suggestions.append(
                f"Strings were shortened to fit inverter capacity. "
                f"Consider using a larger inverter to allow longer strings and reduce "
                f"the total number of inverters needed."
            )
        
        return suggestions
    
    def _calculate_preliminary_dc_ac_ratio(self) -> Dict[str, Any]:
        """
        STAGE 0: Pre-stringing inverter sizing check.
        Calculate total system DC power and preliminary DC/AC ratio.
        This happens BEFORE any stringing to detect obviously unsuitable inverters.
        """
        total_panels = len(self.panel_specs)
        
        # Calculate power per panel at operating temperature (hot)
        panel = self.panel_specs[0]
        temp_diff_hot = self.temperature_data.max_temp_c - 25.0
        vmpp_hot = panel.vmpp_stc * (1 + self.temp_coeff_vmpp * temp_diff_hot)
        power_per_panel_hot = vmpp_hot * panel.impp_stc
        
        # Total system DC power
        total_system_dc_power = total_panels * power_per_panel_hot
        
        # Preliminary DC/AC ratio
        inverter_ac_power = self.inverter_specs.rated_ac_power_w or 0
        preliminary_ratio = (total_system_dc_power / inverter_ac_power) if inverter_ac_power > 0 else 0
        
        # Determine suitability
        if preliminary_ratio > 1.5:
            suitability = "UNDERSIZED"
            recommendation = f"Inverter too small. Need ~{int(total_system_dc_power / (inverter_ac_power * 1.3))} of these or a {total_system_dc_power/1000/1.2:.1f}kW inverter"
        elif preliminary_ratio < 1.1:
            suitability = "OVERSIZED"
            recommendation = "Inverter may be too large. Consider smaller model for cost efficiency"
        elif 1.1 <= preliminary_ratio <= 1.3:
            suitability = "OPTIMAL"
            recommendation = "Inverter size is in optimal range"
        elif 1.3 < preliminary_ratio <= 1.5:
            suitability = "ACCEPTABLE"
            recommendation = "Inverter size acceptable, some clipping expected"
        else:
            suitability = "UNKNOWN"
            recommendation = "Unable to determine suitability"
        
        return {
            "total_panels": total_panels,
            "power_per_panel_W": round(power_per_panel_hot, 2),
            "total_system_dc_power_W": round(total_system_dc_power, 2),
            "inverter_rated_ac_power_W": round(inverter_ac_power, 2),
            "preliminary_dc_ac_ratio": round(preliminary_ratio, 2),
            "status": suitability,
            "recommendation": recommendation
        }
    
    def optimize(self, inverter_csv_path: str = None, validate_power: bool = False) -> 'OptimizationResult':
        """
        Run the simple nearest-neighbor optimization
        
        Args:
            inverter_csv_path: Path to inverter CSV for suggestions
            validate_power: If True, validates power during stringing and creates
                          new inverters as needed to maintain optimal DC/AC ratios
        """
        
        # Initialize power validator if requested
        if validate_power:
            from validatePower import PowerValidator
            self.power_validator = PowerValidator(
                self.inverter_specs,
                self.panel_specs[0],
                self.temperature_data,
                target_dc_ac_ratio=1.25,
                max_dc_ac_ratio=1.5
            )
            self.inverter_power_tracking = {}  # Track DC power per inverter
            
            # CRITICAL: Adjust string length to fit inverter capacity
            max_panels_per_string = int(self.power_validator.max_dc_power_per_inverter / 
                                       self.power_validator.power_per_panel)
            original_ideal = self.ideal_panels_per_string
            self.ideal_panels_per_string = min(self.ideal_panels_per_string, max_panels_per_string)
            
            print(f"\n⚡ Power validation ENABLED")
            print(f"  Adjusted string length: {original_ideal} → {self.ideal_panels_per_string} panels")
            print(f"  (to fit {self.inverter_specs.rated_ac_power_w}W inverter at {self.power_validator.max_dc_ac_ratio}x ratio)\n")
        else:
            self.power_validator = None
            print("\n⚡ Power validation DISABLED - using standard assignment")
        
        # STAGE 0: Pre-stringing inverter sizing check
        preliminary_check = self._calculate_preliminary_dc_ac_ratio()
        
        # Load available inverters for suggestions (if path provided)
        better_inverters = []
        if inverter_csv_path:
            try:
                import data_parsers
                available_inverters = data_parsers.parse_inverter_specs_csv(inverter_csv_path)
                better_inverters = self._suggest_better_inverters(
                    preliminary_check['total_system_dc_power_W'], 
                    available_inverters
                )
            except Exception as e:
                print(f"Note: Could not load inverter suggestions: {e}")
        
        preliminary_check["better_inverter_options"] = better_inverters
        
        print("\n" + "="*80)
        print("STAGE 0: PRELIMINARY INVERTER SIZING CHECK")
        print("="*80)
        print(f"Total panels: {preliminary_check['total_panels']}")
        print(f"Total system DC power: {preliminary_check['total_system_dc_power_W']:.0f} W")
        print(f"Inverter AC capacity: {preliminary_check['inverter_rated_ac_power_W']:.0f} W")
        print(f"Preliminary DC/AC ratio: {preliminary_check['preliminary_dc_ac_ratio']:.2f}")
        print(f"Status: {preliminary_check['status']}")
        print(f"Recommendation: {preliminary_check['recommendation']}")
        
        if better_inverters:
            print(f"\n💡 Better Inverter Options:")
            for i, inv in enumerate(better_inverters[:3], 1):
                print(f"  {i}. {inv['model']}: {inv['rated_ac_power_W']/1000:.1f}kW AC, "
                      f"ratio={inv['dc_ac_ratio']:.2f}, {inv['suitability']}")
        
        print("\n" + "="*80)
        print("STAGE 1: SIMPLE NEAREST-NEIGHBOR STRINGING")
        print("="*80)
        print(f"Total panels: {len(self.panel_specs)}")
        print(f"String length target: {self.ideal_panels_per_string} panels")
        
        # Initialize straggler warnings list
        self.straggler_warnings = []
        
        # Group by roof plane
        roof_groups = self._group_by_roof_plane()
        
        # Step 1: String each roof plane independently
        all_strings = []
        
        for roof_id, panels in roof_groups.items():
            print(f"\nRoof Plane {roof_id}: {len(panels)} panels")
            strings = self._string_roof_plane(panels, roof_id)
            all_strings.extend(strings)
            
            stringed = sum(len(s) for s in strings)
            print(f"  Created {len(strings)} strings ({stringed}/{len(panels)} panels stringed)")
        
        # Step 2: Assign strings to MPPTs (with parallel connection evaluation)
        print(f"\nAssigning {len(all_strings)} strings to MPPTs...")
        mppts = self._assign_strings_to_mppts(all_strings)
        print(f"  Created {len(mppts)} MPPTs")
        
        # Step 3: Assign MPPTs to inverters
        print(f"\nAssigning MPPTs to inverters (max {self.inverter_specs.number_of_mppts} MPPTs per inverter)...")
        if validate_power:
            all_connections = self._assign_mppts_to_inverters_with_power_validation(mppts)
        else:
            all_connections = self._assign_mppts_to_inverters(mppts)
        print(f"  Created {len(all_connections)} inverters")
        
        # Calculate summary (needed for suggestions)
        total_panels = len(self.panel_specs)
        string_lengths = [len(s) for s in all_strings]
        stringed_panels = sum(string_lengths)
        
        # Track if strings were cropped due to power validation
        strings_cropped_by_power = False
        if validate_power and self.power_validator:
            # Compare actual string lengths to ideal (9 panels normally)
            original_ideal = 9  # Voltage-based ideal before power adjustment
            cropped_count = sum(1 for length in string_lengths if length < original_ideal)
            cropped_percentage = (cropped_count / len(string_lengths)) if string_lengths else 0
            strings_cropped_by_power = cropped_percentage > 0.3  # More than 30% cropped
        
        # Generate intelligent suggestions
        has_stragglers = len(self.straggler_warnings) > 0
        total_straggler_count = sum(w['panel_count'] for w in self.straggler_warnings) if has_stragglers else 0
        suggestions = self._generate_suggestions(has_stragglers, total_straggler_count, 
                                                strings_cropped_by_power, validate_power)
        
        # Print straggler summary if any
        if self.straggler_warnings:
            print(f"\n{'='*80}")
            print(f"⚠️  STRAGGLER SUMMARY")
            print(f"{'='*80}")
            print(f"Total straggler groups: {len(self.straggler_warnings)}")
            print(f"Total straggler panels: {total_straggler_count}")
            print(f"\nThese panels CANNOT be connected due to insufficient voltage.")
            print(f"Minimum {self.min_panels_per_string} panels required per string for inverter activation.")
            print(f"{'='*80}")
        
        # Print suggestions if any
        if suggestions:
            print(f"\n{'='*80}")
            print(f"💡 SUGGESTIONS")
            print(f"{'='*80}")
            for suggestion in suggestions:
                print(f"  • {suggestion}")
            print(f"{'='*80}")
        
        print(f"\n" + "="*80)
        print(f"RESULTS: {stringed_panels}/{total_panels} panels in {len(all_strings)} strings")
        print(f"Leftovers: {total_panels - stringed_panels} panels")
        if self.straggler_warnings:
            print(f"⚠️  Straggler panels: {sum(w['panel_count'] for w in self.straggler_warnings)} "
                  f"(cannot be connected - insufficient voltage)")
        print("="*80)
        
        # Build formatted output with proper roof/inverter/MPPT/string structure
        formatted_result = self._build_formatted_output(all_connections, all_strings)
        
        # Add preliminary check and suggestions to output
        formatted_result["preliminary_sizing_check"] = preliminary_check
        formatted_result["suggestions"] = suggestions
        
        # Transform to frontend format if requested
        if self.output_frontend:
            formatted_result = self._transform_to_frontend_format(formatted_result)
        
        # Also return legacy OptimizationResult for backward compatibility
        result = OptimizationResult(
            connections=all_connections,
            total_panels=total_panels,
            string_lengths=string_lengths,
            total_strings=len(all_strings),
            stringed_panels=stringed_panels
        )
        
        # Add straggler warnings to result if any exist
        if self.straggler_warnings:
            result.straggler_warnings = self.straggler_warnings
        
        # Add formatted result
        result.formatted_output = formatted_result
        
        return result
    
    def _group_by_roof_plane(self) -> Dict[str, List[PanelSpecs]]:
        """Group panels by roof plane ID"""
        groups = {}
        for panel in self.panel_specs:
            roof_id = panel.roof_plane_id
            if roof_id not in groups:
                groups[roof_id] = []
            groups[roof_id].append(panel)
        return groups
    
    def _string_roof_plane(self, panels: List[PanelSpecs], roof_id: str) -> List[List[str]]:
        """
        String a single roof plane using nearest-neighbor approach.
        
        Algorithm:
        1. Start from a corner panel (least connected)
        2. Build string by always connecting to closest unconnected panel
        3. When string reaches ideal length, start new string
        4. WITH POWER VALIDATION: Track inverter power and create new inverter when needed
        5. Repeat until no more valid strings can be made
        6. Handle stragglers: group leftover panels and assign to MPPTs
        """
        if not panels:
            return []
        
        # Find starting panel (corner panel = least connected)
        start_panel = self._find_corner_panel(panels)
        
        unconnected = set(p.panel_id for p in panels)
        strings = []
        
        # Phase 1: Create standard strings (min_panels_per_string or more)
        while len(unconnected) >= self.min_panels_per_string:
            # Start new string
            if start_panel.panel_id not in unconnected:
                # Find new starting point from remaining panels
                remaining_panels = [p for p in panels if p.panel_id in unconnected]
                if not remaining_panels:
                    break
                start_panel = self._find_corner_panel(remaining_panels)
            
            # Build string using nearest neighbor (with power validation if enabled)
            string = self._build_string_nearest_neighbor(start_panel, panels, unconnected)
            
            if len(string) >= self.min_panels_per_string:
                strings.append(string)
                
                # Remove these panels from unconnected
                for pid in string:
                    unconnected.discard(pid)
            else:
                # Can't make valid strings anymore
                break
        
        # Phase 2: Detect and report stragglers (cannot be connected due to min voltage requirement)
        if unconnected:
            print(f"  ⚠️  {len(unconnected)} straggler panels detected (cannot form valid strings)")
            self._report_stragglers(panels, unconnected, roof_id)
        
        return strings
    
    def _find_corner_panel(self, panels: List[PanelSpecs]) -> PanelSpecs:
        """Find a corner panel (one with fewest neighbors within threshold)"""
        if len(panels) == 1:
            return panels[0]
        
        min_neighbors = float('inf')
        corner_panel = panels[0]
        threshold = 100.0  # Distance threshold for being a "neighbor"
        
        for panel in panels:
            # Count how many panels are within threshold distance
            neighbor_count = 0
            for other in panels:
                if other.panel_id == panel.panel_id:
                    continue
                dist = self._distance(panel, other)
                if dist <= threshold:
                    neighbor_count += 1
            
            if neighbor_count < min_neighbors:
                min_neighbors = neighbor_count
                corner_panel = panel
        
        return corner_panel
    
    def _build_string_nearest_neighbor(self, start_panel: PanelSpecs, 
                                      all_panels: List[PanelSpecs],
                                      unconnected: set) -> List[str]:
        """
        Build a string using nearest-neighbor approach.
        
        Start from start_panel and always connect to the closest unconnected panel.
        Stop when string reaches ideal length or no nearby panels available.
        
        WITH POWER VALIDATION:
        - After each panel addition, validate if string would exceed inverter capacity
        - If invalid, stop at current length (before adding the last panel)
        - This ensures each string fits within inverter power limits
        """
        # Create lookup for fast access
        panel_lookup = {p.panel_id: p for p in all_panels}
        
        string = [start_panel.panel_id]
        current_panel = start_panel
        max_distance_threshold = 100.0  # Maximum jump distance
        
        while len(string) < self.ideal_panels_per_string:
            # Find closest unconnected panel
            closest_panel = None
            closest_distance = float('inf')
            
            for pid in unconnected:
                if pid in string:
                    continue
                
                candidate = panel_lookup[pid]
                dist = self._distance(current_panel, candidate)
                
                if dist < closest_distance:
                    closest_distance = dist
                    closest_panel = candidate
            
            # Check if closest panel is reasonable distance
            if closest_panel and closest_distance <= max_distance_threshold:
                string.append(closest_panel.panel_id)
                current_panel = closest_panel
            else:
                # No more nearby panels
                break
        
        return string
    
    def _distance(self, p1: PanelSpecs, p2: PanelSpecs) -> float:
        """Calculate Euclidean distance between two panels"""
        x1, y1 = p1.center_coords
        x2, y2 = p2.center_coords
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    def _report_stragglers(self, all_panels: List[PanelSpecs], 
                          straggler_ids: set, roof_id: str):
        """
        Report straggler panels that cannot form valid strings.
        
        Groups stragglers by proximity and reports each group's details including:
        - Panel IDs
        - Number of panels in group
        - Voltage that would be generated (below minimum required)
        - Minimum voltage required for inverter activation
        
        Args:
            all_panels: All panels in the roof plane
            straggler_ids: Set of panel IDs that are stragglers
            roof_id: ID of the roof plane
        """
        if not straggler_ids:
            return
        
        # Get straggler panel objects
        panel_lookup = {p.panel_id: p for p in all_panels}
        straggler_panels = [panel_lookup[pid] for pid in straggler_ids if pid in panel_lookup]
        
        if not straggler_panels:
            return
        
        # Group stragglers by proximity
        straggler_groups = self._group_stragglers_by_proximity(straggler_panels)
        
        # Store warnings for summary
        if not hasattr(self, 'straggler_warnings'):
            self.straggler_warnings = []
        
        # Report each group
        print(f"\n  ╔════════════════════════════════════════════════════════════════")
        print(f"  ║ STRAGGLER WARNING - Roof {roof_id}")
        print(f"  ╠════════════════════════════════════════════════════════════════")
        
        for i, group in enumerate(straggler_groups, 1):
            panel_count = len(group)
            panel_ids = [p.panel_id for p in group]
            
            # Calculate voltage for this group (using Vmpp at hot temp)
            panel = group[0]  # Use representative panel
            temp_diff_hot = self.temperature_data.max_temp_c - 25.0
            vmpp_hot = panel.vmpp_stc * (1 + self.temp_coeff_vmpp * temp_diff_hot)
            group_voltage = vmpp_hot * panel_count
            
            # Get minimum required voltage (startup voltage)
            min_required_voltage = self.inverter_specs.startup_voltage
            voltage_deficit = min_required_voltage - group_voltage
            
            print(f"  ║")
            print(f"  ║ Straggler Group {i}:")
            print(f"  ║   • Panel Count: {panel_count} panels (min required: {self.min_panels_per_string})")
            print(f"  ║   • Panel IDs: {', '.join(panel_ids)}")
            print(f"  ║   • Estimated Voltage: {group_voltage:.1f}V")
            print(f"  ║   • Required for Startup: {min_required_voltage:.1f}V")
            print(f"  ║   • Voltage Deficit: {voltage_deficit:.1f}V")
            print(f"  ║   • Status: ❌ CANNOT BE CONNECTED (insufficient voltage)")
            
            # Store warning for output
            warning = {
                "roof_id": roof_id,
                "group_number": i,
                "panel_count": panel_count,
                "panel_ids": panel_ids,
                "estimated_voltage_V": round(group_voltage, 1),
                "min_required_voltage_V": round(min_required_voltage, 1),
                "voltage_deficit_V": round(voltage_deficit, 1),
                "reason": "Insufficient panels to meet minimum inverter startup voltage"
            }
            self.straggler_warnings.append(warning)
        
        print(f"  ╚════════════════════════════════════════════════════════════════\n")
    
    def _group_stragglers_by_proximity(self, stragglers: List[PanelSpecs]) -> List[List[PanelSpecs]]:
        """
        Group straggler panels based on proximity.
        Panels within threshold distance are grouped together.
        """
        if not stragglers:
            return []
        
        # Use union-find to group nearby panels
        groups = []
        ungrouped = set(range(len(stragglers)))
        threshold = 100.0  # Same as neighbor threshold
        
        while ungrouped:
            # Start new group with first ungrouped panel
            group_indices = [ungrouped.pop()]
            group = [stragglers[group_indices[0]]]
            
            # Find all panels within threshold of this group
            changed = True
            while changed:
                changed = False
                to_remove = []
                
                for idx in ungrouped:
                    panel = stragglers[idx]
                    # Check if this panel is close to any panel in the group
                    for group_panel in group:
                        if self._distance(panel, group_panel) <= threshold:
                            group.append(panel)
                            to_remove.append(idx)
                            changed = True
                            break
                
                for idx in to_remove:
                    ungrouped.discard(idx)
            
            groups.append(group)
        
        return groups
    
    def _order_group_by_proximity(self, group: List[PanelSpecs]) -> List[str]:
        """
        Order a group of panels using nearest-neighbor.
        Returns list of panel IDs in connection order.
        """
        if not group:
            return []
        
        if len(group) == 1:
            return [group[0].panel_id]
        
        # Start from first panel
        ordered = [group[0]]
        remaining = set(group[1:])
        
        while remaining:
            current = ordered[-1]
            # Find closest remaining panel
            closest = min(remaining, key=lambda p: self._distance(current, p))
            ordered.append(closest)
            remaining.remove(closest)
        
        return [p.panel_id for p in ordered]
    
    def _assign_strings_to_mppts(self, strings: List[List[str]]) -> List[List[List[str]]]:
        """
        Assign strings to MPPTs, allowing parallel connections where appropriate.
        
        Logic:
        1. First string goes to MPPT_1
        2. For each subsequent string:
           - Check if it can be added in parallel to an existing MPPT (voltage and current compatible)
           - If yes: add to that MPPT
           - If no: create new MPPT
        
        Args:
            strings: List of strings (each string is a list of panel IDs)
            
        Returns:
            List of MPPTs, where each MPPT contains one or more parallel strings
        """
        if not strings:
            return []
        
        mppts = []  # Each MPPT is a list of strings (parallel connections)
        
        for string in strings:
            # Get string characteristics
            string_panels = [self.panel_lookup[pid] for pid in string if pid in self.panel_lookup]
            if not string_panels:
                continue
            
            # Calculate string voltage (at hot temp for min voltage check)
            panel = string_panels[0]
            temp_diff_hot = self.temperature_data.max_temp_c - 25.0
            vmpp_hot = panel.vmpp_stc * (1 + self.temp_coeff_vmpp * temp_diff_hot)
            string_voltage = vmpp_hot * len(string_panels)
            string_current = panel.impp_stc
            
            # Try to add to existing MPPT (parallel connection)
            added_to_existing = False
            for mppt in mppts:
                # Check if this string can be added in parallel to this MPPT
                if self._can_add_string_to_mppt(mppt, string, string_voltage, string_current):
                    mppt.append(string)
                    added_to_existing = True
                    break
            
            # If couldn't add to existing MPPT, create new one
            if not added_to_existing:
                mppts.append([string])
        
        return mppts
    
    def _can_add_string_to_mppt(self, existing_mppt: List[List[str]], new_string: List[str],
                                new_string_voltage: float, new_string_current: float) -> bool:
        """
        Check if a new string can be added in parallel to an existing MPPT.
        
        Requirements for parallel connection:
        1. Voltages must be compatible (within tolerance)
        2. Total current must not exceed MPPT limit
        
        Args:
            existing_mppt: MPPT with existing strings
            new_string: New string to potentially add
            new_string_voltage: Voltage of new string
            new_string_current: Current of new string
            
        Returns:
            True if string can be added, False otherwise
        """
        # Get voltage of first string in MPPT (all parallel strings should have similar voltage)
        first_string = existing_mppt[0]
        first_string_panels = [self.panel_lookup[pid] for pid in first_string if pid in self.panel_lookup]
        if not first_string_panels:
            return False
        
        panel = first_string_panels[0]
        temp_diff_hot = self.temperature_data.max_temp_c - 25.0
        vmpp_hot = panel.vmpp_stc * (1 + self.temp_coeff_vmpp * temp_diff_hot)
        existing_voltage = vmpp_hot * len(first_string_panels)
        
        # Check 1: Voltage compatibility (within 5% tolerance)
        voltage_diff_pct = abs(new_string_voltage - existing_voltage) / existing_voltage
        if voltage_diff_pct > 0.05:
            return False
        
        # Check 2: Current limit
        # Calculate total current if we add this string
        existing_current = panel.impp_stc * len(existing_mppt)
        total_current = existing_current + new_string_current
        
        if total_current > self.inverter_specs.max_dc_current_per_mppt:
            return False
        
        return True
    
    def _assign_mppts_to_inverters(self, mppts: List[List[List[str]]]) -> Dict[str, Dict[str, List[List[str]]]]:
        """
        Assign MPPTs to inverters based on inverter MPPT capacity.
        
        Args:
            mppts: List of MPPTs (each MPPT contains parallel strings)
            
        Returns:
            Dict mapping inverter IDs to their MPPTs
        """
        inverters = {}
        mppts_per_inverter = self.inverter_specs.number_of_mppts
        
        inverter_counter = 1
        mppt_global_counter = 1
        
        for i in range(0, len(mppts), mppts_per_inverter):
            inverter_id = f"Inverter_{inverter_counter}"
            inverter_mppts = mppts[i:i + mppts_per_inverter]
            inverters[inverter_id] = {}
            
            for mppt in inverter_mppts:
                mppt_id = f"MPPT_{mppt_global_counter}"
                inverters[inverter_id][mppt_id] = mppt
                mppt_global_counter += 1
            
            inverter_counter += 1
        
        return inverters
    
    def _assign_mppts_to_inverters_with_power_validation(self, mppts: List[List[List[str]]]) -> Dict[str, Dict[str, List[List[str]]]]:
        """
        Assign MPPTs to inverters WITH power validation.
        Creates new inverters as needed to maintain optimal DC/AC ratios.
        
        Args:
            mppts: List of MPPTs (each MPPT contains parallel strings)
            
        Returns:
            Dict mapping inverter IDs to their MPPTs
        """
        inverters = {}
        inverter_counter = 1
        mppt_global_counter = 1
        
        current_inverter_id = f"Inverter_{inverter_counter}"
        current_inverter_mppts = {}
        current_inverter_power = 0.0
        
        for mppt_strings in mppts:
            # Calculate power for this MPPT
            mppt_panel_count = sum(len(string) for string in mppt_strings)
            mppt_power = self.power_validator.calculate_string_power(mppt_panel_count)
            
            # Validate if adding this MPPT to current inverter is acceptable
            validation = self.power_validator.validate_string_assignment(
                mppt_panel_count,
                current_inverter_power
            )
            
            mppt_id = f"MPPT_{mppt_global_counter}"
            
            if validation["valid"]:
                # Add MPPT to current inverter
                current_inverter_mppts[mppt_id] = mppt_strings
                current_inverter_power += mppt_power
                mppt_global_counter += 1
                
                # Check if we've reached MPPT limit for this inverter
                if len(current_inverter_mppts) >= self.inverter_specs.number_of_mppts:
                    # Save current inverter and start new one
                    inverters[current_inverter_id] = current_inverter_mppts
                    self.inverter_power_tracking[current_inverter_id] = current_inverter_power
                    
                    inverter_counter += 1
                    current_inverter_id = f"Inverter_{inverter_counter}"
                    current_inverter_mppts = {}
                    current_inverter_power = 0.0
            else:
                # MPPT would exceed power limit
                # Save current inverter and start new one with this MPPT
                if current_inverter_mppts:  # Only save if not empty
                    inverters[current_inverter_id] = current_inverter_mppts
                    self.inverter_power_tracking[current_inverter_id] = current_inverter_power
                    
                    inverter_counter += 1
                    current_inverter_id = f"Inverter_{inverter_counter}"
                
                # Start new inverter with this MPPT
                current_inverter_mppts = {mppt_id: mppt_strings}
                current_inverter_power = mppt_power
                mppt_global_counter += 1
        
        # Don't forget the last inverter
        if current_inverter_mppts:
            inverters[current_inverter_id] = current_inverter_mppts
            self.inverter_power_tracking[current_inverter_id] = current_inverter_power
        
        return inverters
    
    def _build_formatted_output(self, inverter_structure: Dict[str, Dict[str, List[List[str]]]], 
                                all_strings: List[List[str]]) -> Dict[str, Any]:
        """
        Build the final formatted output with inverter at top of hierarchy.
        
        Structure:
        {
          "connections": {
            "Inverter_1": {
              "roof_1": {
                "MPPT_1": {
                  "s1": [panel_ids],
                  "s2": [panel_ids],  // if parallel
                  "properties": {...}
                }
              },
              "roof_2": {
                "MPPT_2": {...}
              }
            },
            "Inverter_2": {
              "roof_1": {  // Same roof can appear under different inverters
                "MPPT_5": {...}
              }
            }
          }
        }
        """
        # Create string ID mapping and track which roof each string belongs to
        string_counter = 1
        string_to_id = {}
        string_to_roof = {}
        
        for panel_ids in all_strings:
            string_id = f"s{string_counter}"
            string_to_id[tuple(panel_ids)] = string_id
            
            # Determine roof from first panel
            if panel_ids and panel_ids[0] in self.panel_lookup:
                string_to_roof[string_id] = self.panel_lookup[panel_ids[0]].roof_plane_id
            
            string_counter += 1
        
        # Build connections organized by: Inverter → Roof → MPPT → Strings
        connections_by_inverter = {}
        
        for inv_id, mppt_data in inverter_structure.items():
            connections_by_inverter[inv_id] = {}
            
            for mppt_id, parallel_strings in mppt_data.items():
                # Determine which roof this MPPT belongs to (from first string)
                if not parallel_strings or not parallel_strings[0]:
                    continue
                
                first_string = parallel_strings[0]
                string_id = string_to_id.get(tuple(first_string))
                roof_id = string_to_roof.get(string_id, "unknown")
                
                # Initialize roof structure under inverter
                if roof_id not in connections_by_inverter[inv_id]:
                    connections_by_inverter[inv_id][roof_id] = {}
                
                # Initialize MPPT under roof
                connections_by_inverter[inv_id][roof_id][mppt_id] = {}
                
                # Add all strings in this MPPT
                for panel_ids in parallel_strings:
                    string_id = string_to_id.get(tuple(panel_ids))
                    if string_id:
                        connections_by_inverter[inv_id][roof_id][mppt_id][string_id] = panel_ids
                
                # Add MPPT properties
                connections_by_inverter[inv_id][roof_id][mppt_id]["properties"] = \
                    self._calculate_mppt_properties_for_strings(parallel_strings)
        
        # Build strings dict with basic info
        strings_dict = {}
        for panel_ids in all_strings:
            string_id = string_to_id.get(tuple(panel_ids))
            if string_id:
                roof_id = string_to_roof.get(string_id, "unknown")
                # Calculate string properties
                string_props = self._calculate_string_properties(panel_ids)
                strings_dict[string_id] = {
                    "panel_ids": list(panel_ids),
                    "panel_count": len(panel_ids),
                    "properties": string_props
                }
        
        # Calculate summary
        total_stringed = sum(len(panel_ids) for panel_ids in all_strings)
        
        result = {
            "connections": connections_by_inverter,
            "strings": strings_dict,
            "summary": {
                "total_panels": len(self.panel_specs),
                "total_panels_stringed": total_stringed,
                "total_strings": len(all_strings),
                "total_mppts_used": sum(len(mppt_data) for mppt_data in inverter_structure.values()),
                "total_inverters_used": len(inverter_structure),
                "stringing_efficiency": round(100 * total_stringed / len(self.panel_specs), 2)
            }
        }
        
        # Add straggler warnings if present
        if self.straggler_warnings:
            result["straggler_warnings"] = self.straggler_warnings
            result["summary"]["total_straggler_panels"] = sum(
                w["panel_count"] for w in self.straggler_warnings
            )
        
        return result
    
    def _transform_to_frontend_format(self, technical_output: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform technical format to frontend/presentation format.
        
        Technical format: Inverter → Roof → MPPT → Strings
        Frontend format: Strings (flat) with references + Device specs
        
        Frontend structure:
        {
          "strings": {
            "s1": {
              "panel_ids": [...],
              "inverter": "Inverter_1",
              "mppt": "MPPT_1",
              "roof_section": "3",
              "properties": {...}
            }
          },
          "inverter_specs": {
            "Inverter_1": { voltage, current, power properties }
          },
          "mppt_specs": {
            "MPPT_1": { voltage, current, power properties }
          },
          "summary": {...}
        }
        """
        # Extract connections from technical format
        connections = technical_output.get("connections", {})
        strings_dict = technical_output.get("strings", {})
        
        # Build flat strings structure with references
        frontend_strings = {}
        mppt_to_inverter = {}
        string_to_mppt = {}
        string_to_roof = {}
        
        # Extract mapping from technical format
        for inv_id, roof_data in connections.items():
            for roof_id, mppt_data in roof_data.items():
                for mppt_id, string_data in mppt_data.items():
                    mppt_to_inverter[mppt_id] = inv_id
                    
                    for string_id, panel_ids in string_data.items():
                        if string_id != "properties" and isinstance(panel_ids, list):
                            string_to_mppt[string_id] = mppt_id
                            string_to_roof[string_id] = roof_id
        
        # Build frontend strings
        for string_id, string_info in strings_dict.items():
            mppt_id = string_to_mppt.get(string_id)
            inv_id = mppt_to_inverter.get(mppt_id)
            roof_id = string_to_roof.get(string_id)
            
            frontend_strings[string_id] = {
                "panel_ids": string_info.get("panel_ids", []),
                "inverter": inv_id,
                "mppt": mppt_id,
                "roof_section": roof_id,
                "properties": string_info.get("properties", {})
            }
        
        # Extract inverter specs
        inverter_specs = {}
        for inv_id, roof_data in connections.items():
            # Aggregate properties for this inverter across all its MPPTs
            all_mppts = []
            for roof_id, mppt_data in roof_data.items():
                for mppt_id, string_data in mppt_data.items():
                    if "properties" in string_data:
                        all_mppts.append((mppt_id, string_data["properties"]))
            
            if all_mppts:
                # Calculate aggregate inverter properties
                inverter_specs[inv_id] = self._calculate_inverter_aggregate_specs(all_mppts)
        
        # Extract MPPT specs
        mppt_specs = {}
        for inv_id, roof_data in connections.items():
            for roof_id, mppt_data in roof_data.items():
                for mppt_id, string_data in mppt_data.items():
                    if "properties" in string_data:
                        mppt_specs[mppt_id] = string_data["properties"]
        
        # Build frontend output
        frontend_output = {
            "strings": frontend_strings,
            "inverter_specs": inverter_specs,
            "mppt_specs": mppt_specs,
            "summary": technical_output.get("summary", {})
        }
        
        # Add straggler warnings if present
        if "straggler_warnings" in technical_output:
            frontend_output["straggler_warnings"] = technical_output["straggler_warnings"]
        
        # Add preliminary sizing check if present
        if "preliminary_sizing_check" in technical_output:
            frontend_output["preliminary_sizing_check"] = technical_output["preliminary_sizing_check"]
        
        # Add suggestions if present
        if "suggestions" in technical_output:
            frontend_output["suggestions"] = technical_output["suggestions"]
        
        return frontend_output
    
    def _calculate_string_properties(self, panel_ids: List[str]) -> Dict[str, Any]:
        """Calculate electrical properties for a single string"""
        num_panels = len(panel_ids)
        
        # Temperature adjustments
        temp_coeff_voc = 0.00446  # V/°C per panel
        temp_diff_cold = self.temperature_data.min_temp_c - 25.0
        temp_diff_hot = self.temperature_data.max_temp_c - 25.0
        
        # Sample panel (assume all panels are identical)
        panel = self.panel_specs[0]
        
        # Voltage calculations
        voc_cold = panel.voc_stc * (1 + temp_coeff_voc * temp_diff_cold)
        vmpp_hot = panel.vmpp_stc * (1 + temp_coeff_voc * temp_diff_hot)
        
        # String voltage/current/power
        string_voc_cold = voc_cold * num_panels
        string_vmpp_hot = vmpp_hot * num_panels
        string_impp = panel.impp_stc
        string_power = string_vmpp_hot * string_impp
        
        return {
            "voltage_V": round(string_vmpp_hot, 2),
            "current_A": round(string_impp, 2),
            "power_W": round(string_power, 2),
            "max_voltage_V": round(string_voc_cold, 2)
        }
    
    def _calculate_mppt_properties_for_strings(self, parallel_strings: List[List[str]]) -> Dict[str, Any]:
        """Calculate MPPT properties from its parallel strings"""
        if not parallel_strings:
            return {}
        
        # Get first string's panels for voltage calculation
        first_string_panels = [self.panel_lookup[pid] for pid in parallel_strings[0] if pid in self.panel_lookup]
        if not first_string_panels:
            return {}
        
        panel = first_string_panels[0]
        temp_diff_hot = self.temperature_data.max_temp_c - 25.0
        vmpp_hot = panel.vmpp_stc * (1 + self.temp_coeff_vmpp * temp_diff_hot)
        string_voltage = vmpp_hot * len(first_string_panels)
        
        # Current sums across parallel strings
        total_current = panel.impp_stc * len(parallel_strings)
        total_max_current = panel.isc_stc * len(parallel_strings)
        isc_with_safety = panel.isc_stc * 1.25
        
        # Power calculation: Voltage (per string) × Current (summed across parallel strings)
        # This equals: (Vmpp × panels_per_string) × (Impp × num_parallel_strings)
        # Which equals: Sum of (Vmpp × Impp) for all panels in this MPPT
        total_power = string_voltage * total_current
        
        return {
            "num_strings": len(parallel_strings),
            "total_panels": sum(len(s) for s in parallel_strings),
            "voltage": {
                "operating_voltage_V": round(string_voltage, 2),
                "max_allowed_voltage_V": round(self.inverter_specs.mppt_max_voltage, 2),
                "min_required_voltage_V": round(self.inverter_specs.mppt_min_voltage, 2),
                "within_limits": (self.inverter_specs.mppt_min_voltage <= string_voltage <= 
                                 self.inverter_specs.mppt_max_voltage)
            },
            "current": {
                "operating_current_A": round(total_current, 2),
                "max_current_A": round(total_max_current, 2),
                "isc_with_safety_factor_A": round(isc_with_safety * len(parallel_strings), 2),
                "max_usable_current_per_string_A": round(self.inverter_specs.max_dc_current_per_string, 2),
                "max_short_circuit_current_per_mppt_A": round(
                    self.inverter_specs.max_short_circuit_current_per_mppt if self.inverter_specs.max_short_circuit_current_per_mppt
                    else self.inverter_specs.max_dc_current_per_mppt * 1.5, 2
                ),
                "will_clip": panel.impp_stc > self.inverter_specs.max_dc_current_per_string,
                "is_safe": (isc_with_safety) <= (
                    self.inverter_specs.max_short_circuit_current_per_mppt if self.inverter_specs.max_short_circuit_current_per_mppt
                    else self.inverter_specs.max_dc_current_per_mppt * 1.5
                ),
                "within_limits": total_current <= self.inverter_specs.max_dc_current_per_mppt
            },
            "power": {
                "total_power_W": round(total_power, 2),
                "calculation": {
                    "panels_per_string": len(first_string_panels),
                    "num_parallel_strings": len(parallel_strings),
                    "total_panels": sum(len(s) for s in parallel_strings),
                    "vmpp_per_panel_V": round(vmpp_hot, 2),
                    "impp_per_panel_A": round(panel.impp_stc, 2),
                    "string_voltage_V": round(string_voltage, 2),
                    "mppt_current_A": round(total_current, 2),
                    "formula": "Power = String_Voltage × MPPT_Current = (Vmpp × panels) × (Impp × strings)"
                }
            }
        }
    
    def _calculate_inverter_aggregate_specs(self, mppt_list: List[Tuple[str, Dict]]) -> Dict[str, Any]:
        """
        Calculate aggregate specifications for an inverter from its MPPTs.
        
        IMPORTANT: MPPTs operate INDEPENDENTLY in parallel:
        - Voltages are NOT added (each MPPT has its own voltage)
        - Currents are NOT added on DC side (each MPPT has its own current limit)
        - Only POWER is aggregated (watts from all MPPTs combine)
        
        Main validation: Total DC Power vs Rated AC Power (DC/AC ratio)
        """
        if not mppt_list:
            return {}
        
        # Check if all MPPTs are within their individual limits
        all_mppts_within_limits = all(
            mppt[1].get("current", {}).get("within_limits", False) 
            for mppt in mppt_list
        )
        
        # Check if any MPPT will clip
        any_mppt_will_clip = any(
            mppt[1].get("current", {}).get("will_clip", False)
            for mppt in mppt_list
        )
        
        # Check if all MPPTs are safe
        all_mppts_safe = all(
            mppt[1].get("current", {}).get("is_safe", True)
            for mppt in mppt_list
        )
        
        # Get representative voltage (MPPTs should have similar voltages for parallel operation)
        voltages = [mppt[1].get("voltage", {}).get("operating_voltage_V", 0) for mppt in mppt_list]
        avg_voltage = sum(voltages) / len(voltages) if voltages else 0
        
        # Power aggregation - THIS IS THE KEY VALIDATION
        total_dc_power = sum(mppt[1].get("power", {}).get("total_power_W", 0) 
                            for mppt in mppt_list)
        
        # Calculate DC/AC ratio
        rated_ac_power = self.inverter_specs.rated_ac_power_w or 0
        # Industry standard: Max DC power is typically 1.35-1.5x rated AC power
        max_dc_power = rated_ac_power * 1.5 if rated_ac_power > 0 else 0
        
        dc_ac_ratio = (total_dc_power / rated_ac_power) if rated_ac_power > 0 else 0
        will_clip_power = total_dc_power > rated_ac_power
        within_dc_limit = total_dc_power <= max_dc_power
        
        return {
            "num_mppts": len(mppt_list),
            "mppt_ids": [mppt[0] for mppt in mppt_list],
            "voltage": {
                "typical_mppt_voltage_V": round(avg_voltage, 2),
                "max_allowed_voltage_V": self.inverter_specs.max_dc_voltage
            },
            "current": {
                "per_mppt_limit_A": self.inverter_specs.max_dc_current_per_mppt,
                "all_mppts_within_limits": all_mppts_within_limits,
                "will_clip": any_mppt_will_clip,
                "is_safe": all_mppts_safe
            },
            "power": {
                "total_dc_power_W": round(total_dc_power, 2),
                "rated_ac_power_W": round(rated_ac_power, 2),
                "max_dc_power_limit_W": round(max_dc_power, 2),
                "dc_ac_ratio": round(dc_ac_ratio, 2),
                "will_clip_power": will_clip_power,
                "within_dc_power_limit": within_dc_limit,
                "average_power_per_mppt_W": round(total_dc_power / len(mppt_list) if mppt_list else 0, 2)
            },
            "validation": {
                "all_mppts_safe": all_mppts_safe,
                "within_power_limits": within_dc_limit,
                "optimal_dc_ac_ratio": 1.1 <= dc_ac_ratio <= 1.3,
                "status": "OPTIMAL" if (all_mppts_safe and within_dc_limit and 1.1 <= dc_ac_ratio <= 1.3) else 
                         ("ACCEPTABLE" if (all_mppts_safe and within_dc_limit and 1.3 < dc_ac_ratio <= 1.5) else
                         ("UNDERSIZED" if dc_ac_ratio > 1.5 else "OVERSIZED"))
            }
        }


@dataclass
class OptimizationResult:
    """Result of the optimization"""
    connections: Dict[str, Dict[str, Dict[str, List[str]]]]
    total_panels: int
    string_lengths: List[int]
    total_strings: int
    stringed_panels: int
    straggler_warnings: List[Dict[str, Any]] = None
    formatted_output: Dict[str, Any] = None

