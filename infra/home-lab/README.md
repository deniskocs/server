# Home lab — AWS (Terraform)

Домашняя инфраструктура в AWS: DNS `chilik.net` и связанные ресурсы.  
Отдельный Terraform-стек и **отдельный state** (`home-lab/terraform.tfstate` в S3).

Не путать с:

- `infra/terraform` — bootstrap S3 bucket для remote state;
- `infra/k8s/` — Kubernetes / Argo CD;
- `tzone/infra/terraform` — продукт TZone (`t-zone.org`, SES, media и т.д.).

## Credentials

```bash
export AWS_ACCESS_KEY_ID='...'
export AWS_SECRET_ACCESS_KEY='...'
export AWS_DEFAULT_REGION='us-east-1'
```

## Apply

```bash
cd infra/home-lab
terraform init
terraform plan
terraform apply
```

## Миграция state из tzone

Ресурсы `chilik.net` раньше жили в `tzone/infra/terraform` (ключ `tzone/terraform.tfstate`).  
Перед первым `apply` здесь — перенести state, иначе Terraform попытается создать дубликаты.

### 1. Удалить из state tzone (AWS не трогается)

```bash
cd tzone/infra/terraform
terraform init

terraform state rm aws_route53_zone.chilik_net
terraform state rm aws_route53_record.chilik_net_api
terraform state rm aws_route53_record.chilik_net_denis
terraform state rm aws_route53_record.chilik_net_home
terraform state rm aws_route53_record.chilik_net_learn_english
terraform state rm aws_route53_record.chilik_net_apex
```

### 2. Import в home-lab

Hosted zone ID `chilik.net`: `Z00069343EECSSFO5X065`.

```bash
cd server/infra/home-lab
terraform init

terraform import aws_route53_zone.chilik_net Z00069343EECSSFO5X065

terraform import aws_route53_record.chilik_net_apex Z00069343EECSSFO5X065_chilik.net_A
terraform import aws_route53_record.chilik_net_api Z00069343EECSSFO5X065_api.chilik.net_CNAME
terraform import aws_route53_record.chilik_net_denis Z00069343EECSSFO5X065_denis.chilik.net_CNAME
terraform import aws_route53_record.chilik_net_home Z00069343EECSSFO5X065_home.chilik.net_CNAME
terraform import aws_route53_record.chilik_net_learn_english Z00069343EECSSFO5X065_learn-english.chilik.net_CNAME

terraform plan   # ожидается: No changes
```

### 3. Проверка tzone

```bash
cd tzone/infra/terraform
terraform plan   # destroy по chilik.net быть не должно
```
