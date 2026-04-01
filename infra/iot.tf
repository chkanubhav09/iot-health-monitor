# infra/iot.tf
# AWS IoT Core: Thing, Certificate policy, and Topic Rule

# IoT Thing
resource "aws_iot_thing" "patient_device" {
  name = "${var.project}-esp32-${var.environment}"
}

# IoT Policy
resource "aws_iot_policy" "device_policy" {
  name = "${var.project}-device-policy-${var.environment}"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect   = "Allow"
        Action   = ["iot:Connect"]
        Resource = "arn:aws:iot:${var.aws_region}:*:client/$${iot:ClientId}"
      },
      {
        Effect   = "Allow"
        Action   = ["iot:Publish"]
        Resource = "arn:aws:iot:${var.aws_region}:*:topic/health/*/vitals"
      },
      {
        Effect   = "Allow"
        Action   = ["iot:Subscribe"]
        Resource = "arn:aws:iot:${var.aws_region}:*:topicfilter/health/*/vitals"
      },
      {
        Effect   = "Allow"
        Action   = ["iot:Receive"]
        Resource = "arn:aws:iot:${var.aws_region}:*:topic/health/*/vitals"
      }
    ]
  })
}

# Topic Rule: route MQTT messages -> Lambda
resource "aws_iot_topic_rule" "vitals_ingest" {
  name        = "${replace(var.project, "-", "_")}_vitals_ingest_${var.environment}"
  enabled     = true
  sql         = "SELECT * FROM 'health/+/vitals'"
  sql_version = "2016-03-23"

  lambda {
    function_arn = aws_lambda_function.vitals_validator.arn
  }

  error_action {
    cloudwatch_logs {
      log_group_name = "/aws/iot/${var.project}"
      role_arn       = aws_iam_role.iot_logging.arn
    }
  }
}

# IAM Role for IoT to invoke Lambda
resource "aws_iam_role" "iot_logging" {
  name = "${var.project}-iot-logging-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "iot.amazonaws.com" }
    }]
  })
}

# Allow IoT to call the validator Lambda
resource "aws_lambda_permission" "iot_invoke_validator" {
  statement_id  = "AllowIoTInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.vitals_validator.function_name
  principal     = "iot.amazonaws.com"
  source_arn    = aws_iot_topic_rule.vitals_ingest.arn
}

output "iot_endpoint" {
  value = data.aws_iot_endpoint.current.endpoint_address
}

data "aws_iot_endpoint" "current" {
  endpoint_type = "iot:Data-ATS"
}
