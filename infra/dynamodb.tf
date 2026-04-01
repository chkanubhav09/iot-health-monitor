# infra/dynamodb.tf
# DynamoDB table for vitals storage with TTL and Streams

resource "aws_dynamodb_table" "vitals" {
  name           = "${var.project}-vitals-${var.environment}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "device_id"
  range_key      = "timestamp"

  attribute {
    name = "device_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "N"
  }

  # 90-day automatic data expiry
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  # Enable Streams to trigger anomaly detector Lambda
  stream_enabled   = true
  stream_view_type = "NEW_IMAGE"

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name = "${var.project}-vitals"
  }
}

# Lambda triggered by DynamoDB Streams
resource "aws_lambda_event_source_mapping" "stream_to_anomaly" {
  event_source_arn  = aws_dynamodb_table.vitals.stream_arn
  function_name     = aws_lambda_function.anomaly_detector.function_name
  starting_position = "LATEST"
  batch_size        = 10
  bisect_batch_on_function_error = true
}

# Lambda functions
resource "aws_lambda_function" "vitals_validator" {
  function_name = "${var.project}-vitals-validator-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 30
  filename      = "../backend/vitals_validator.zip"

  environment {
    variables = {
      VITALS_TABLE = aws_dynamodb_table.vitals.name
    }
  }
}

resource "aws_lambda_function" "anomaly_detector" {
  function_name = "${var.project}-anomaly-detector-${var.environment}"
  role          = aws_iam_role.lambda_exec.arn
  handler       = "handler.lambda_handler"
  runtime       = "python3.11"
  timeout       = 60
  memory_size   = 512
  filename      = "../backend/anomaly_detector.zip"

  environment {
    variables = {
      SNS_TOPIC_ARN = aws_sns_topic.health_alerts.arn
      MODEL_BUCKET  = var.model_bucket
      MODEL_KEY     = "models/isolation_forest.pkl"
    }
  }
}

# IAM Role for Lambda
resource "aws_iam_role" "lambda_exec" {
  name = "${var.project}-lambda-exec-${var.environment}"
  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action    = "sts:AssumeRole"
      Effect    = "Allow"
      Principal = { Service = "lambda.amazonaws.com" }
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_basic" {
  role       = aws_iam_role.lambda_exec.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

output "vitals_table_name" {
  value = aws_dynamodb_table.vitals.name
}
