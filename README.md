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

## 🧪 End-to-End Testing

See [E2E testing](lambdas/tests/e2e/README.md) README.
