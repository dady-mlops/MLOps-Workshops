resource "aws_iam_role" "apprunner_ecr_role" {
  name = "apprunner-ecr-role-ai-write-agent"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = {
          Service = "build.apprunner.amazonaws.com"
        }
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "apprunner_ecr_policy_attachment" {
  role       = aws_iam_role.apprunner_ecr_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSAppRunnerServicePolicyForECRAccess"
}

# Create role for SSM Parameter Store access
resource "aws_iam_role" "apprunner_service_role" {
  name = "apprunner-service-role-ai-write-agent"
  assume_role_policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [
      {
        Action    = "sts:AssumeRole"
        Effect    = "Allow"
        Principal = {
          Service = "tasks.apprunner.amazonaws.com"
        }
      }
    ]
  })
}

# Create policy for SSM Parameter Store access
resource "aws_iam_policy" "ssm_parameter_access" {
  name        = "apprunner-ssm-parameter-access"
  description = "Allow App Runner to access SSM parameters"
  
  policy = jsonencode({
    Version   = "2012-10-17"
    Statement = [
      {
        Action   = [
          "ssm:GetParameters",
          "ssm:GetParameter",
          "ssm:GetParametersByPath"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:ssm:${var.aws_region}:*:parameter/ai-agents-app/*",
          "arn:aws:ssm:${var.aws_region}:*:parameter/ai-agents-app"
        ]
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "apprunner_ssm_policy_attachment" {
  role       = aws_iam_role.apprunner_service_role.name
  policy_arn = aws_iam_policy.ssm_parameter_access.arn
}