#!/usr/bin/env bash
# Generate RSA-2048 key pair for JWT RS256 signing.
# Run from the backend/ directory.
set -euo pipefail

SECRETS_DIR="./secrets"
mkdir -p "$SECRETS_DIR"

openssl genrsa -out "$SECRETS_DIR/private.pem" 2048
openssl rsa -in "$SECRETS_DIR/private.pem" -pubout -out "$SECRETS_DIR/public.pem"

echo "Keys generated:"
echo "  Private key: $SECRETS_DIR/private.pem"
echo "  Public key:  $SECRETS_DIR/public.pem"
echo ""
echo "Add to .gitignore: secrets/"
