# Зона chilik.net — DNS для домашних сервисов (home, api, learn-english и т.д.).
# Тот же домашний IP, отдельные vhost'ы на nginx.
resource "aws_route53_zone" "chilik_net" {
  comment = "Personal / home services"
  name    = "chilik.net"
}
