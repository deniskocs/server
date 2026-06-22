output "route53_zone_chilik_net_id" {
  description = "Hosted zone ID для chilik.net."
  value       = aws_route53_zone.chilik_net.id
}

output "route53_zone_chilik_net_name_servers" {
  description = "NS-записи зоны (если делегирование настраивается вручную у регистратора)."
  value       = aws_route53_zone.chilik_net.name_servers
}
