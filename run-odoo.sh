#!/usr/bin/env bash
# Run odoo (image tag ODOO_IMAGE, default odoo:19.0) with this repository's addons mounted, on the dev Postgres of the connector stack.
#   ODOO_IMAGE=odoo:20.0 ./run-odoo.sh -d mydb -i partner_warn_block --test-tags /partner_warn_block --stop-after-init
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
ENVFILE="${ENVFILE:-$HERE/../odoo-shopify-connector/.env}"
set -a; . "$ENVFILE"; set +a
exec docker run --rm -i --network odoo-shopify-connector_default \
  -e HOST=db -e USER="$POSTGRES_USER" -e PASSWORD="$POSTGRES_PASSWORD" \
  -v "$HERE/addons:/mnt/extra-addons" ${EXTRA_MOUNTS:-} "${ODOO_IMAGE:-odoo:19.0}" odoo \
  --addons-path=/mnt/extra-addons,/usr/lib/python3/dist-packages/odoo/addons "$@"
