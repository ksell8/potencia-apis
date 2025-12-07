# Install pre-commit

    $ pip install pre-commit
    $ pre-commit install

This will setup the git hooks for the project.

# Install terraform

See [Install Terraform](https://developer.hashicorp.com/terraform/tutorials/aws-get-started/install-cli).

## Setup

### 1. Create Secrets in AWS Secrets Manager

Create two secrets manually:

**Authorization Secret** (`/api/token`):
```json
{
  "api_key": "your-secure-api-key-here"
}
```

**Airtable Secret** (`/api/token/airtable`):
```json
{
  "token": "your-airtable-personal-access-token",
  "base_id": "your-airtable-base-id"
}
```

### 2. Build Lambda Functions

```bash
./build.sh
```

### 3. Deploy with Terraform

```bash
terraform init
terraform plan
terraform apply
```
