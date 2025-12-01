import json
import boto3
import os
from datetime import datetime, timezone
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
sqs = boto3.client('sqs')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    """
    Verifier Lambda that:
    1. Validates incoming requests (placeholder for now)
    2. Creates a unique ID for deduplication using Learner#Tutor
    3. Adds entry to DynamoDB with 'PENDING' status
    4. Sends original body to SQS queue
    """

    try:
        # Check HTTP method - only POST is allowed
        http_method = event.get('httpMethod', '')
        if http_method != 'POST':
            return {
                'statusCode': 405,
                'body': json.dumps({
                    'message': f'Method {http_method} not allowed. Only POST requests are supported.',
                    'error': 'METHOD_NOT_ALLOWED'
                })
            }

        # Parse the incoming request
        table_name = event['pathParameters']['tableName']
        body = json.loads(event['body'])

        # Extract Learner and Tutor from body to create match combo ID
        learner = body.get('Learner')
        tutor = body.get('Tutor')

        if not learner or not tutor:
            return {
                'statusCode': 400,
                'body': json.dumps({
                    'message': 'Missing required fields: Learner and Tutor',
                    'error': 'MISSING_FIELDS'
                })
            }

        # Generate match combo ID
        match_combo_id = f"{learner}#{tutor}"

        # Generate timestamp
        timestamp = datetime.now(timezone.utc).isoformat()

        # Check for existing entry in DynamoDB (deduplication)
        table = dynamodb.Table('matches-queue')

        try:
            response = table.get_item(
                Key={
                    'MatchComboId': match_combo_id
                }
            )

            # If item exists and is not completed, return failure
            if 'Item' in response and response['Item'].get('Status') in ['PENDING', 'PROCESSING']:
                return {
                    'statusCode': 409,
                    'body': json.dumps({
                        'message': 'Match request already exists',
                        'matchId': match_combo_id,
                        'status': 'FAILED',
                        'error': 'DUPLICATE_REQUEST'
                    })
                }
        except Exception as e:
             return {
                    'statusCode': 503,
                    'body': json.dumps({
                        'message': 'Error Checking Dynamo DB',
                        'matchId': match_combo_id,
                        'status': 'FAILED',
                        'error': str(e)
                    })
                }

        # Create DynamoDB entry with pending status
        try:
            table.put_item(
                Item={
                    'MatchComboId': match_combo_id,
                    'MatchTimestamp': timestamp,
                    'Status': 'PENDING',
                    'TableName': table_name,
                    'RequestBody': body,
                    'MatchRequestExpiry': int((datetime.now(timezone.utc).timestamp() + 86400))  # 24 hours TTL
                }
            )
        except Exception as e:
            logger.error(f"Error writing to DynamoDB: {e}")
            raise e

        # Send original body to SQS
        try:
            queue_url = os.environ.get('SQS_QUEUE_URL')
            if not queue_url:
                raise ValueError("SQS_QUEUE_URL environment variable not set")

            sqs_response = sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=json.dumps(body),
                MessageAttributes={
                    'MatchComboId': {
                        'StringValue': match_combo_id,
                        'DataType': 'String'
                    },
                    'TableName': {
                        'StringValue': table_name,
                        'DataType': 'String'
                    },

                }
            )

            logger.info(f"Message sent to SQS: {sqs_response['MessageId']}")

        except Exception as e:
            logger.error(f"Error sending to SQS: {e}")
            # Update DynamoDB status to failed
            table.update_item(
                Key={
                    'MatchComboId': match_combo_id,
                    'MatchTimestamp': timestamp
                },
                UpdateExpression='SET #status = :status, ErrorMessage = :error',
                ExpressionAttributeNames={'#status': 'Status'},
                ExpressionAttributeValues={
                    ':status': 'FAILED',
                    ':error': str(e)
                }
            )
            raise e

        # Return success response
        return {
            'statusCode': 202,
            'body': json.dumps({
                'message': 'Request queued successfully',
                'matchId': match_combo_id,
                'status': 'PENDING'
            })
        }

    except Exception as e:
        logger.error(f"Verifier Lambda error: {e}")
        return {
            'statusCode': 500,
            'body': json.dumps({
                'message': 'Internal server error',
                'error': str(e)
            })
        }
