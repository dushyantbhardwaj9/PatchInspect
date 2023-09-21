
# PatchInspect

PatchInspect is a serverless solution that computes patch compliance percentages for each server in your AWS environment using AWS Lambda and Systems Manager (SSM). Utilizing this tool makes it simple to oversee patch compliance across your whole AWS infrastructure.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration](#configuration)
- [Logging](#logging)
- [Visualization](#visualization)
- [Contributing](#contributing)
- [License](#license)

## Features

- **Serverless**: PatchInspect is built on AWS Lambda, making it cost-effective and scalable.
- **Automated**: It automatically collects and computes patch compliance, reducing manual effort.
- **Customizable**: You can customize PatchInspect to fit your organization's patch compliance policies.
- **Reporting**: Obtain patch compliance reports as raw findings in JSON format.
- **Logging**: PatchInspect logs findings in a CloudWatch Log Group for further analysis.

## Prerequisites

Before getting started with PatchInspect, make sure you have the following prerequisites:

- An AWS account with appropriate permissions to create and manage Lambda functions, SSM resources, EventBridge rules, and CloudWatch Logs.
- [AWS CLI](https://aws.amazon.com/cli/) installed and configured with the necessary credentials.
- [Terraform](https://www.terraform.io/) installed on your local machine.

## Deployment

To deploy PatchInspect in your AWS environment using Terraform, follow these steps:

1. Clone this GitHub repository:
   ```shell
   git clone https://github.com/yourusername/PatchInspect.git
    ```

2. Navigate to the PatchInspect directory:
    ```shell
    cd PatchInspect
    ```

3. Initialize Terraform:
    ```shell
    terraform init
    ```

4. Review and customize the following configuration files to match your AWS environment:
    - variables.tf: Define Terraform variables that can be customized.
    - terraform.auto.tfvars: Provide values for the Terraform variables, including AWS region, tags, IAM roles, and other settings.

5. Apply the Terraform configuration to create the necessary resources:
    ```shell
    terraform apply
    ```

6. Once the deployment is complete, PatchInspect will be up and running in your AWS environment.

## Usage
1. Every Monday morning, on a predetermined schedule through AWS EventBridge, PatchInspect gathers patch compliance data. It can be set up to collect at any time period (hours, days, or weeks). If required, it can also be triggered on demand.
2. The Lambda function runs on every Monday to check patch compliance for all servers in the accounts specified in accounts.json.

Patch compliance reports are obtained as raw findings for each server in JSON format. You can export and analyze these findings using your preferred log analysis or visualization tool.

## Configuration
- variables.tf and terraform.auto.tfvars
- variables.tf: This file defines Terraform variables that can be customized. Review and modify this file to suit your configuration needs.
- terraform.auto.tfvars: Provide values for the Terraform variables in this file. Include AWS region, tags, IAM roles, and other settings as required.

## Logging
PatchInspect logs its findings in a CloudWatch Log Group named PatchInspect_findings. You can configure log retention policies and access controls for this log group in the AWS Management Console.

## Visualization
To visualize and analyze the findings logged by PatchInspect, you can integrate the CloudWatch Logs with visualization tools like ELK (Elasticsearch, Logstash, Kibana) or other log analysis solutions. Here are the general steps:

1. Set up Elasticsearch: Create an Elasticsearch cluster where the log data will be stored.
2. Set up Logstash: Configure Logstash to pull data from the CloudWatch Log Group and send it to Elasticsearch.
3. Set up Kibana: Use Kibana to create custom dashboards and visualizations for your log data.
4. Configure Log Forwarding: Ensure that CloudWatch Logs are configured to forward log data to your Logstash instance.
5. Analyze Data: Access Kibana to analyze and visualize your PatchInspect findings easily.

## Contributing
We welcome contributions to PatchInspect! If you have any ideas for improvements, bug fixes, or new features, please open an issue or submit a pull request. Check out our contributing guidelines for more details.

## License
This project is licensed under the Apache License 2.0. You are free to use, modify, and distribute the code as per the terms of the license.