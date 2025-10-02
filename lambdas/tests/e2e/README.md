# 🧪 End-to-End Testing Setup

These tests focus on the features of the NDR. This will serve as a blended suite of integration and end-to-end (E2E) tests, with the aim to validate API functionality and snapshot comparisons.

## 🔧 Available Make Commands

- `make test-api-e2e` — Runs the full suite of E2E tests.
- `make test-api-e2e-snapshots` — Runs snapshot comparison tests.

### Snapshots

Snapshots reduce the amount of individual assertions by comparing pre and post an object e.g. a JSON returned from an API
To update snapshots you can run pytest with the additional argument `--snapshot-update` this will replace the existing snapshots

`make test-api-e2e
make test-api-e2e-snapshots`

## 🌍 Required Environment Variables

In order to execute these tests you will need to have a default AWS configuration pointed to your environment under tests.

In addition ensure the following environment variables are exported in your shell configuration file (`~/.zshrc` or `~/.bashrc`):

| Environment Variable | Description                                                                                                                       |
| -------------------- | --------------------------------------------------------------------------------------------------------------------------------- |
| `NDR_API_KEY`        | The API key required to authenticate requests to the NDR API. API Gateway → API Keys for associated env e.g. ndr-dev_apim-api-key |
| `NDR_API_ENDPOINT`   | The URI string used to connect to the NDR API.                                                                                    |
| `NDR_S3_BUCKET`      | The name of the Store e.g. ndr-dev-lloyd-george-store.                                                                            |
| `NDR_DYNAMO_STORE`   | The name of the Reference Data Store e.g. ndr-dev_LloydGeorgeReferenceMetadata.                                                   |
| `MOCK_CIS2_KEY`      | The value of the Mock CIS2 Key. Found in Parameter Store: /auth/password/MOCK_KEY                                                 |

After updating your shell config, reload it:

```bash
source ~/.zshrc   # or source ~/.bashrc
```

### 🔐 AWS Authentication

You must be authenticated with AWS to run the tests. Use the following commands with a configured profile set up in ~/.aws/config to authenticate:

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
