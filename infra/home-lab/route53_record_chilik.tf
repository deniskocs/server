# DNS-записи зоны chilik.net (личный / домашний сайт).
# Apex A → 69.248.197.36 (домашний публичный IP).

# --- Сервисы ---

resource "aws_route53_record" "chilik_net_api" {
  name    = "api.chilik.net"
  records = ["chilik.net"]
  ttl     = "300"
  type    = "CNAME"
  zone_id = aws_route53_zone.chilik_net.zone_id
}

resource "aws_route53_record" "chilik_net_denis" {
  name    = "denis.chilik.net"
  records = ["chilik.net"]
  ttl     = "300"
  type    = "CNAME"
  zone_id = aws_route53_zone.chilik_net.zone_id
}

resource "aws_route53_record" "chilik_net_home" {
  name    = "home.chilik.net"
  records = ["chilik.net"]
  ttl     = "300"
  type    = "CNAME"
  zone_id = aws_route53_zone.chilik_net.zone_id
}

resource "aws_route53_record" "chilik_net_learn_english" {
  name    = "learn-english.chilik.net"
  records = ["chilik.net"]
  ttl     = "300"
  type    = "CNAME"
  zone_id = aws_route53_zone.chilik_net.zone_id
}

resource "aws_route53_record" "chilik_net_argo" {
  name    = "argo.chilik.net"
  records = ["chilik.net"]
  ttl     = "300"
  type    = "CNAME"
  zone_id = aws_route53_zone.chilik_net.zone_id
}

resource "aws_route53_record" "chilik_net_keycloak" {
  name    = "keycloak.chilik.net"
  records = ["chilik.net"]
  ttl     = "300"
  type    = "CNAME"
  zone_id = aws_route53_zone.chilik_net.zone_id
}

resource "aws_route53_record" "chilik_net_llms" {
  name    = "llms.chilik.net"
  records = ["chilik.net"]
  ttl     = "300"
  type    = "CNAME"
  zone_id = aws_route53_zone.chilik_net.zone_id
}

resource "aws_route53_record" "chilik_net_api_llms" {
  name    = "api.llms.chilik.net"
  records = ["chilik.net"]
  ttl     = "300"
  type    = "CNAME"
  zone_id = aws_route53_zone.chilik_net.zone_id
}

# --- Apex ---

resource "aws_route53_record" "chilik_net_apex" {
  name    = "chilik.net"
  records = ["69.248.197.36"]
  ttl     = "300"
  type    = "A"
  zone_id = aws_route53_zone.chilik_net.zone_id
}
