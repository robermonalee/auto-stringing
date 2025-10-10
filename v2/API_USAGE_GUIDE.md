# Solar Stringing Optimizer - API Usage Guide

## Overview
The Solar Stringing Optimizer creates optimal string configurations for solar panel installations, considering electrical constraints, temperature effects, and inverter capacity.

---

## Core Files (Production Ready)

### Python Modules
- **`simple_stringing.py`** - Main optimizer with stringing logic
- **`data_parsers.py`** - Input/output data parsing
- **`validatePower.py`** - Power validation (optional, only used when `validate_power=True`)

### Data Files
- **`panel_specs.csv`** - Panel electrical specifications
- **`inverter_specs.csv`** - Inverter specifications
- **`amb_temperature_data.csv`** - Temperature data by state

### Example Input Files
- `oct9design.json` - Standard auto-design format
- `exampleCA.json` - California example
- `second-test.json` - Additional test case

---

## API Usage

### Basic Import
```python
from simple_stringing import SimpleStringingOptimizer
import data_parsers
```

### Complete Example
```python
# 1. Load panel data
panels = data_parsers.create_panel_specs_objects(
    data_parsers.parse_auto_design_json('oct9design.json'),
    data_parsers.parse_panel_specs_csv('panel_specs.csv')
)

# 2. Load inverter specs
inverter = data_parsers.create_inverter_specs_object(
    data_parsers.parse_inverter_specs_csv('inverter_specs.csv')
)

# 3. Load temperature data
temp = data_parsers.parse_temperature_data_csv(
    'amb_temperature_data.csv', 
    'California'  # State name
)

# 4. Create optimizer
optimizer = SimpleStringingOptimizer(
    panel_specs=panels,
    inverter_specs=inverter,
    temperature_data=temp,
    output_frontend=True  # OPTIONAL: Default False (technical format)
)

# 5. Run optimization
result = optimizer.optimize(
    validate_power=True  # OPTIONAL: Default False
)

# 6. Access results
output = result.formatted_output
```

---

## Parameters

### `SimpleStringingOptimizer.__init__()`

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `panel_specs` | List[PanelSpecs] | ✅ Yes | - | Panel specifications and locations |
| `inverter_specs` | InverterSpecs | ✅ Yes | - | Inverter electrical specs |
| `temperature_data` | TemperatureData | ✅ Yes | - | Min/max temperatures for voltage calc |
| `output_frontend` | bool | ⚪ Optional | `False` | Output format (see below) |

### `optimizer.optimize()`

| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| `validate_power` | bool | ⚪ Optional | `False` | Enable power validation & string length adjustment |

---

## Output Formats

### Technical Format (`output_frontend=False`)
Hierarchical structure: **Inverter → Roof → MPPT → Strings**

```json
{
  "connections": {
    "Inverter_1": {
      "3": {  // Roof plane ID
        "MPPT_1": {
          "s1": ["panel_id_1", "panel_id_2", ...],
          "properties": {
            "voltage": {...},
            "current": {...},
            "power": {...}
          }
        }
      }
    }
  },
  "strings": {
    "s1": {
      "panel_ids": [...],
      "panel_count": 9,
      "properties": {...}
    }
  },
  "summary": {
    "total_panels": 63,
    "total_panels_stringed": 58,
    "total_strings": 15,
    "total_inverters_used": 15
  },
  "suggestions": [
    "Recommended inverter capacity: ~4kW AC per inverter..."
  ]
}
```

### Frontend Format (`output_frontend=True`)
Flat structure with references for easier API consumption:

```json
{
  "strings": {
    "s1": {
      "panel_ids": ["panel_1", "panel_2", ...],
      "inverter": "Inverter_1",
      "mppt": "MPPT_1",
      "roof_section": "3",
      "properties": {
        "voltage_V": 450.0,
        "current_A": 10.5,
        "power_W": 4725.0
      }
    }
  },
  "inverter_specs": {
    "Inverter_1": {
      "voltage": {
        "operating_V": 450.0,
        "max_V": 600.0,
        "startup_V": 100.0,
        "within_range": true
      },
      "current": {
        "per_mppt_limit_A": 12.5,
        "all_mppts_within_limits": true
      },
      "power": {
        "total_dc_power_W": 4725.0,
        "rated_ac_power_W": 2000.0,
        "dc_ac_ratio": 2.36
      },
      "validation": {
        "status": "ACCEPTABLE",
        "is_safe": true
      }
    }
  },
  "mppt_specs": {
    "MPPT_1": {
      "voltage": {...},
      "current": {...},
      "power": {...}
    }
  },
  "summary": {
    "total_panels": 63,
    "total_panels_stringed": 58,
    "total_strings": 15,
    "total_inverters_used": 15
  },
  "straggler_warnings": [
    {
      "roof_plane_id": "3",
      "panel_count": 1,
      "panel_ids": ["panel_x"],
      "reason": "insufficient_voltage"
    }
  ],
  "suggestions": [
    "Straggler panels detected (5 panels) and inverter was undersized...",
    "Recommended inverter capacity: ~4kW AC per inverter..."
  ]
}
```

---

## Power Validation (`validate_power=True`)

When enabled, the optimizer:
1. **Calculates optimal string length** based on inverter capacity
2. **Adjusts string length** to fit within inverter power limits
3. **Creates more inverters** as needed for optimal DC/AC ratios (1.1-1.5)
4. **Generates intelligent suggestions** about inverter sizing

### Example: Impact of Power Validation

```python
# Without validation (validate_power=False)
# - String length: 9 panels (voltage-based ideal)
# - Result: 9 strings, 5 inverters
# - DC/AC ratios: 1.70 - 6.11 (OVERSIZED)

# With validation (validate_power=True)
# - String length: 4 panels (adjusted for 2kW inverter)
# - Result: 15 strings, 15 inverters  
# - DC/AC ratios: 1.02 - 1.36 (OPTIMAL)
```

---

## Output Properties Explained

### Voltage Properties
- `operating_V`: Voltage at maximum power point (hot temp)
- `max_V`: Open circuit voltage (cold temp)
- `startup_V`: Minimum voltage needed to start inverter
- `within_range`: Whether voltage is within inverter MPPT range

### Current Properties
- `operating_A`: Current at maximum power point (Impp)
- `short_circuit_A`: Short circuit current with safety factor (Isc × 1.25)
- `will_clip`: True if operating current exceeds inverter's max usable current
- `is_safe`: True if short circuit current is within inverter's safety limit

### Power Properties
- `total_dc_power_W`: Total DC power from all panels
- `rated_ac_power_W`: Inverter's rated AC output capacity
- `dc_ac_ratio`: Ratio of DC input to AC output (optimal: 1.1-1.3)

### Validation Status
- `OPTIMAL`: DC/AC ratio between 1.1-1.3
- `ACCEPTABLE`: DC/AC ratio between 1.0-1.5
- `UNDERSIZED`: DC/AC ratio < 1.0
- `OVERSIZED`: DC/AC ratio > 1.5

---

## Suggestions System

The optimizer automatically generates actionable suggestions based on results:

### Suggestion Types

1. **Stragglers + Undersized Inverter**
   ```
   "Straggler panels detected (5 panels) and inverter was undersized 
   for ideal string length. Consider using an inverter with higher capacity..."
   
   "Recommended inverter capacity: ~4kW AC per inverter 
   (to accommodate 9-panel strings at optimal 1.25 DC/AC ratio)."
   ```

2. **Stragglers Only**
   ```
   "Straggler panels detected (5 panels). Consider reorganizing panels 
   more compactly. Panels must be grouped in multiples of 3 or more..."
   ```

3. **String Cropping Only**
   ```
   "Strings were shortened to fit inverter capacity. Consider using 
   a larger inverter to allow longer strings..."
   ```

---

## Error Handling

### Straggler Warnings
Panels that cannot be connected due to insufficient voltage are reported:

```python
if output.get("straggler_warnings"):
    for warning in output["straggler_warnings"]:
        print(f"Roof {warning['roof_plane_id']}: {warning['panel_count']} stragglers")
        print(f"Reason: {warning['reason']}")
```

### Validation Flags
Check inverter status before deployment:

```python
for inv_id, inv_specs in output["inverter_specs"].items():
    status = inv_specs["validation"]["status"]
    if status not in ["OPTIMAL", "ACCEPTABLE"]:
        print(f"⚠️  {inv_id}: {status}")
```

---

## Complete Working Example

```python
from simple_stringing import SimpleStringingOptimizer
import data_parsers
import json

# Load data
panels = data_parsers.create_panel_specs_objects(
    data_parsers.parse_auto_design_json('oct9design.json'),
    data_parsers.parse_panel_specs_csv('panel_specs.csv')
)
inverter = data_parsers.create_inverter_specs_object(
    data_parsers.parse_inverter_specs_csv('inverter_specs.csv')
)
temp = data_parsers.parse_temperature_data_csv('amb_temperature_data.csv', 'California')

# Create optimizer with frontend output format
optimizer = SimpleStringingOptimizer(panels, inverter, temp, output_frontend=True)

# Run with power validation
result = optimizer.optimize(validate_power=True)

# Access output
output = result.formatted_output

# Print summary
print(f"Panels stringed: {output['summary']['total_panels_stringed']}/{output['summary']['total_panels']}")
print(f"Strings: {output['summary']['total_strings']}")
print(f"Inverters: {output['summary']['total_inverters_used']}")

# Check suggestions
if output.get('suggestions'):
    print("\nSuggestions:")
    for suggestion in output['suggestions']:
        print(f"  • {suggestion}")

# Save to file
with open('stringing_output.json', 'w') as f:
    json.dump(output, f, indent=2)
```

---

## Notes

- **Minimum string length**: 3 panels (to meet minimum voltage requirements)
- **Ideal string length**: 9 panels (voltage-based, may be adjusted by power validation)
- **Temperature adjustments**: Automatically calculated based on state
- **Roof plane isolation**: Each roof plane is stringed independently
- **MPPT assignment**: Strings assigned to MPPTs based on voltage/current compatibility
- **Inverter assignment**: MPPTs grouped into inverters based on capacity

---

## Support

For issues or questions about the stringing optimizer, refer to the example files:
- `oct9design.json` - Standard input format
- `panel_specs.csv` - Panel specifications format
- `inverter_specs.csv` - Inverter specifications format

