import json
import boto3
import os
import requests
from typing import Dict, Any, Optional

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda function that handles Airtable API operations.
    Processes requests to add record to /airtable/{tableName}.
    """

    try:
        # Parse the incoming request
        http_method = event.get('httpMethod', '')
        path = event.get('path', '')
        path_parameters = event.get('pathParameters', {}) or {}
        body = event.get('body', '')
        headers = event.get('headers', {})

        # Extract table name from path parameters
        table_name = path_parameters.get('tableName', '')

        if not table_name:
            return create_error_response(400, "Table name is required")

        # Get Airtable credentials from Secrets Manager
        airtable_config = get_airtable_config()
        if not airtable_config:
            return create_error_response(500, "Failed to retrieve Airtable configuration")

        airtable_token = airtable_config.get('token', '')
        base_id = airtable_config.get('base_id', '')

        if not airtable_token or not base_id:
            return create_error_response(500, "Missing Airtable token or base_id in configuration")

        # Handle different HTTP methods
        if http_method == 'POST':
            return handle_post_request(table_name, body, airtable_token, base_id)
        else:
            return create_error_response(405, f"Method {http_method} not allowed")

    except Exception as e:
        print(f"Error processing request: {str(e)}")
        return create_error_response(500, f"Internal server error: {str(e)}")

def get_airtable_config() -> Optional[Dict[str, str]]:
    """Get Airtable configuration from Secrets Manager."""
    try:
        secret_name = os.environ.get('AIRTABLE_SECRET_NAME', '/api/token/airtable')
        secrets_client = boto3.client('secretsmanager')

        response = secrets_client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])

    except Exception as e:
        print(f"Error retrieving Airtable config: {str(e)}")
        return None

def handle_post_request(table_name: str, body: str, token: str, base_id: str) -> Dict[str, Any]:
    """Handle POST request to create a new record."""
    try:
        if not body:
            return create_error_response(400, "Request body is required")

        # Parse the request body
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return create_error_response(400, "Invalid JSON in request body")

        # Convert flattened Softr format to Airtable format
        airtable_data = convert_softr_to_airtable(data)

        # Prepare Airtable API request
        url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        # Make request to Airtable
        response = requests.post(url, headers=headers, json=airtable_data)

        if response.status_code == 200:
            return {
                'statusCode': 200,
                'headers': {
                    'Content-Type': 'application/json'
                },
                'body': response.text
            }
        else:
            return create_error_response(response.status_code, f"Airtable API error: {response.text}")

    except Exception as e:
        print(f"Error in POST request: {str(e)}")
        return create_error_response(500, f"Error creating record: {str(e)}")

def convert_softr_to_airtable(softr_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert flattened Softr webhook data to Airtable API format.

    Input (Softr format):
    {
        "name": "John Doe",
        "email": "john@example.com",
        "age": 30
    }

    Output (Airtable format):
    {
        "records": [
            {
                "fields": {
                    "name": "John Doe",
                    "email": "john@example.com",
                    "age": 30
                }
            }
        ]
    }
    """
    return {
        "records": [
            {
                "fields": softr_data
            }
        ]
    }

def create_error_response(status_code: int, message: str) -> Dict[str, Any]:
    """Create a standardized error response."""
    return {
        'statusCode': status_code,
        'headers': {
            'Content-Type': 'application/json'
        },
        'body': json.dumps({
            'error': message,
            'code': status_code
        })
    }
