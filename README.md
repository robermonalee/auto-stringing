# Solar Panel Stringing Optimizer

A comprehensive Python-based system for optimizing solar panel stringing configurations based on temperature-adjusted voltages and inverter constraints.

## 1. What This Does

This optimizer takes a solar panel layout and equipment specifications as input and generates an optimized stringing configuration. It aims to maximize the system's performance and efficiency by grouping panels into strings that respect the electrical constraints of the inverters and MPPTs, while considering temperature effects on voltage.

## 2. Project Structure

```
auto-stringing/
├── stringer/
│   ├── simple_stringing.py         # Core optimization algorithm
│   ├── data_parsers.py             # Data loading and parsing utilities
│   ├── specs.py                    # Data classes for panel and inverter specs
│   └── amb_temperature_data.csv    # Temperature data by state
├── tests/
│   └── local_stringing_test.py     # Local test script
├── output_examples/                # Example output files
├── helper_functions/
│   └── visualization_helper.py     # Visualization helper
├── README.md                       # This file
└── process_logic.md                # Detailed explanation of the stringing logic
```

## 3. Process Logic

The stringing process follows a hierarchical approach to create logical and efficient string paths:

1.  **Pre-Computation and Constraint Calculation:**
    *   Calculates the minimum and maximum panel voltages based on historical temperature data for the site's location.
    *   Determines the valid range of string lengths (minimum, maximum, and ideal) based on the inverter's voltage and current limits.

2.  **Hierarchical String Generation:**
    *   **Roof Grouping:** Panels are first grouped by roof plane. Roofs with similar azimuth and pitch angles (within a configurable tolerance) are considered as a single group to allow for more flexible stringing.
    *   **Proximity Clustering:** Within each roof group, panels are further grouped into localized clusters based on their proximity to each other.
    *   **String Creation:** The algorithm iterates through each cluster, starting from a corner panel and following a nearest-neighbor approach to create strings of the ideal length.

3.  **Straggler Absorption and Rebalancing:**
    *   **Straggler Absorption:** Any leftover panels (stragglers) that could not form a valid string are then checked to see if they can be absorbed into existing strings without violating any constraints. This is first attempted within the same roof and then across similar roofs.
    *   **Parallel Rebalancing:** To optimize for parallel connections, the algorithm attempts to rebalance the lengths of strings on similar roofs, aiming to create as many same-length strings as possible.

4.  **MPPT and Inverter Assignment:**
    *   **MPPT Assignment:** The generated strings are assigned to the available MPPTs on the inverters. Strings with the same length are prioritized for parallel connection to the same MPPT.
    *   **Inverter Assignment:** MPPTs are then assigned to inverters. If the `override_inv_quantity` flag is set, the system can dynamically add more inverters if the number of MPPTs exceeds the capacity of the initially specified inverters.

## 4. Inputs

### Required Inputs

*   **Auto Design Data (JSON):** A JSON file containing the solar panel layout, including panel coordinates and roof plane information. The script can fetch this from an API or load it from a local file.
    *   `latitude`, `longitude`: The geographical coordinates of the site.
    *   `state`: The two-letter state code for temperature data.

*   **Panel Specifications (Dictionary):** A Python dictionary containing the electrical specifications of the solar panels.
    *   `voc`: Open-circuit voltage (V)
    *   `vmp`: Maximum power point voltage (V)
    *   `isc`: Short-circuit current (A)
    *   `imp`: Maximum power point current (A)

*   **Inverter Specifications (Dictionary):** A Python dictionary containing the electrical specifications of the inverters.
    *   `maxDCInputVoltage`: Maximum DC input voltage (V)
    *   `numberOfMPPTs`: Number of MPPTs per inverter
    *   `startUpVoltage`: The minimum voltage required to start the inverter (V)
    *   `maxDCInputCurrentPerMPPT`: Maximum DC input current per MPPT (A)
    *   `maxDCInputCurrentPerString`: Maximum DC input current per string (A)
    *   `mpptOperatingVoltageMinRange`: Minimum MPPT operating voltage (V)
    *   `mpptOperatingVoltageMaxRange`: Maximum MPPT operating voltage (V)
    *   `maxShortCircuitCurrentPerMPPT`: Maximum short-circuit current per MPPT (A)
    *   `ratedACPowerW`: Rated AC power output (W)

*   **Temperature Data (CSV):** A CSV file (`amb_temperature_data.csv`) containing historical temperature data by state.

### Optional Inputs

*   **`INVERTERS_QUANTITY` (integer):** The number of inverters to be used in the system. This is used as a hard limit unless `OVERRIDE_INV_QUANTITY` is true.
*   **`OVERRIDE_INV_QUANTITY` (boolean):** If set to `true`, the optimizer can dynamically add more inverters than specified in `INVERTERS_QUANTITY` to accommodate all the generated strings.

## 5. Output Structure

The optimizer generates a JSON output with the following structure:

*   **`strings`**: Detailed information for each string, including panel IDs, inverter and MPPT assignments, and electrical properties.
*   **`inverter_specs`**: Aggregated specifications for each inverter, including DC/AC ratio and validation status.
*   **`mppt_specs`**: Detailed specifications for each MPPT, including voltage, current, and power.
*   **`summary`**: A high-level summary of the stringing results, including total panels, strings, and efficiency.
*   **`straggler_warnings`**: A list of warnings for panels that could not be strung.
*   **`preliminary_sizing_check`**: An initial check of the inverter sizing.
*   **`metadata`**: Information about the stringing process.

### Output Package Codes

*   **`straggler_warnings.reason`**:
    *   `LOW_VOLTAGE_STARTUP`: The panels could not form a string that meets the minimum voltage requirements of the inverter.
*   **`preliminary_sizing_check.recommendation`**:
    *   `LOW_INV_CAPACITY`: The inverter is likely undersized for the total DC power of the system.

## 6. Example Output

```json
{
  "strings": {
    "s1": {
      "panel_ids": ["p1", "p2", "p3", "p4", "p5", "p6", "p7", "p8", "p9"],
      "inverter": "i1",
      "mppt": "i1_mppt1",
      "roof_section": "1",
      "properties": {
        "voltage_V": 222.55,
        "current_A": 10.52,
        "power_W": 2341.27,
        "max_voltage_V": 372.34
      }
    }
  },
  "inverter_specs": {
    "i1": {
      "num_mppts": 1,
      "mppt_ids": ["i1_mppt1"],
      "power": {
        "total_dc_power_W": 2341.27,
        "rated_ac_power_W": 8000.0,
        "dc_ac_ratio": 0.29,
        "status": "OVERSIZED"
      }
    }
  },
  "mppt_specs": {
    "i1_mppt1": {
      "num_strings": 1,
      "total_panels": 9,
      "voltage": {
        "operating_voltage_V": 222.55,
        "within_limits": true
      },
      "current": {
        "operating_current_A": 10.52,
        "within_limits": true
      },
      "power": {
        "total_power_W": 2341.27
      }
    }
  },
  "summary": {
    "total_panels": 99,
    "total_panels_stringed": 98,
    "total_strings": 13,
    "stringing_efficiency": 98.99,
    "parallel_strings": [["s1", "s2"]]
  },
  "straggler_warnings": [
    {
      "roof_id": "5",
      "panel_ids": ["p100"],
      "reason": "LOW_VOLTAGE_STARTUP"
    }
  ],
  "preliminary_sizing_check": {
    "status": "UNDERSIZED",
    "recommendation": "LOW_INV_CAPACITY",
    "optimal_inv_capacity_kWh": 21.5
  },
  "metadata": {
    "optimization_time_seconds": 0.0123,
    "timestamp": 1761358911.172756,
    "validate_power": true
  }
}
```

## 7. Helper Functions

The project includes a `visualization_helper.py` module that can be used to generate visual representations of the stringing configurations on the panel layout. This is useful for debugging and verifying the results of the optimization.

## 8. Temperature Functions

The system uses temperature coefficients to adjust the panel's voltage based on the ambient temperature. The following coefficients are used:

*   **`temp_coeff_voc`**: -0.00279 V/°C per panel
*   **`temp_coeff_vmpp`**: -0.00446 V/°C per panel

These coefficients are used to calculate the panel's voltage at the record low and high temperatures for the site's location, ensuring that the strings will not exceed the inverter's maximum voltage in the cold or drop below the minimum operating voltage in the heat.

## 9. Recent Changes

*   **Hierarchical Stringing Logic:** The stringing process has been re-architected to follow a hierarchical approach, resulting in more organized and efficient string paths.
*   **Enforced Parallel Connections:** The algorithm now actively tries to create parallel connections by rebalancing strings on roofs with similar orientations.
*   **Dynamic Inverter Quantity:** The system can now dynamically add inverters as needed when the `override_inv_quantity` flag is set.
*   **Streamlined Output Package:** The JSON output has been refined for clarity and programmatic use, with standardized reason codes and more precise metadata.
