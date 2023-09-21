data "aws_caller_identity" "current" {}

locals {
  role_arn = resource.aws_iam_role.role.arn

  env_vars = {
    SUBNET_ID       = module.network.subnet_id                                                                                           # Subnet Id for compliant server
    IAM_PROFILE_ARN = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:instance-profile/AmazonSSMRoleForInstancesQuickSetup" # IAM profile ARN for compliant server
    QUEUE_URL       = aws_sqs_queue.queue.id
    SG_ID           = module.network.sg_id # Security group ID for compliant server
    ROLE_NAME       = var.iam_role
  }
}

# IAM role 
data "aws_iam_policy_document" "assume_role_policy" {
  statement {
    actions = ["sts:AssumeRole"]

    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "role" {
  name                = var.iam_role
  assume_role_policy  = data.aws_iam_policy_document.assume_role_policy.json
  managed_policy_arns = [aws_iam_policy.iam_policy.arn]

}

resource "aws_iam_policy" "iam_policy" {
  name   = "${var.project}_policy"
  policy = file("data/iamPolicy.json")
}

# create necessary network resources: VPC, route table, 1 Internet gateway, 1 public subnet, 1 security group

data "aws_availability_zones" "available" {
  state = "available"
}

module "network" {
  source = "./modules/networking"

  project     = var.project
  vpc_cidr    = "10.0.0.0/24"
  subnet_cidr = "10.0.0.0/28"
  az          = data.aws_availability_zones.available.names[0]
}

# creates lambda functions

module "initiate" {
  source = "./modules/lambda_function"

  rule_name = "initiate"
  env_vars  = local.env_vars
  role_arn  = local.role_arn
}

module "list_instances" {
  source = "./modules/lambda_function"

  env_vars  = local.env_vars
  rule_name = "list_instances"
  rule      = true
  role_arn  = local.role_arn
}

# create sqs queue for validateInstanceCompliance

resource "aws_sqs_queue" "queue" {
  name                      = "patch_inspect_instances"
  delay_seconds             = 5
  message_retention_seconds = 86400
  receive_wait_time_seconds = 20

  visibility_timeout_seconds = 920

  tags = {
    Name    = "patch_inspect_instances"
    Service = "sqs"
  }
}

resource "aws_lambda_event_source_mapping" "sqs_lambda_mapping" {
  event_source_arn = aws_sqs_queue.queue.arn
  function_name    = module.validate_instance_compliance.function_arn

  maximum_batching_window_in_seconds = 30
  batch_size                         = 50
  scaling_config {

    maximum_concurrency = 4
  }
}

module "validate_instance_compliance" {
  source = "./modules/lambda_function"

  env_vars  = local.env_vars
  rule_name = "validate_instance_compliance"
  role_arn  = local.role_arn
}

# creates log group to publish findings

resource "aws_cloudwatch_event_rule" "findings_rule" {

  name        = "${var.project}_findings"
  description = "Rule to trigger Patch Inspect findings"

  event_pattern = file("data/event_pattern/findings.json")

  tags = {
    Name    = "${var.project}_findings"
    Service = "eventbridge"
  }

}

resource "aws_cloudwatch_event_target" "rule_target" {

  target_id = "log"
  arn       = aws_cloudwatch_log_group.findings.arn
  rule      = aws_cloudwatch_event_rule.findings_rule.name
}

resource "aws_cloudwatch_log_group" "findings" {
  name = "/aws/events/${var.project}_findings"

  tags = {
    Name    = "/aws/events/${var.project}_findings"
    Service = "cloudwatch"
  }
}

data "aws_iam_policy_document" "log_policy" {
  statement {
    effect = "Allow"
    actions = [
      "logs:CreateLogStream"
    ]

    resources = [
      "${aws_cloudwatch_log_group.findings.arn}:*"
    ]

    principals {
      type = "Service"
      identifiers = [
        "events.amazonaws.com"
      ]
    }
  }
  statement {
    effect = "Allow"
    actions = [
      "logs:PutLogEvents"
    ]

    resources = [
      "${aws_cloudwatch_log_group.findings.arn}:*:*"
    ]

    principals {
      type = "Service"
      identifiers = [
        "events.amazonaws.com"
      ]
    }

    condition {
      test     = "ArnEquals"
      values   = [aws_cloudwatch_event_rule.findings_rule.arn]
      variable = "aws:SourceArn"
    }
  }
}

resource "aws_cloudwatch_log_resource_policy" "findings_policy" {
  policy_document = data.aws_iam_policy_document.log_policy.json
  policy_name     = "${var.project}-findings-publishing-policy"
}
