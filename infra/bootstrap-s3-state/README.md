# Terraform state bucket (bootstrap)

Отдельный S3 bucket для **remote state** остальных стеков (`server`, `tzone/infra/terraform`, …).

Этот каталог **сам** хранит state **локально** (`terraform.tfstate` в `.gitignore`) — классический bootstrap: сначала создаём bucket, потом подключаем `backend "s3"` в других проектах.

## Credentials

```bash
export AWS_ACCESS_KEY_ID='...'
export AWS_SECRET_ACCESS_KEY='...'
export AWS_DEFAULT_REGION='us-east-1'
```

## Переменные

| Переменная | Обязательна | По умолчанию | Описание |
|------------|-------------|--------------|----------|
| `bucket_name` | нет | `null` → `server-terraform-state-<AWS_ACCOUNT_ID>` | Имя S3 bucket для state |

**Account ID передавать не нужно** — Terraform берёт его из credentials (`data.aws_caller_identity`) и подставляет в имя bucket.

### Дефолтный apply (без переменных)

Создаёт bucket `server-terraform-state-<AWS_ACCOUNT_ID>`:

```bash
cd infra/bootstrap-s3-state
terraform init
terraform plan
terraform apply
```

Подтвердите план (`yes`) — bucket появится в AWS в регионе `us-east-1`.

### Свой bucket name (опционально)

Если нужно другое имя:

```bash
terraform plan  -var='bucket_name=my-terraform-state'
terraform apply -var='bucket_name=my-terraform-state'
```

Или через файл (не коммитить, если имя уникально для окружения):

```bash
# terraform.tfvars
bucket_name = "my-terraform-state"
```

```bash
terraform apply
```

После `apply` имя bucket — в output:

```bash
terraform output state_bucket_name
```

## Backend в других стеках

После `apply` возьмите имя из output `state_bucket_name` или `backend_config_example`:

```hcl
terraform {
  backend "s3" {
    bucket = "server-terraform-state-123456789012"
    key    = "route53/terraform.tfstate"
    region = "us-east-1"
  }
}
```

Опционально позже: DynamoDB table для state locking.
