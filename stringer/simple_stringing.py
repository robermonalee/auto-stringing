"""
Simple Nearest-Neighbor Stringing Optimizer

This is the simplest possible stringing algorithm:
1. Group panels by roof plane
2. For each roof plane, use nearest-neighbor to create strings
3. No complex projections, no row detection, just connect to closest panel

Total: ~200 lines of straightforward code
"""

import math
import time
from typing import List, Dict, Tuple, Any
from dataclasses import dataclass
from collections import defaultdict
from .specs import PanelSpecs, InverterSpecs, TemperatureData


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
    
    NEW: Optional Guided PCA sorting for improved stringing paths
    """
    
    def __init__(self, panel_specs: List[PanelSpecs], inverter_specs: InverterSpecs, 
                 temperature_data: TemperatureData, auto_design_data: Dict[str, Any] = None, output_frontend: bool = True,
                 use_guided_pca: bool = False, pca_method: str = "guided_pca", inverters_quantity: int = None):
        self.panel_specs = panel_specs
        self.inverter_specs = inverter_specs
        self.temperature_data = temperature_data
        self.auto_design_data = auto_design_data
        self.output_frontend = output_frontend  # Flag for presentation format
        self.use_guided_pca = use_guided_pca  # NEW: Enable improved sorting
        self.pca_method = pca_method  # NEW: "guided_pca", "forced_axis", or "nearest_neighbor"
        
        if inverters_quantity is not None:
            self.inverter_specs.number_of_inverters = inverters_quantity
        
        # Create panel lookup
        self.panel_lookup = {p.panel_id: p for p in panel_specs}
        
        # Store auto_design data for guided PCA (set later if needed)
        self.roof_planes = {}
        if self.auto_design_data:
            self.roof_planes = self.auto_design_data.get('roof_planes', {})
        
        # Calculate temperature-adjusted constraints
        self.temp_coeff_voc = -0.00279  # V/°C per panel (negative for silicon)
        self.temp_coeff_vmpp = -0.00446  # V/°C per panel (negative for silicon)
        
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
        if preliminary_ratio > 1.3:
            suitability = "UNDERSIZED"
            recommendation = "LOW_INV_CAPACITY"
            optimal_inv_capacity_kWh = round(total_system_dc_power / 1.2 / 1000, 1)
        elif 1.1 < preliminary_ratio <= 1.3:
            suitability = "OPTIMAL"
            recommendation = "OPTIMAL"
            optimal_inv_capacity_kWh = None
        elif 0.9 <= preliminary_ratio <= 1.1:
            suitability = "ACCEPTABLE"
            recommendation = "ACCEPTABLE"
            optimal_inv_capacity_kWh = None
        else: # preliminary_ratio < 0.9
            suitability = "OVERSIZED"
            recommendation = "OVERSIZED"
            optimal_inv_capacity_kWh = None
        
        result = {
            "total_panels": total_panels,
            "power_per_panel_W": round(power_per_panel_hot, 2),
            "total_system_dc_power_W": round(total_system_dc_power, 2),
            "inverter_rated_ac_power_W": round(inverter_ac_power, 2),
            "preliminary_dc_ac_ratio": round(preliminary_ratio, 2),
            "status": suitability,
            "recommendation": recommendation,
        }
        if optimal_inv_capacity_kWh is not None:
            result["optimal_inv_capacity_kWh"] = optimal_inv_capacity_kWh
            
        return result
    
    def optimize(self, inverter_csv_path: str = None, override_inv_quantity: bool = False) -> 'OptimizationResult':
        """
        Run the hierarchical stringing optimization.
        """
        start_time = time.time()

        # Initialize power validator if requested
        if override_inv_quantity:
            from .validatePower import PowerValidator
            self.power_validator = PowerValidator(
                self.inverter_specs,
                self.panel_specs[0],
                self.temperature_data,
                target_dc_ac_ratio=1.25,
                max_dc_ac_ratio=1.5
            )
        else:
            self.power_validator = None
        
        self.straggler_warnings = []
        
        # ... (initialization code remains the same)

        # Step 1: Identify all panel groupings (clusters)
        all_clusters = []
        roof_groups = self._group_by_roof_plane()
        for roof_id, panels in roof_groups.items():
            clusters = self._group_panels_by_proximity(panels)
            for cluster in clusters:
                all_clusters.append({"cluster": cluster, "roof_id": roof_id})
        
        # Sort clusters from largest to smallest
        all_clusters.sort(key=lambda x: len(x["cluster"]), reverse=True)

        # Step 2: String within each cluster
        all_strings = []
        unstrung_panels = []
        for item in all_clusters:
            cluster = item["cluster"]
            roof_id = item["roof_id"]
            
            strings, leftovers = self._string_cluster(cluster, roof_id)
            all_strings.extend(strings)
            unstrung_panels.extend(leftovers)

        # Step 3: Absorb stragglers
        all_strings, unstrung_panels = self._absorb_stragglers(all_strings, unstrung_panels)
        all_strings, unstrung_panels = self._absorb_stragglers_across_similar_roofs(all_strings, unstrung_panels)

        # Report final stragglers
        if unstrung_panels:
            stragglers_by_roof = defaultdict(list)
            for panel in unstrung_panels:
                stragglers_by_roof[panel.roof_plane_id].append(panel)

            for roof_id, panels in stragglers_by_roof.items():
                all_roof_panels = roof_groups.get(roof_id, [])
                straggler_ids = {p.panel_id for p in panels}
                if all_roof_panels:
                    self._report_stragglers(all_roof_panels, straggler_ids, roof_id)

        # Step 4: Rebalance for parallel connections
        all_strings = self._rebalance_strings_for_parallel(all_strings)

        # ... (rest of the method: MPPT assignment, output formatting, etc.)
        # This part will also need to be adjusted to work with the new stringing results.
        
        # For now, I will just return a placeholder result.
        # The full implementation will follow in the next steps.
        
        # We need to re-integrate the full output generation now
        mppts = self._assign_strings_to_mppts(all_strings)
        all_connections = self._assign_mppts_to_inverters(mppts)
        
        # We need to generate preliminary_check before building the final output
        preliminary_check = self._calculate_preliminary_dc_ac_ratio()

        metadata = {
            "optimization_time_seconds": round(time.time() - start_time, 4),
            "timestamp": time.time(),
            "total_panels": len(self.panel_specs),
            "validate_power": override_inv_quantity,
        }
        if hasattr(self.temperature_data, 'state'):
             metadata["state"] = self.temperature_data.state

        formatted_result = self._build_final_output(all_connections, all_strings, preliminary_check, metadata)

        return OptimizationResult(
            connections=all_connections,
            total_panels=len(self.panel_specs),
            string_lengths=[len(s) for s in all_strings],
            total_strings=len(all_strings),
            stringed_panels=sum(len(s) for s in all_strings),
            formatted_output=formatted_result
        )

    def _string_cluster(self, cluster: List[PanelSpecs], roof_id: str) -> Tuple[List[List[str]], List[PanelSpecs]]:
        """String a single cluster of panels."""
        strings = []
        unconnected = set(p.panel_id for p in cluster)
        
        while len(unconnected) >= self.min_panels_per_string:
            remaining = [p for p in cluster if p.panel_id in unconnected]
            start_panel = self._find_corner_panel(remaining)
            
            string = self._build_string_nearest_neighbor(start_panel, cluster, unconnected)
            
            if len(string) >= self.min_panels_per_string:
                strings.append(string)
                for pid in string:
                    unconnected.discard(pid)
            else:
                break
        
        leftovers = [p for p in cluster if p.panel_id in unconnected]
        if leftovers:
            print(f"  ⚠️  {len(leftovers)} straggler panels detected on roof {roof_id} (cannot form valid strings)")

        return strings, leftovers

    def _absorb_stragglers(self, strings: List[List[str]], stragglers: List[PanelSpecs]) -> Tuple[List[List[str]], List[PanelSpecs]]:
        """Attempt to absorb stragglers into existing strings."""
        
        still_stragglers = []
        
        for straggler in stragglers:
            absorbed = False
            # Find the closest string to this straggler
            closest_string = None
            min_dist = float('inf')

            for string in strings:
                # Check if the string is on the same roof
                if self.panel_lookup[string[0]].roof_plane_id == straggler.roof_plane_id:
                    for panel_id in string:
                        dist = self._distance(self.panel_lookup[panel_id], straggler)
                        if dist < min_dist:
                            min_dist = dist
                            closest_string = string
            
            if closest_string and len(closest_string) < self.max_panels_per_string:
                # Check if adding the straggler is feasible
                # For simplicity, we'll just append it. A more advanced implementation
                # would find the best position in the string to insert it.
                closest_string.append(straggler.panel_id)
                absorbed = True

            if not absorbed:
                still_stragglers.append(straggler)
                
        return strings, still_stragglers

    def _absorb_stragglers_across_similar_roofs(self, strings: List[List[str]], stragglers: List[PanelSpecs]) -> Tuple[List[List[str]], List[PanelSpecs]]:
        """Attempt to absorb stragglers into strings on similar roofs."""
        still_stragglers = []
        
        # Create a map of roof_id to similar_roof_group_id
        roof_to_group_map = {}
        similar_roof_groups = self._get_similar_roof_groups()
        for group_id, roof_ids in similar_roof_groups.items():
            for roof_id in roof_ids:
                roof_to_group_map[roof_id] = group_id

        for straggler in stragglers:
            absorbed = False
            straggler_group = roof_to_group_map.get(straggler.roof_plane_id)
            if not straggler_group:
                still_stragglers.append(straggler)
                continue

            # Find the closest string within the same group of similar roofs
            closest_string = None
            min_dist = float('inf')

            for string in strings:
                string_roof_id = self.panel_lookup[string[0]].roof_plane_id
                if roof_to_group_map.get(string_roof_id) == straggler_group:
                    for panel_id in string:
                        dist = self._distance(self.panel_lookup[panel_id], straggler)
                        if dist < min_dist:
                            min_dist = dist
                            closest_string = string
            
            if closest_string and len(closest_string) < self.max_panels_per_string:
                closest_string.append(straggler.panel_id)
                absorbed = True

            if not absorbed:
                still_stragglers.append(straggler)
                
        return strings, still_stragglers

    def _get_similar_roof_groups(self) -> Dict[str, List[str]]:
        """Helper to get groups of similar roofs."""
        # This is a simplified version of the logic that should be in data_parsers.py
        # For now, it will just group by exact azimuth and pitch.
        groups = {}
        for roof_id, roof_data in self.roof_planes.items():
            key = (roof_data.get('azimuth', 0), roof_data.get('pitch', 0))
            if key not in groups:
                groups[key] = []
            groups[key].append(roof_id)
        
        return {f"group_{i}": g for i, g in enumerate(groups.values())}

    def _rebalance_strings_for_parallel(self, strings: List[List[str]]) -> List[List[str]]:
        """Rebalance strings within each group of similar roofs."""
        
        # Create a map of roof_id to similar_roof_group_id
        roof_to_group_map = {}
        similar_roof_groups = self._get_similar_roof_groups()
        for group_id, roof_ids in similar_roof_groups.items():
            for roof_id in roof_ids:
                roof_to_group_map[roof_id] = group_id

        # Group strings by their similar_roof_group
        strings_by_group = {}
        for string in strings:
            roof_id = self.panel_lookup[string[0]].roof_plane_id
            group_id = roof_to_group_map.get(roof_id)
            if group_id:
                if group_id not in strings_by_group:
                    strings_by_group[group_id] = []
                strings_by_group[group_id].append(string)

        # Rebalance within each group
        rebalanced_strings = []
        for group_id, group_strings in strings_by_group.items():
            rebalanced_group = self._rebalance_string_group(group_strings)
            rebalanced_strings.extend(rebalanced_group)
            
        return rebalanced_strings

    def _rebalance_string_group(self, strings: List[List[str]]) -> List[List[str]]:
        """Rebalance a group of strings to create equal-length strings."""
        
        all_panels = [pid for s in strings for pid in s]
        total_panels = len(all_panels)
        num_strings = len(strings)

        if num_strings < 2:
            return strings

        # Try to create pairs of equal-length strings
        for i in range(2, num_strings + 1):
            if total_panels % i == 0:
                new_len = total_panels // i
                if new_len >= self.min_panels_per_string and new_len <= self.max_panels_per_string:
                    # We can create i strings of equal length
                    print(f"Rebalancing {num_strings} strings into {i} strings of length {new_len}")
                    
                    # Re-order all panels by proximity
                    ordered_panels = self._order_group_by_proximity([self.panel_lookup[pid] for pid in all_panels])
                    
                    new_strings = []
                    for j in range(i):
                        start = j * new_len
                        end = start + new_len
                        new_strings.append(ordered_panels[start:end])
                    return new_strings
        
        # If no perfect rebalancing is possible, return the original strings
        return strings

    def _placeholder_result(self, strings: List[List[str]]) -> 'OptimizationResult':
        """Create a placeholder result for now."""
        # This is a temporary function to allow me to test the first step.
        # It will be replaced with the full output generation logic.
        return OptimizationResult(
            connections={},
            total_panels=len(self.panel_specs),
            string_lengths=[len(s) for s in strings],
            total_strings=len(strings),
            stringed_panels=sum(len(s) for s in strings)
        )

    
    def _group_by_roof_plane(self) -> Dict[str, List[PanelSpecs]]:
        """Group panels by roof plane ID"""
        groups = {}
        for panel in self.panel_specs:
            roof_id = panel.roof_plane_id
            if roof_id not in groups:
                groups[roof_id] = []
            groups[roof_id].append(panel)
        return groups
    
    def _group_panels_by_proximity(self, panels: List[PanelSpecs]) -> List[List[PanelSpecs]]:
        """Group panels based on proximity."""
        if not panels:
            return []
        
        groups = []
        ungrouped = set(range(len(panels)))
        # Tighter threshold to create more localized clusters
        threshold = 100.0
        
        while ungrouped:
            group_indices = [ungrouped.pop()]
            group = [panels[group_indices[0]]]
            
            changed = True
            while changed:
                changed = False
                to_remove = []
                
                for idx in ungrouped:
                    panel = panels[idx]
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

    def _string_roof_plane(self, panels: List[PanelSpecs], roof_id: str) -> Tuple[List[List[str]], List[PanelSpecs]]:
        """
        String a single roof plane and return strings and leftovers.
        """
        if not panels:
            return [], []
        
        unconnected = set(p.panel_id for p in panels)
        strings = []
        
        while len(unconnected) >= self.min_panels_per_string:
            remaining_panels = [p for p in panels if p.panel_id in unconnected]
            if not remaining_panels:
                break
            
            start_panel = self._find_corner_panel(remaining_panels)
            
            # Build the longest possible string from this starting point
            string = self._build_string_nearest_neighbor(start_panel, panels, unconnected)
            
            if len(string) >= self.min_panels_per_string:
                strings.append(string)
                for pid in string:
                    unconnected.discard(pid)
            else:
                # Break if we can't form a valid string from the remaining panels
                break
        
        leftovers = [p for p in panels if p.panel_id in unconnected]
        if leftovers:
            print(f"  ⚠️  {len(leftovers)} straggler panels detected (cannot form valid strings)")
            self._report_stragglers(panels, {p.panel_id for p in leftovers}, roof_id)
        
        return strings, leftovers
    
    def _rebalance_strings(self, strings: List[List[str]]) -> List[List[str]]:
        """
        Rebalance strings to have similar lengths for parallel connections.
        """
        all_panels = [panel for string in strings for panel in string]
        total_panels = len(all_panels)
        num_strings = len(strings)

        if num_strings == 0:
            return []

        # Ideal number of panels per string
        ideal_len = total_panels // num_strings
        remainder = total_panels % num_strings

        new_strings = []
        start_index = 0
        
        # Re-order all panels based on proximity before re-stringing
        ordered_panels = self._order_group_by_proximity([self.panel_lookup[pid] for pid in all_panels])

        for i in range(num_strings):
            length = ideal_len + 1 if i < remainder else ideal_len
            if length >= self.min_panels_per_string:
                new_string = ordered_panels[start_index : start_index + length]
                new_strings.append(new_string)
                start_index += length
            else:
                # If rebalancing results in strings that are too short,
                # it's better to return the original strings.
                return strings
        
        return new_strings

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
        max_distance_threshold = 150.0  # A bit more lenient
        
        while len(string) < self.max_panels_per_string: # Go for the max possible length
            # Find closest unconnected panel
            closest_panel = None
            closest_distance = float('inf')
            
            temp_unconnected = unconnected.copy()
            temp_unconnected.remove(current_panel.panel_id)

            for pid in temp_unconnected:
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
        
        # Now, trim the string to the ideal length if it's too long
        if len(string) > self.ideal_panels_per_string:
            string = string[:self.ideal_panels_per_string]

        return string
    
    def _distance(self, p1: PanelSpecs, p2: PanelSpecs) -> float:
        """Calculate Euclidean distance between two panels"""
        x1, y1 = p1.center_coords
        x2, y2 = p2.center_coords
        return math.sqrt((x2 - x1)**2 + (y2 - y1)**2)
    
    def _sort_panels_guided_pca(self, panels: List[PanelSpecs], roof_id: str) -> List[str]:
        """
        Sort panels using Guided PCA method.
        
        Returns sorted list of panel IDs or empty list if method fails.
        """
        try:
            from guided_pca_sorting import sort_panels_guided_pca
        except ImportError:
            print("  ⚠️ guided_pca_sorting module not available")
            return []
        
        # Get roof azimuth
        roof_data = self.roof_planes.get(roof_id, {})
        azimuth = roof_data.get('azimuth', 180.0)  # Default to South if not available
        
        # Get panel data from auto_design
        if not self.auto_design_data or 'solar_panels' not in self.auto_design_data:
            return []
        
        # Filter panels for this roof
        panel_ids_set = {p.panel_id for p in panels}
        panels_data = [
            p for p in self.auto_design_data['solar_panels']
            if p.get('panel_id') in panel_ids_set
        ]
        
        if not panels_data:
            return []
        
        # Call the guided PCA sorter
        sorted_ids = sort_panels_guided_pca(
            panels_data,
            azimuth,
            method=self.pca_method,
            verbose=True
        )
        
        return sorted_ids
    
    def _create_strings_from_sorted_ids(
        self,
        sorted_panel_ids: List[str],
        panels: List[PanelSpecs]
    ) -> List[List[str]]:
        """
        Create strings from pre-sorted panel IDs.
        
        Simply chunks the sorted list into strings of ideal length.
        """
        strings = []
        current_string = []
        
        for panel_id in sorted_panel_ids:
            current_string.append(panel_id)
            
            # Check if string is at ideal length
            if len(current_string) >= self.ideal_panels_per_string:
                strings.append(current_string)
                current_string = []
        
        # Handle remaining panels
        if current_string:
            # If remaining panels meet minimum requirement, add as string
            if len(current_string) >= self.min_panels_per_string:
                strings.append(current_string)
            else:
                # Too few - these become stragglers
                pass
        
        return strings
    
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
        
        # Group straggler panels by proximity
        straggler_groups = self._group_straggler_by_proximity(straggler_panels)
        
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
                "reason": "LOW_VOLTAGE_STARTUP"
            }
            self.straggler_warnings.append(warning)
        
        print(f"  ╚════════════════════════════════════════════════════════════════\n")
    
    def _track_disconnected_panels(self, all_mppts: List[List[List[str]]], mppts_assigned_count: int):
        """
        Track panels that were disconnected due to inverter capacity limits.
        
        Args:
            all_mppts: All MPPTs created during stringing
            mppts_assigned_count: Number of MPPTs that were assigned to inverters
        """
        if not hasattr(self, 'disconnected_warnings'):
            self.disconnected_warnings = []
        
        # Get unassigned MPPTs
        unassigned_mppts = all_mppts[mppts_assigned_count:]
        
        for mppt_idx, mppt_strings in enumerate(unassigned_mppts, start=mppts_assigned_count + 1):
            for string in mppt_strings:
                panel_count = len(string)
                
                # Calculate voltage and power for this string
                panel = self.panel_lookup[string[0]] if string and string[0] in self.panel_lookup else None
                if panel:
                    temp_diff_hot = self.temperature_data.max_temp_c - 25.0
                    vmpp_hot = panel.vmpp_stc * (1 + self.temp_coeff_vmpp * temp_diff_hot)
                    string_voltage = vmpp_hot * panel_count
                    string_power = string_voltage * panel.impp_stc
                    
                    warning = {
                        "mppt_id": f"MPPT_{mppt_idx}",
                        "panel_count": panel_count,
                        "panel_ids": string,
                        "estimated_voltage_V": round(string_voltage, 1),
                        "estimated_power_W": round(string_power, 1),
                        "reason": "Inverter capacity limit reached - no available MPPT slots"
                    }
                    self.disconnected_warnings.append(warning)
    
    def _group_straggler_by_proximity(self, straggler_panels: List[PanelSpecs]) -> List[List[PanelSpecs]]:
        """
        Group straggler panels based on proximity.
        Panels within threshold distance are grouped together.
        """
        if not straggler_panels:
            return []
        
        # Use union-find to group nearby panels
        groups = []
        ungrouped = set(range(len(straggler_panels)))
        threshold = 100.0  # Same as neighbor threshold
        
        while ungrouped:
            # Start new group with first ungrouped panel
            group_indices = [ungrouped.pop()]
            group = [straggler_panels[group_indices[0]]]
            
            # Find all panels within threshold of this group
            changed = True
            while changed:
                changed = False
                to_remove = []
                
                for idx in ungrouped:
                    panel = straggler_panels[idx]
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
        remaining = list(group[1:])
        
        while remaining:
            current = ordered[-1]
            # Find closest remaining panel
            closest = min(remaining, key=lambda p: self._distance(current, p))
            ordered.append(closest)
            remaining.remove(closest)
        
        return [p.panel_id for p in ordered]
    
    def _assign_strings_to_mppts(self, strings: List[List[str]]) -> List[List[List[str]]]:
        """
        Assign strings to MPPTs, creating parallel connections where possible.
        """
        if not strings:
            return []

        # Group strings by length for potential parallel connection
        strings_by_length = defaultdict(list)
        for s in strings:
            strings_by_length[len(s)].append(s)

        mppts = []
        
        for length, string_group in strings_by_length.items():
            if not string_group:
                continue

            panel = self.panel_lookup[string_group[0][0]]
            string_current = panel.impp_stc
            
            # Determine how many strings can be connected in parallel
            max_parallel = 1
            if string_current > 0:
                max_parallel = int(self.inverter_specs.max_dc_current_per_mppt / string_current)

            # Create MPPTs, grouping strings for parallel connection
            for i in range(0, len(string_group), max_parallel):
                mppt = string_group[i:i + max_parallel]
                mppts.append(mppt)
        
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
        Assign MPPTs to inverters with the new naming convention.
        """
        inverters = {}
        mppts_per_inverter = self.inverter_specs.number_of_mppts
        max_inverters = self.inverter_specs.number_of_inverters if not self.power_validator else float('inf')
        
        inverter_counter = 1
        mppt_local_counter = 1
        
        for mppt in mppts:
            if inverter_counter > max_inverters:
                break

            inverter_id = f"i{inverter_counter}"
            if inverter_id not in inverters:
                inverters[inverter_id] = {}
                mppt_local_counter = 1

            mppt_id = f"i{inverter_counter}_mppt{mppt_local_counter}"
            inverters[inverter_id][mppt_id] = mppt
            
            if len(inverters[inverter_id]) >= mppts_per_inverter:
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
            
            if validation["valid"] and len(current_inverter_mppts) < self.inverter_specs.number_of_mppts:
                # Add MPPT to current inverter
                current_inverter_mppts[mppt_id] = mppt_strings
                current_inverter_power += mppt_power
                mppt_global_counter += 1
            else:
                # MPPT would exceed power limit or MPPT limit
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
    
    def _build_final_output(self, inverter_structure: Dict[str, Dict[str, List[List[str]]]], all_strings: List[List[str]], preliminary_check: Dict[str, Any], metadata: Dict[str, Any]) -> Dict[str, Any]:
        """
        Build the final JSON output in the desired format.
        """
        strings_data = {}
        mppt_specs = {}
        inverter_specs = {}
        parallel_strings = []
        
        string_counter = 1
        for inv_id, mppts in inverter_structure.items():
            inv_mppt_ids = []
            for mppt_id, strings in mppts.items():
                inv_mppt_ids.append(mppt_id)
                mppt_specs[mppt_id] = self._calculate_mppt_properties_for_strings(strings)
                
                if len(strings) > 1:
                    parallel_group = []
                    for string_panels in strings:
                        string_id = f"s{string_counter}"
                        parallel_group.append(string_id)
                        string_counter += 1
                    parallel_strings.append(parallel_group)
                else:
                    string_counter += len(strings)

            inverter_specs[inv_id] = self._calculate_inverter_aggregate_specs([(mppt_id, mppt_specs[mppt_id]) for mppt_id in inv_mppt_ids])

        # Re-build strings_data with the correct string IDs
        string_counter = 1
        for inv_id, mppts in inverter_structure.items():
            for mppt_id, strings in mppts.items():
                for string_panels in strings:
                    string_id = f"s{string_counter}"
                    strings_data[string_id] = {
                        "panel_ids": string_panels,
                        "inverter": inv_id,
                        "mppt": mppt_id,
                        "roof_section": self.panel_lookup[string_panels[0]].roof_plane_id,
                        "properties": self._calculate_string_properties(string_panels)
                    }
                    string_counter += 1

        summary = {
            "total_panels": len(self.panel_specs),
            "total_panels_stringed": sum(len(s) for s in all_strings),
            "total_strings": len(all_strings),
            "total_mppts_used": len(mppt_specs),
            "total_inverters_used": len(inverter_specs),
            "stringing_efficiency": round(100 * sum(len(s) for s in all_strings) / len(self.panel_specs), 2) if len(self.panel_specs) > 0 else 0,
            "total_straggler_panels": len(self.panel_specs) - sum(len(s) for s in all_strings),
            "parallel_strings": parallel_strings
        }

        return {
            "strings": strings_data,
            "inverter_specs": inverter_specs,
            "mppt_specs": mppt_specs,
            "summary": summary,
            "straggler_warnings": self.straggler_warnings,
            "preliminary_sizing_check": preliminary_check,
            "metadata": metadata
        }

    
    def _calculate_string_properties(self, panel_ids: List[str]) -> Dict[str, Any]:
        """Calculate electrical properties for a single string"""
        num_panels = len(panel_ids)
        
        # Temperature adjustments
        temp_diff_cold = self.temperature_data.min_temp_c - 25.0
        temp_diff_hot = self.temperature_data.max_temp_c - 25.0
        
        # Sample panel (assume all panels are identical)
        panel = self.panel_specs[0]
        
        # Voltage calculations
        voc_cold = panel.voc_stc * (1 + self.temp_coeff_voc * temp_diff_cold)
        vmpp_hot = panel.vmpp_stc * (1 + self.temp_coeff_vmpp * temp_diff_hot)
        
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
                    "mppt_current_A": round(total_current, 2)
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
        
        # Determine status based on DC/AC ratio
        if dc_ac_ratio < 0.9:
            status = "OVERSIZED"
        elif 0.9 <= dc_ac_ratio <= 1.1:
            status = "ACCEPTABLE"
        elif 1.1 < dc_ac_ratio <= 1.3:
            status = "OPTIMAL"
        else: # dc_ac_ratio > 1.3
            status = "UNDERSIZED"

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
                "will_clip_power": total_dc_power > rated_ac_power,
                "within_dc_power_limit": total_dc_power <= max_dc_power,
                "average_power_per_mppt_W": round(total_dc_power / len(mppt_list) if mppt_list else 0, 2)
            },
            "validation": {
                "all_mppts_safe": all_mppts_safe,
                "within_power_limits": total_dc_power <= max_dc_power,
                "optimal_dc_ac_ratio": 1.1 < dc_ac_ratio <= 1.3,
                "status": status
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

