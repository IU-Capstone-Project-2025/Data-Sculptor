#!/bin/sh

# Enable PKI
vault secrets enable -path=pki pki

# Configure CA
vault secrets tune -max-lease-ttl=$CA_LIFETIME pki

vault write -field=certificate pki/root/generate/internal \
  common_name="internal.service" \
  ttl=87600h > /vault/file/ca.crt

vault write pki/config/urls \
  issuing_certificates="$VAULT_ADDR/v1/pki/ca" \
  crl_distribution_points="$VAULT_ADDR/v1/pki/crl"

# Create a role
vault write pki/roles/microservice \
  allowed_domains="internal.service" \
  allow_subdomains=true \
  max_ttl="$CRT_LIFETIME"
