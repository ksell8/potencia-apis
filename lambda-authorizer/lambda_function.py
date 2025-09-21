import json
import os
from typing import Dict, Any

import boto3
from botocore.exceptions import ClientError

def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Lambda authorizer function that validates API tokens from Secrets Manager.
    Returns an IAM policy based on token validation.
    """

    # Get the token from the Authorization header
    token = event.get('authorizationToken', '')
    method_arn = event.get('methodArn', '')

    # Remove 'Bearer ' prefix if present
    if token.startswith('Bearer '):
        token = token[7:]

    try:
        # Get the expected token from Secrets Manager
        secret_name = os.environ.get('SECRET_NAME', '/api/token')
        secrets_client = boto3.client('secretsmanager')

        response = secrets_client.get_secret_value(SecretId=secret_name)
        secret_data = json.loads(response['SecretString'])
        expected_token = secret_data.get('api_key', '')

        # Validate the token
        if token == expected_token and token:
            effect = 'Allow'
            principal_id = 'authorized-user'
        else:
            effect = 'Deny'
            principal_id = 'unauthorized'

        # Build the IAM policy
        policy = {
            'principalId': principal_id,
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': 'execute-api:Invoke',
                        'Effect': effect,
                        'Resource': method_arn
                    }
                ]
            },
            'context': {
                'authorized': str(effect == 'Allow').lower()
            }
        }

        return policy

    except KeyError as e:
        print(f"Configuration error: {str(e)}")
        return {
            'principalId': 'unauthorized',
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': 'execute-api:Invoke',
                        'Effect': 'Deny',
                        'Resource': method_arn
                    }
                ]
            },
            'context': {
                'authorized': 'false',
                'error': f"Configuration error: {str(e)}"
            }
        }
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {str(e)}")
        return {
            'principalId': 'unauthorized',
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': 'execute-api:Invoke',
                        'Effect': 'Deny',
                        'Resource': method_arn
                    }
                ]
            },
            'context': {
                'authorized': 'false',
                'error': f"JSON parsing error: {str(e)}"
            }
        }
    except ClientError as e:
        print(f"AWS Secrets Manager error: {str(e)}")
        return {
            'principalId': 'unauthorized',
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': 'execute-api:Invoke',
                        'Effect': 'Deny',
                        'Resource': method_arn
                    }
                ]
            },
            'context': {
                'authorized': 'false',
                'error': f"AWS error: {str(e)}"
            }
        }
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'principalId': 'unauthorized',
            'policyDocument': {
                'Version': '2012-10-17',
                'Statement': [
                    {
                        'Action': 'execute-api:Invoke',
                        'Effect': 'Deny',
                        'Resource': method_arn
                    }
                ]
            },
            'context': {
                'authorized': 'false',
                'error': f"Unexpected error: {str(e)}"
            }
        }
