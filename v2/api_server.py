"""
Flask API Server for Solar Stringing Optimizer
Provides REST API endpoints for stringing optimization
"""

from flask import Flask, request, jsonify
from simple_stringing import SimpleStringingOptimizer
import data_parsers
import json
import traceback

app = Flask(__name__)

# Load static data files once at startup
try:
    PANEL_SPECS_CSV = data_parsers.parse_panel_specs_csv('panel_specs.csv')
    INVERTER_SPECS_CSV = data_parsers.parse_inverter_specs_csv('inverter_specs.csv')
    TEMP_DATA_CSV = 'amb_temperature_data.csv'
    print("✅ Static data files loaded successfully")
except Exception as e:
    print(f"❌ Error loading data files: {e}")
    raise


@app.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        "status": "healthy",
        "service": "Solar Stringing Optimizer API",
        "version": "v2.0"
    }), 200


@app.route('/api/optimize', methods=['POST'])
def optimize_stringing():
    """
    Main optimization endpoint
    
    Request Body:
    {
        "design": {...},              // Auto-design JSON structure
        "state": "California",        // State name for temperature data
        "validate_power": true,       // Optional: enable power validation (default: false)
        "output_frontend": true       // Optional: frontend format (default: false)
    }
    
    Returns:
    {
        "success": true,
        "data": {...},                // Stringing output
        "metadata": {
            "panels_stringed": 58,
            "total_panels": 63,
            "strings_created": 15,
            "inverters_used": 15
        }
    }
    """
    try:
        # Parse request
        data = request.get_json()
        
        if not data:
            return jsonify({
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        # Extract parameters
        design = data.get('design')
        state = data.get('state', 'California')
        validate_power = data.get('validate_power', False)
        output_frontend = data.get('output_frontend', False)
        
        if not design:
            return jsonify({
                "success": False,
                "error": "Missing 'design' field in request"
            }), 400
        
        # Create panel specs from design
        panels = data_parsers.create_panel_specs_objects(design, PANEL_SPECS_CSV)
        
        # Create inverter specs
        inverter = data_parsers.create_inverter_specs_object(INVERTER_SPECS_CSV)
        
        # Parse temperature data for the state
        temp = data_parsers.parse_temperature_data_csv(TEMP_DATA_CSV, state)
        
        # Run optimization
        optimizer = SimpleStringingOptimizer(
            panels, 
            inverter, 
            temp,
            output_frontend=output_frontend
        )
        
        result = optimizer.optimize(validate_power=validate_power)
        
        # Build response
        output = result.formatted_output
        
        response = {
            "success": True,
            "data": output,
            "metadata": {
                "panels_stringed": output['summary']['total_panels_stringed'],
                "total_panels": output['summary']['total_panels'],
                "strings_created": output['summary']['total_strings'],
                "inverters_used": output['summary']['total_inverters_used'],
                "state": state,
                "validate_power": validate_power,
                "output_frontend": output_frontend
            }
        }
        
        # Add suggestions if present
        if 'suggestions' in output and output['suggestions']:
            response["metadata"]["suggestions"] = output['suggestions']
        
        return jsonify(response), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e),
            "traceback": traceback.format_exc()
        }), 500


@app.route('/api/validate', methods=['POST'])
def validate_design():
    """
    Validation endpoint - checks design without full optimization
    
    Request Body:
    {
        "design": {...},
        "state": "California"
    }
    
    Returns:
    {
        "success": true,
        "validation": {
            "total_panels": 63,
            "roof_planes": 6,
            "estimated_strings": 9,
            "estimated_inverters": 5,
            "preliminary_dc_ac_ratio": 21.39
        }
    }
    """
    try:
        data = request.get_json()
        
        if not data or not data.get('design'):
            return jsonify({
                "success": False,
                "error": "Missing 'design' field"
            }), 400
        
        design = data['design']
        state = data.get('state', 'California')
        
        # Create specs
        panels = data_parsers.create_panel_specs_objects(design, PANEL_SPECS_CSV)
        inverter = data_parsers.create_inverter_specs_object(INVERTER_SPECS_CSV)
        temp = data_parsers.parse_temperature_data_csv(TEMP_DATA_CSV, state)
        
        # Get roof plane count
        roof_planes = set()
        for panel in panels:
            roof_planes.add(panel.roof_plane_id)
        
        # Quick estimation
        total_panels = len(panels)
        estimated_strings = total_panels // 7  # Rough estimate
        estimated_inverters = max(1, estimated_strings // 2)
        
        # Calculate preliminary DC/AC
        panel_sample = panels[0]
        temp_coeff_vmpp = 0.00446
        temp_diff_hot = temp.max_temp_c - 25.0
        vmpp_hot = panel_sample.vmpp_stc * (1 + temp_coeff_vmpp * temp_diff_hot)
        power_per_panel = vmpp_hot * panel_sample.impp_stc
        total_dc_power = total_panels * power_per_panel
        preliminary_dc_ac = total_dc_power / inverter.rated_ac_power_w if inverter.rated_ac_power_w else 0
        
        return jsonify({
            "success": True,
            "validation": {
                "total_panels": total_panels,
                "roof_planes": len(roof_planes),
                "estimated_strings": estimated_strings,
                "estimated_inverters": estimated_inverters,
                "preliminary_dc_ac_ratio": round(preliminary_dc_ac, 2),
                "inverter_model": inverter.model,
                "inverter_ac_capacity_w": inverter.rated_ac_power_w
            }
        }), 200
        
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500


if __name__ == '__main__':
    print("="*80)
    print("🚀 Starting Solar Stringing Optimizer API Server")
    print("="*80)
    print("\nEndpoints:")
    print("  GET  /health             - Health check")
    print("  POST /api/optimize       - Run stringing optimization")
    print("  POST /api/validate       - Validate design (quick check)")
    print("\nServer will run on: http://localhost:5000")
    print("="*80)
    
    app.run(host='0.0.0.0', port=5000, debug=True)

