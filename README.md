# Potencia API Middleware

This middleware serves as a bridge between Softr webhooks and Airtable, providing custom record logic and data transformation capabilities.

## Why This Middleware is Necessary

**Softr Webhook Limitations**: Softr's webhook system only supports flattened request bodies (simple key-value pairs), as shown in their Call API interface:

![Softr Webhook Interface](imgs/softr_webhook.png)

This creates a problem when working with Airtable, which often requires:

- Complex data structures
- Record relationships (arrays/lists)
- Computed fields based on input data
- Custom business logic before record creation

## Solution

This AWS Lambda-SQS middleware:

1. **Receives flattened data** from Softr webhooks
2. **Determines if request is valid** based on buisness logic and if so queues it for publish
2. **Applies custom transformations** using Pydantic models
3. **Formats data appropriately** for Airtable's API requirements
4. **Sends structured data** to Airtable

## Example: Match Records

For the `Matches` table, this middleware:

- Converts single `Learner` and `Tutor` strings to required list format
- Calculates `Overlapping Available Time Slots` by intersecting learner and tutor time slots
- Excludes intermediate time slot fields from the final record
- Maintains proper field naming conventions for Airtable

### Input (from Softr):
```json
{
  "Learner": "recJpeIQuMnAlfJ1R",
  "Tutor": "recuUhUFHYIQ6B3De",
  "Learner Available Time Slots": ["rec1", "rec2", "rec3"],
  "Tutor Available Time Slots": ["rec2", "rec4", "rec5"],
  "Approval Status": "Requested"
}
```

### Output (to Airtable):
```json
{
  "records": [{
    "fields": {
      "Learner": ["recJpeIQuMnAlfJ1R"],
      "Tutor": ["recuUhUFHYIQ6B3De"],
      "Overlapping Available Time Slots": ["rec2"],
      "Approval Status": "Requested"
    }
  }]
}
```

## Architecture

- **API Gateway**: REST API with OpenAPI specification
- **Lambda Authorizer**: Validates API tokens from Secrets Manager (`/api/token`)
- **Verifier Lambda**: Verifies that the match request is valid and then forwards it to the SQS.
- **Match SQS**: Match requests queue (deduplication and strong consistency provided with DynamoDB)
- **Lambda Event Source**: Waits for messages in SQS queue and then sends to main lambda worker.
- **Main Lambda**: Handles Airtable operations using credentials from Secrets Manager (`/api/token/airtable`)

## Rationale for this Architecture

We are working towards a matching workflow which will calculate all of the tutors who could possibly be matched against a user and sends the request.  Making this request have an synchronous kick off and an asynchronous fulfillment is a step in this direction.

## Endpoints

- `POST /airtable/{tableName}` - Create records in specified table

## Usage

### Authentication

Include your API key in the Authorization header:
```
Authorization: your-secure-api-key
```

### Example Request

```bash
curl -X POST https://your-api-gateway-url/prod/airtable/customers \
  -H "Authorization: your-secure-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "fields": {
      "Name": "John Doe",
      "Email": "john@example.com"
    }
  }'
```
