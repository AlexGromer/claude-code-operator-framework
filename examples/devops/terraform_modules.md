# Few-Shot Example: Terraform Module Design

**Domain:** devops
**Skill Level:** Intermediate
**Pattern:** Design → Structure → Implement → Test

---

## User Query

We're deploying the same infrastructure pattern across multiple environments (dev, staging, prod) and regions. Currently we have copy-pasted Terraform code with subtle differences. How do I refactor this into reusable modules with proper structure?

Current mess:
```
terraform/
├── dev/
│   ├── main.tf      (VPC, ECS, RDS - all in one file)
│   └── variables.tf
├── staging/
│   ├── main.tf      (copy of dev with changes)
│   └── variables.tf
└── prod/
    ├── main.tf      (copy with more changes)
    └── variables.tf
```

---

## Exemplary Response

### 1. Terraform Module Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     TERRAFORM MODULE HIERARCHY                              │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                              │
│  LEVEL 3: Root Modules (Environments)                                       │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  environments/                                                       │    │
│  │  ├── dev/         ─┐                                                │    │
│  │  ├── staging/      ├── Compose infrastructure modules               │    │
│  │  └── prod/        ─┘     with environment-specific vars             │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  LEVEL 2: Infrastructure Modules (Compositions)                             │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  modules/                                                            │    │
│  │  ├── app-stack/    ─── Combines: VPC + ECS + RDS + Monitoring       │    │
│  │  ├── data-stack/   ─── Combines: VPC + RDS + ElastiCache            │    │
│  │  └── web-stack/    ─── Combines: VPC + ALB + ECS + CloudFront       │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                              │                                               │
│                              ▼                                               │
│  LEVEL 1: Resource Modules (Building Blocks)                                │
│  ┌─────────────────────────────────────────────────────────────────────┐    │
│  │  modules/                                                            │    │
│  │  ├── vpc/          ─── VPC, Subnets, NAT, IGW                       │    │
│  │  ├── ecs-cluster/  ─── ECS Cluster, ASG, Launch Template            │    │
│  │  ├── ecs-service/  ─── ECS Service, Task Definition, IAM            │    │
│  │  ├── rds/          ─── RDS Instance, Subnet Group, Security Group   │    │
│  │  └── alb/          ─── ALB, Listeners, Target Groups                │    │
│  └─────────────────────────────────────────────────────────────────────┘    │
│                                                                              │
└─────────────────────────────────────────────────────────────────────────────┘
```

### 2. Recommended Directory Structure

```
terraform/
├── modules/                          # Reusable modules
│   ├── vpc/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── versions.tf
│   │   └── README.md
│   ├── ecs-cluster/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── versions.tf
│   ├── ecs-service/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── versions.tf
│   ├── rds/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   └── versions.tf
│   └── app-stack/                    # Composition module
│       ├── main.tf
│       ├── variables.tf
│       ├── outputs.tf
│       └── versions.tf
│
├── environments/                      # Environment configurations
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── backend.tf
│   │   ├── terraform.tfvars
│   │   └── versions.tf
│   ├── staging/
│   │   └── ... (same structure)
│   └── prod/
│       └── ... (same structure)
│
├── shared/                            # Shared data sources
│   ├── data.tf                       # AMI lookups, account ID
│   └── outputs.tf
│
└── terragrunt.hcl                    # Optional: DRY configuration
```

### 3. Module Implementation

#### 3.1 VPC Module (Level 1)

```hcl
# modules/vpc/variables.tf
variable "name" {
  description = "Name prefix for VPC resources"
  type        = string
}

variable "cidr_block" {
  description = "CIDR block for VPC"
  type        = string
  default     = "10.0.0.0/16"
}

variable "availability_zones" {
  description = "List of availability zones"
  type        = list(string)
}

variable "private_subnet_cidrs" {
  description = "CIDR blocks for private subnets"
  type        = list(string)
  default     = []
}

variable "public_subnet_cidrs" {
  description = "CIDR blocks for public subnets"
  type        = list(string)
  default     = []
}

variable "enable_nat_gateway" {
  description = "Enable NAT Gateway for private subnets"
  type        = bool
  default     = true
}

variable "single_nat_gateway" {
  description = "Use single NAT Gateway (cost savings for non-prod)"
  type        = bool
  default     = false
}

variable "tags" {
  description = "Tags to apply to all resources"
  type        = map(string)
  default     = {}
}
```

```hcl
# modules/vpc/main.tf
locals {
  # Calculate subnet CIDRs if not provided
  private_subnet_cidrs = length(var.private_subnet_cidrs) > 0 ? var.private_subnet_cidrs : [
    for i, az in var.availability_zones : cidrsubnet(var.cidr_block, 4, i)
  ]
  public_subnet_cidrs = length(var.public_subnet_cidrs) > 0 ? var.public_subnet_cidrs : [
    for i, az in var.availability_zones : cidrsubnet(var.cidr_block, 4, i + length(var.availability_zones))
  ]

  nat_gateway_count = var.enable_nat_gateway ? (var.single_nat_gateway ? 1 : length(var.availability_zones)) : 0
}

resource "aws_vpc" "this" {
  cidr_block           = var.cidr_block
  enable_dns_hostnames = true
  enable_dns_support   = true

  tags = merge(var.tags, {
    Name = "${var.name}-vpc"
  })
}

resource "aws_internet_gateway" "this" {
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.name}-igw"
  })
}

resource "aws_subnet" "private" {
  count = length(local.private_subnet_cidrs)

  vpc_id            = aws_vpc.this.id
  cidr_block        = local.private_subnet_cidrs[count.index]
  availability_zone = var.availability_zones[count.index]

  tags = merge(var.tags, {
    Name = "${var.name}-private-${var.availability_zones[count.index]}"
    Tier = "private"
  })
}

resource "aws_subnet" "public" {
  count = length(local.public_subnet_cidrs)

  vpc_id                  = aws_vpc.this.id
  cidr_block              = local.public_subnet_cidrs[count.index]
  availability_zone       = var.availability_zones[count.index]
  map_public_ip_on_launch = true

  tags = merge(var.tags, {
    Name = "${var.name}-public-${var.availability_zones[count.index]}"
    Tier = "public"
  })
}

resource "aws_eip" "nat" {
  count  = local.nat_gateway_count
  domain = "vpc"

  tags = merge(var.tags, {
    Name = "${var.name}-nat-eip-${count.index + 1}"
  })

  depends_on = [aws_internet_gateway.this]
}

resource "aws_nat_gateway" "this" {
  count = local.nat_gateway_count

  allocation_id = aws_eip.nat[count.index].id
  subnet_id     = aws_subnet.public[count.index].id

  tags = merge(var.tags, {
    Name = "${var.name}-nat-${count.index + 1}"
  })
}

resource "aws_route_table" "private" {
  count  = length(local.private_subnet_cidrs)
  vpc_id = aws_vpc.this.id

  tags = merge(var.tags, {
    Name = "${var.name}-private-rt-${count.index + 1}"
  })
}

resource "aws_route" "private_nat" {
  count = var.enable_nat_gateway ? length(local.private_subnet_cidrs) : 0

  route_table_id         = aws_route_table.private[count.index].id
  destination_cidr_block = "0.0.0.0/0"
  nat_gateway_id         = aws_nat_gateway.this[var.single_nat_gateway ? 0 : count.index].id
}

resource "aws_route_table_association" "private" {
  count = length(local.private_subnet_cidrs)

  subnet_id      = aws_subnet.private[count.index].id
  route_table_id = aws_route_table.private[count.index].id
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.this.id

  route {
    cidr_block = "0.0.0.0/0"
    gateway_id = aws_internet_gateway.this.id
  }

  tags = merge(var.tags, {
    Name = "${var.name}-public-rt"
  })
}

resource "aws_route_table_association" "public" {
  count = length(local.public_subnet_cidrs)

  subnet_id      = aws_subnet.public[count.index].id
  route_table_id = aws_route_table.public.id
}
```

```hcl
# modules/vpc/outputs.tf
output "vpc_id" {
  description = "VPC ID"
  value       = aws_vpc.this.id
}

output "vpc_cidr_block" {
  description = "VPC CIDR block"
  value       = aws_vpc.this.cidr_block
}

output "private_subnet_ids" {
  description = "List of private subnet IDs"
  value       = aws_subnet.private[*].id
}

output "public_subnet_ids" {
  description = "List of public subnet IDs"
  value       = aws_subnet.public[*].id
}

output "nat_gateway_ids" {
  description = "List of NAT Gateway IDs"
  value       = aws_nat_gateway.this[*].id
}

output "private_route_table_ids" {
  description = "List of private route table IDs"
  value       = aws_route_table.private[*].id
}
```

#### 3.2 ECS Service Module (Level 1)

```hcl
# modules/ecs-service/variables.tf
variable "name" {
  description = "Service name"
  type        = string
}

variable "cluster_id" {
  description = "ECS Cluster ID"
  type        = string
}

variable "vpc_id" {
  description = "VPC ID"
  type        = string
}

variable "subnet_ids" {
  description = "Subnet IDs for service"
  type        = list(string)
}

variable "container_image" {
  description = "Container image"
  type        = string
}

variable "container_port" {
  description = "Container port"
  type        = number
  default     = 8080
}

variable "cpu" {
  description = "Task CPU units"
  type        = number
  default     = 256
}

variable "memory" {
  description = "Task memory (MB)"
  type        = number
  default     = 512
}

variable "desired_count" {
  description = "Desired task count"
  type        = number
  default     = 2
}

variable "min_capacity" {
  description = "Minimum task count for autoscaling"
  type        = number
  default     = 1
}

variable "max_capacity" {
  description = "Maximum task count for autoscaling"
  type        = number
  default     = 10
}

variable "target_group_arn" {
  description = "ALB target group ARN (optional)"
  type        = string
  default     = null
}

variable "environment_variables" {
  description = "Environment variables for container"
  type        = map(string)
  default     = {}
}

variable "secrets" {
  description = "Secrets from SSM/Secrets Manager"
  type = list(object({
    name      = string
    valueFrom = string
  }))
  default = []
}

variable "health_check_path" {
  description = "Health check path"
  type        = string
  default     = "/health"
}

variable "tags" {
  description = "Tags"
  type        = map(string)
  default     = {}
}
```

```hcl
# modules/ecs-service/main.tf
locals {
  container_name = var.name
}

# IAM Role for Task Execution
resource "aws_iam_role" "execution" {
  name = "${var.name}-execution-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

resource "aws_iam_role_policy_attachment" "execution" {
  role       = aws_iam_role.execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# IAM Role for Task
resource "aws_iam_role" "task" {
  name = "${var.name}-task-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Action = "sts:AssumeRole"
      Effect = "Allow"
      Principal = {
        Service = "ecs-tasks.amazonaws.com"
      }
    }]
  })

  tags = var.tags
}

# CloudWatch Log Group
resource "aws_cloudwatch_log_group" "this" {
  name              = "/ecs/${var.name}"
  retention_in_days = 30

  tags = var.tags
}

# Security Group
resource "aws_security_group" "this" {
  name        = "${var.name}-sg"
  description = "Security group for ${var.name} ECS service"
  vpc_id      = var.vpc_id

  ingress {
    from_port   = var.container_port
    to_port     = var.container_port
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/8"]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.name}-sg"
  })
}

# Task Definition
resource "aws_ecs_task_definition" "this" {
  family                   = var.name
  network_mode             = "awsvpc"
  requires_compatibilities = ["FARGATE"]
  cpu                      = var.cpu
  memory                   = var.memory
  execution_role_arn       = aws_iam_role.execution.arn
  task_role_arn            = aws_iam_role.task.arn

  container_definitions = jsonencode([{
    name      = local.container_name
    image     = var.container_image
    essential = true

    portMappings = [{
      containerPort = var.container_port
      hostPort      = var.container_port
      protocol      = "tcp"
    }]

    environment = [
      for k, v in var.environment_variables : {
        name  = k
        value = v
      }
    ]

    secrets = var.secrets

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.this.name
        "awslogs-region"        = data.aws_region.current.name
        "awslogs-stream-prefix" = "ecs"
      }
    }

    healthCheck = {
      command     = ["CMD-SHELL", "curl -f http://localhost:${var.container_port}${var.health_check_path} || exit 1"]
      interval    = 30
      timeout     = 5
      retries     = 3
      startPeriod = 60
    }
  }])

  tags = var.tags
}

# ECS Service
resource "aws_ecs_service" "this" {
  name            = var.name
  cluster         = var.cluster_id
  task_definition = aws_ecs_task_definition.this.arn
  desired_count   = var.desired_count
  launch_type     = "FARGATE"

  network_configuration {
    subnets          = var.subnet_ids
    security_groups  = [aws_security_group.this.id]
    assign_public_ip = false
  }

  dynamic "load_balancer" {
    for_each = var.target_group_arn != null ? [1] : []
    content {
      target_group_arn = var.target_group_arn
      container_name   = local.container_name
      container_port   = var.container_port
    }
  }

  deployment_circuit_breaker {
    enable   = true
    rollback = true
  }

  tags = var.tags

  lifecycle {
    ignore_changes = [desired_count]  # Managed by autoscaling
  }
}

# Auto Scaling
resource "aws_appautoscaling_target" "this" {
  max_capacity       = var.max_capacity
  min_capacity       = var.min_capacity
  resource_id        = "service/${split("/", var.cluster_id)[1]}/${aws_ecs_service.this.name}"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "${var.name}-cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.this.resource_id
  scalable_dimension = aws_appautoscaling_target.this.scalable_dimension
  service_namespace  = aws_appautoscaling_target.this.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value       = 70.0
    scale_in_cooldown  = 300
    scale_out_cooldown = 60
  }
}

data "aws_region" "current" {}
```

#### 3.3 App Stack Module (Level 2 - Composition)

```hcl
# modules/app-stack/variables.tf
variable "name" {
  description = "Application name"
  type        = string
}

variable "environment" {
  description = "Environment (dev, staging, prod)"
  type        = string
}

variable "region" {
  description = "AWS region"
  type        = string
}

variable "availability_zones" {
  description = "Availability zones"
  type        = list(string)
}

variable "vpc_cidr" {
  description = "VPC CIDR block"
  type        = string
  default     = "10.0.0.0/16"
}

# ECS Configuration
variable "services" {
  description = "Map of ECS services to deploy"
  type = map(object({
    image         = string
    cpu           = optional(number, 256)
    memory        = optional(number, 512)
    desired_count = optional(number, 2)
    port          = optional(number, 8080)
    environment   = optional(map(string), {})
  }))
}

# RDS Configuration
variable "db_instance_class" {
  description = "RDS instance class"
  type        = string
  default     = "db.t3.micro"
}

variable "db_allocated_storage" {
  description = "RDS allocated storage (GB)"
  type        = number
  default     = 20
}

variable "tags" {
  description = "Tags"
  type        = map(string)
  default     = {}
}
```

```hcl
# modules/app-stack/main.tf
locals {
  common_tags = merge(var.tags, {
    Environment = var.environment
    Application = var.name
    ManagedBy   = "terraform"
  })

  # Determine if production
  is_prod = var.environment == "prod"
}

# VPC
module "vpc" {
  source = "../vpc"

  name               = "${var.name}-${var.environment}"
  cidr_block         = var.vpc_cidr
  availability_zones = var.availability_zones

  # Cost optimization: single NAT for non-prod
  enable_nat_gateway = true
  single_nat_gateway = !local.is_prod

  tags = local.common_tags
}

# ECS Cluster
resource "aws_ecs_cluster" "this" {
  name = "${var.name}-${var.environment}"

  setting {
    name  = "containerInsights"
    value = local.is_prod ? "enabled" : "disabled"
  }

  tags = local.common_tags
}

# ECS Services
module "ecs_services" {
  source   = "../ecs-service"
  for_each = var.services

  name            = "${var.name}-${each.key}"
  cluster_id      = aws_ecs_cluster.this.id
  vpc_id          = module.vpc.vpc_id
  subnet_ids      = module.vpc.private_subnet_ids
  container_image = each.value.image
  container_port  = each.value.port
  cpu             = each.value.cpu
  memory          = each.value.memory
  desired_count   = each.value.desired_count

  environment_variables = merge(each.value.environment, {
    ENVIRONMENT = var.environment
    DB_HOST     = module.rds.endpoint
  })

  # Scale more aggressively in prod
  min_capacity = local.is_prod ? 2 : 1
  max_capacity = local.is_prod ? 20 : 5

  tags = local.common_tags
}

# RDS
module "rds" {
  source = "../rds"

  name                = "${var.name}-${var.environment}"
  vpc_id              = module.vpc.vpc_id
  subnet_ids          = module.vpc.private_subnet_ids
  instance_class      = var.db_instance_class
  allocated_storage   = var.db_allocated_storage

  # Production settings
  multi_az               = local.is_prod
  deletion_protection    = local.is_prod
  backup_retention_period = local.is_prod ? 30 : 7

  tags = local.common_tags
}
```

### 4. Environment Configuration

```hcl
# environments/prod/main.tf
terraform {
  required_version = ">= 1.5.0"

  backend "s3" {
    bucket         = "mycompany-terraform-state"
    key            = "prod/app-stack/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "terraform-locks"
  }
}

provider "aws" {
  region = var.region

  default_tags {
    tags = {
      Environment = "prod"
      ManagedBy   = "terraform"
    }
  }
}

module "app_stack" {
  source = "../../modules/app-stack"

  name        = "myapp"
  environment = "prod"
  region      = var.region

  availability_zones = ["us-east-1a", "us-east-1b", "us-east-1c"]
  vpc_cidr           = "10.0.0.0/16"

  services = {
    api = {
      image         = "mycompany/api:${var.api_version}"
      cpu           = 512
      memory        = 1024
      desired_count = 3
      port          = 8080
      environment = {
        LOG_LEVEL = "info"
      }
    }
    worker = {
      image         = "mycompany/worker:${var.worker_version}"
      cpu           = 256
      memory        = 512
      desired_count = 2
      port          = 8081
    }
  }

  db_instance_class    = "db.r5.large"
  db_allocated_storage = 100

  tags = {
    CostCenter = "engineering"
    Owner      = "platform-team"
  }
}
```

```hcl
# environments/prod/variables.tf
variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "api_version" {
  description = "API container version"
  type        = string
}

variable "worker_version" {
  description = "Worker container version"
  type        = string
}
```

```hcl
# environments/prod/terraform.tfvars
region         = "us-east-1"
api_version    = "v1.2.3"
worker_version = "v1.2.3"
```

### 5. Testing Modules

```hcl
# modules/vpc/tests/vpc_test.go
package test

import (
    "testing"
    "github.com/gruntwork-io/terratest/modules/terraform"
    "github.com/stretchr/testify/assert"
)

func TestVpcModule(t *testing.T) {
    t.Parallel()

    terraformOptions := terraform.WithDefaultRetryableErrors(t, &terraform.Options{
        TerraformDir: "../",
        Vars: map[string]interface{}{
            "name":               "test-vpc",
            "cidr_block":         "10.0.0.0/16",
            "availability_zones": []string{"us-east-1a", "us-east-1b"},
            "enable_nat_gateway": true,
            "single_nat_gateway": true,
        },
    })

    defer terraform.Destroy(t, terraformOptions)
    terraform.InitAndApply(t, terraformOptions)

    vpcId := terraform.Output(t, terraformOptions, "vpc_id")
    assert.NotEmpty(t, vpcId)

    privateSubnetIds := terraform.OutputList(t, terraformOptions, "private_subnet_ids")
    assert.Len(t, privateSubnetIds, 2)

    publicSubnetIds := terraform.OutputList(t, terraformOptions, "public_subnet_ids")
    assert.Len(t, publicSubnetIds, 2)
}
```

### 6. Best Practices Checklist

| Practice | Rationale |
|----------|-----------|
| Single responsibility per module | Easier testing and reuse |
| Explicit variable types with validation | Catch errors early |
| Output everything that might be needed | Avoid module changes for outputs |
| Use `for_each` over `count` | Stable resource addresses |
| Default to secure settings | Prod-safe defaults |
| Document with README.md | Self-documenting modules |
| Version your modules | Reproducible deployments |
| Test with Terratest | Catch regressions |

### 7. Version Pinning

```hcl
# modules/vpc/versions.tf
terraform {
  required_version = ">= 1.5.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}
```

---

## Why This Is A Good Example

- Clear module hierarchy (Level 1, 2, 3)
- Complete working module implementations
- Environment-specific configuration pattern
- Testing strategy with Terratest
- Production vs non-prod considerations

---

## Key Patterns

1. **Module Composition** - Small modules composed into larger stacks
2. **Environment Parity** - Same modules, different variables
3. **Cost Optimization** - Production vs development settings
4. **Explicit Outputs** - Modules expose what's needed

---

**Tags:** #devops #terraform #iac #modules #aws #infrastructure
**Version:** 1.0.0
**Last Updated:** 2026-01-23
