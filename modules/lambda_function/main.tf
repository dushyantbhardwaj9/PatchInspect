# lambda

data "archive_file" "code_zip" {
  type        = "zip"
  output_path = "func/${var.rule_name}.zip"

  source_dir = "src/"
}


resource "aws_lambda_function" "use_case" {
  # If the file is not in the current working directory you will need to include a
  # path.module in the filename.
  filename      = data.archive_file.code_zip.output_path
  function_name = "${var.project}_${var.rule_name}"
  role          = var.role_arn
  handler       = "${var.rule_name}.lambda_handler"

  source_code_hash = data.archive_file.code_zip.output_base64sha256
  layers = var.layers


  memory_size = var.memory_size
  runtime = "python3.9"
  timeout = var.timeout

  environment {
    variables = var.env_vars
  }

  tags = {
    Name = "${var.project}_${var.rule_name}"
    Service = "lambda"
  }

}

# eventbridge rule

resource "aws_cloudwatch_event_rule" "rule" {
  count = var.rule == true ? 1 : 0

  name        = "${var.project}_${var.rule_name}"
  description = "Rule to trigger Patch Inspect function - ${var.rule_name}"

  event_pattern = file("data/event_pattern/${var.rule_name}.json")
  is_enabled = var.rule_enabled

    tags = {
    Name = "${var.project}_${var.rule_name}"
    Service = "eventbridge"
  }

}

resource "aws_cloudwatch_event_target" "rule_target" {
  count = var.rule == true ? 1 : 0

  target_id = "lambda"
  arn       = aws_lambda_function.use_case.arn
  rule      = aws_cloudwatch_event_rule.rule[0].name
}

resource "aws_lambda_permission" "rule_permission" {
  count = var.rule == true ? 1 : 0

  statement_id = "AllowExecutionFromCloudWatch"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.use_case.function_name
  principal = "events.amazonaws.com"
  source_arn = aws_cloudwatch_event_rule.rule[0].arn
}



resource "aws_cloudwatch_event_rule" "cron_rule" {
  count = var.cron != "false" ? 1 : 0

  name        = "${var.project}_${var.rule_name}"
  description = "Patch compliance rule for ${var.rule_name}"

  is_enabled = var.rule_enabled
  schedule_expression = var.cron

  tags = {
    Name = "${var.project}_${var.rule_name}"
    Service = "eventbridge"
  }

}

# eventrbidge target

resource "aws_cloudwatch_event_target" "cron_rule_target" {
  count = var.cron != "false" ? 1 : 0
  
  target_id = "lambda"
  arn       = aws_lambda_function.use_case.arn
  rule      = aws_cloudwatch_event_rule.cron_rule[0].name
}

resource "aws_lambda_permission" "cron_rule_permission" {
  count = var.cron != "false" ? 1 : 0

  statement_id = "AllowExecutionFromCloudWatch"
  action = "lambda:InvokeFunction"
  function_name = aws_lambda_function.use_case.function_name
  principal = "events.amazonaws.com"
  source_arn = aws_cloudwatch_event_rule.cron_rule[0].arn
}