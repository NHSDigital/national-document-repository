# national-document-repository

## Lamda Function Intro

Our Lambda function readme can be found [here](lambdas/README.md)

## React User Interface Intro

Our React User Interface readme can be found [here](app/README.md)

## Installation

- [Git](https://git-scm.com/)
- [Terraform](https://formulae.brew.sh/formula/terraform)
- [docker](https://formulae.brew.sh/formula/docker)
- [docker-compose](https://formulae.brew.sh/formula/docker-compose)
- [AWS CLI](https://aws.amazon.com/cli/)
- [Awsume](https://formulae.brew.sh/formula/awsume)
- [ruff](https://formulae.brew.sh/formula/ruff)
- [Node@24](https://formulae.brew.sh/formula/node@24)
- [Python@3.11](https://formulae.brew.sh/formula/python@3.11)

_Note: It is recommended to use [Homebrew](https://brew.sh/) to install most of these._

## Monitoring

We have configured AWS CloudWatch to provide alarm notifications whenever one of a number of metrics exceeds its normal
state. Currently, the only way to receive these notifications is by subscribing to an SNS topic using an email. You can
subscribe to the SNS topic once you have assumed an appropriate role using the AWS CLI. This is the command:

```bash
aws sns subscribe --topic-arn [topic-arn] --protocol email --notification-endpoint [your NHS email]
```

You will receive a confirmation email with a link allowing you to confirm the subscription. We are also subscribing to
the SNS topic using email addresses that are provided for Microsoft Teams channels.

## 🧪 End-to-End Testing Setup

This project includes E2E tests for validating API functionality and snapshot comparisons. To run these tests, follow the steps below.

### 🔧 Available Make Commands

- `make test-api-e2e` — Runs the full suite of E2E tests.
- `make test-api-e2e-snapshots` — Runs snapshot comparison tests.

### 🌍 Required Environment Variables

Ensure the following environment variables are set in your shell configuration file (`~/.zshrc` or `~/.bashrc`):

```bash
export NDR_API_ENDPOINT=<your-api-endpoint>         # Get value from API Gateway
export NDR_API_KEY=<your-api-key>                   # Get value from API Gateway → API Keys for associated env e.g. ndr-dev_apim-api-key
export NDR_S3_BUCKET=<your-s3-bcuket>               # S3 bucket e.g. ndr-dev-lloyd-george-store
export MOCK_CIS2_KEY=<mock-key>                     # Get value from Parameter Store: /auth/password/MOCK_KEY
export NDR_DYNAMO_STORE=<your-dynamo-table>         # DynamoDB table name e.g. ndr-dev_LloydGeorgeReferenceMetadata
```

After updating your shell config, reload it:

```bash
source ~/.zshrc   # or source ~/.bashrc
```

### 🔐 AWS Authentication

You must be signed in to AWS to run the tests. Use the following commands with a profile set up in ~/.aws/config to authenticate:

```bash
aws sso login --profile <your-aws-profile>

export AWS_PROFILE=<your-aws-profile>
```

An exmaple profile:

```bash
[sso-session PRM]
sso_start_url = https://d-9c67018f89.awsapps.com/start#
sso_region = eu-west-2

[profile NDR-Dev-RW]
sso_session=PRM
sso_account_id=<dev-aws-account-id>
sso_role_name=DomainCGpit-Administrators
region=eu-west-2
output=json
```

Make sure your AWS profile has access to the required resources.
