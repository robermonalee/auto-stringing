import json
import os
import sys
import traceback

# Add the directory containing the stringer modules to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__))))

from simple_stringing import SimpleStringingOptimizer
import data_parsers

def lambda_handler(event, context):
    """
    AWS Lambda handler for the Solar Stringing Optimizer.
    """
    # Health Check for GET requests
    if event.get('requestContext', {}).get('http', {}).get('method') == 'GET':
        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({'status': 'ok', 'message': 'API is healthy.'})
        }

    try:
        # Main stringing logic for POST requests
        if event.get('requestContext', {}).get('http', {}).get('method') != 'POST':
            return {
                'statusCode': 405,
                'body': json.dumps({'error': 'Method Not Allowed'})
            }

        # Parse the input from the event body
        body = json.loads(event.get('body', '{}'))

        # Extract required inputs
        auto_design = body.get('auto_design')
        panel_specs_data = body.get('panel_specs')
        inverter_specs_data = body.get('inverter_specs')
        state = body.get('state')

        # Extract optional inputs
        inverters_quantity = body.get('inverters_quantity')
        override_inv_quantity = body.get('override_inv_quantity', False)

        # Validate required inputs
        if not all([auto_design, panel_specs_data, inverter_specs_data, state]):
            return {
                'statusCode': 400,
                'body': json.dumps({'error': 'Missing required input parameters.'})
            }

        # Create panel specs objects
        panels = data_parsers.create_panel_specs_objects(auto_design, panel_specs_data)

        # Create inverter specs object
        inverter = data_parsers.create_inverter_specs_object(inverter_specs_data)

        # Parse temperature data
        temp_data_path = os.path.join(os.path.dirname(__file__), 'amb_temperature_data.csv')
        temp = data_parsers.parse_temperature_data_csv(temp_data_path, state)

        # Initialize optimizer
        optimizer = SimpleStringingOptimizer(
            panels,
            inverter,
            temp,
            auto_design_data=auto_design,
            inverters_quantity=inverters_quantity
        )

        # Run optimization
        result = optimizer.optimize(override_inv_quantity=override_inv_quantity)

        return {
            'statusCode': 200,
            'body': json.dumps(result.formatted_output)
        }

    except json.JSONDecodeError:
        return {
            'statusCode': 400,
            'body': json.dumps({'error': 'Invalid JSON in request body.'})
        }
    except Exception as e:
        print(traceback.format_exc())
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal Server Error', 'details': str(e)})
        }
