import json
import boto3
import os
import requests
import logging
from typing import Dict, Any, Optional
from pydantic import ValidationError
from models import Match, MatchInput
from datetime import datetime, timezone

# Initialize logger
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main Lambda function that processes SQS messages for Airtable API operations.
    Updates DynamoDB status and calls Airtable API.
    """

    try:
        # Process SQS records
        records = event.get('Records', [])

        for record in records:
            # Parse SQS message
            message_body = json.loads(record['body'])
            message_attributes = record.get('messageAttributes', {})

            # Extract data from message
            table_name = message_attributes.get('TableName', {}).get('stringValue', '')
            match_combo_id = message_attributes.get('MatchComboId', {}).get('stringValue', '')

            if not table_name or not match_combo_id:
                logger.error(f"Missing required message attributes: table_name={table_name}, match_combo_id={match_combo_id}")
                continue

            # Update DynamoDB status to PROCESSING
            try:
                update_dynamodb_status(match_combo_id, 'PROCESSING')
            except Exception as e:
                logger.error(f"Error updating DynamoDB status to PROCESSING: {str(e)}")
                continue

            # Get Airtable credentials from Secrets Manager
            airtable_config = get_airtable_config()
            if not airtable_config:
                update_dynamodb_status(match_combo_id, 'FAILED', 'Failed to retrieve Airtable configuration')
                continue

            airtable_token = airtable_config.get('token', '')
            base_id = airtable_config.get('base_id', '')

            if not airtable_token or not base_id:
                update_dynamodb_status(match_combo_id, 'FAILED', 'Missing Airtable token or base_id')
                continue

            # Process the message and call Airtable API
            try:
                result = process_airtable_request(table_name, message_body, airtable_token, base_id)
                if result['success']:
                    update_dynamodb_status(match_combo_id, 'COMPLETED')
                    logger.info(f"Successfully processed match {match_combo_id}")
                else:
                    update_dynamodb_status(match_combo_id, 'FAILED', result['error'])
                    logger.error(f"Failed to process match {match_combo_id}: {result['error']}")
            except Exception as e:
                update_dynamodb_status(match_combo_id, 'FAILED', str(e))
                logger.error(f"Error processing match {match_combo_id}: {str(e)}")

        return {'statusCode': 200, 'body': 'Processing completed'}

    except Exception as e:
        logger.error(f"Error processing SQS event: {str(e)}")
        return {'statusCode': 500, 'body': f"Error: {str(e)}"}

def get_airtable_config() -> Optional[Dict[str, str]]:
    """Get Airtable configuration from Secrets Manager."""
    try:
        secret_name = os.environ.get('AIRTABLE_SECRET_NAME', '/api/token/airtable')
        secrets_client = boto3.client('secretsmanager')

        response = secrets_client.get_secret_value(SecretId=secret_name)
        return json.loads(response['SecretString'])

    except Exception as e:
        logger.error(f"Error retrieving Airtable config: {str(e)}")
        return None

def update_dynamodb_status(match_combo_id: str, status: str, error_message: str = None) -> None:
    """Update DynamoDB record status."""
    try:
        table = dynamodb.Table('matches-queue')

        update_expression = 'SET #status = :status'
        expression_attribute_names = {'#status': 'Status'}
        expression_attribute_values = {':status': status}

        if error_message:
            update_expression += ', ErrorMessage = :error'
            expression_attribute_values[':error'] = error_message

        table.update_item(
            Key={
                'MatchComboId': match_combo_id
            },
            UpdateExpression=update_expression,
            ExpressionAttributeNames=expression_attribute_names,
            ExpressionAttributeValues=expression_attribute_values
        )

    except Exception as e:
        logger.error(f"Error updating DynamoDB status: {str(e)}")
        raise e

def process_airtable_request(table_name: str, message_body: Dict[str, Any], token: str, base_id: str) -> Dict[str, Any]:
    """Process message body and make Airtable API request."""
    try:
        # Convert flattened format to Airtable format
        try:
            airtable_data = convert_softr_to_airtable(message_body, table_name)
        except ValueError as e:
            return {'success': False, 'error': f"Validation error: {str(e)}"}

        # Prepare Airtable API request
        url = f"https://api.airtable.com/v0/{base_id}/{table_name}"
        headers = {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/json'
        }

        # Make request to Airtable
        response = requests.post(url, headers=headers, json=airtable_data)

        if response.status_code == 200:
            return {'success': True, 'response': response.json()}
        else:
            return {'success': False, 'error': f"Airtable API error: {response.text}"}

    except Exception as e:
        return {'success': False, 'error': f"Error processing request: {str(e)}"}

def convert_softr_to_airtable(softr_data: Dict[str, Any], table_name: str) -> Dict[str, Any]:
    """
    Convert flattened Softr webhook data to Airtable API format.

    For matches table, uses Match model for data transformation.
    For other tables, uses direct field mapping.

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
    if table_name.lower() == "matches":
        try:
            # Use Match model for matches table
            match_input = MatchInput(**softr_data)
            match = Match.from_input(match_input)
            return {
                "records": [
                    {
                        "fields": match.model_dump(by_alias=True)
                    }
                ]
            }
        except ValidationError as e:
            # Re-raise with a more specific error message for matches table
            missing_fields = []
            for error in e.errors():
                if error['type'] == 'missing':
                    field_name = error['loc'][0] if error['loc'] else 'unknown'
                    missing_fields.append(field_name)

            if missing_fields:
                logger.error(f"Missing required fields for matches table: {', '.join(missing_fields)}")
                raise ValueError(f"Missing required fields for matches table: {', '.join(missing_fields)}")
            else:
                logger.error(f"Validation error for matches table: {str(e)}")
                raise ValueError(f"Validation error for matches table: {str(e)}")
    else:
        # Default behavior for other tables
        return {
            "records": [
                {
                    "fields": softr_data
                }
            ]
        }
