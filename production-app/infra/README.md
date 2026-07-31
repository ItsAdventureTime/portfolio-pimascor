# PIMASCOR demo deployment

Before following this runbook, read `../docs/FACTUAL-BASIS.md`. The commands
describe the reviewed repository configuration; they do not prove the current
VPS state. Verify host-specific facts with command output before modifying them.

Short manual runbook for the rootless Fedora CoreOS deployment at:

```text
https://delegateops.business/pimascor/demo/
```

Application source, runtime data, and the Caddy-served PWA live under
`~/bridge-ph/pimascor-demo`; globally unique Quadlets live
in `~/.config/containers/systemd/bridge-ph/pimascor-demo`.

## 1. What runs

```text
Internet -> Caddy -> static PWA
                  -> API -> PostgreSQL
                         -> Resend
                         -> private Backblaze B2 documents

03:00 Asia/Manila -> reset job -> delete demo documents + replace demo data
```

- Only Caddy publishes host ports.
- API and PostgreSQL use private rootless Podman networks.
- The host needs no Python, Node.js, npm, PostgreSQL, Restic, AWS CLI, or B2 CLI.
- Non-secret settings are in `.container` files. Credentials are Podman secrets.
- The demo has no database backup, Restic job, retention job, or backup timer.

## 2. Required paths

Run as the rootless service owner:

```bash
install -d -m 700 ~/bridge-ph/pimascor-demo/source ~/bridge-ph/pimascor-demo/data/postgres/18/docker ~/bridge-ph/pimascor-demo/data/uploads-tmp ~/.config/containers/systemd/bridge-ph/pimascor-demo ~/.config/systemd/user
```

`install -d` creates directories and applies the requested mode; it does not install a software package or overwrite an existing database.

Confirm rootless Podman and persistent user services:

```bash
podman info --format '{{.Host.Security.Rootless}}'
loginctl show-user "$USER" -p Linger
```

Expected: `true` and `Linger=yes`.

## 3. Synchronize reviewed source

From the computer containing `production-app`, first preview and then copy. Replace `VPS_HOST`:

```bash
rsync -avhn --delete --exclude '.DS_Store' --exclude 'node_modules/' --exclude '.venv/' --exclude 'dist/' /Users/jk.deguzman/Downloads/bridge-ph_Dashboard/production-app/ jk@VPS_HOST:/var/home/jk/bridge-ph/pimascor-demo/source/
```

```bash
rsync -avh --delete --exclude '.DS_Store' --exclude 'node_modules/' --exclude '.venv/' --exclude 'dist/' /Users/jk.deguzman/Downloads/bridge-ph_Dashboard/production-app/ jk@VPS_HOST:/var/home/jk/bridge-ph/pimascor-demo/source/
```

`--delete` affects only the destination `source/` mirror, never live PostgreSQL data, installed Quadlets, Podman secrets, or Caddy.

## 4. Required Podman secrets

The demo requires these names:

```text
bridge_ph_pimascor_demo_postgres_password
bridge_ph_pimascor_demo_database_url
bridge_ph_pimascor_demo_resend_api_key
bridge_ph_pimascor_demo_b2_key_id
bridge_ph_pimascor_demo_b2_application_key
```

Check names without exposing values:

```bash
podman secret ls --format '{{.Name}}' | sort
```

Create a missing secret without placing its value in a file or command history:

```bash
read -rsp 'Secret value: ' PIMASCOR_SECRET; printf '%s' "$PIMASCOR_SECRET" | podman secret create SECRET_NAME -; unset PIMASCOR_SECRET; printf '\n'
```

Replace `SECRET_NAME` with the exact name above.

Backblaze mapping:

| Backblaze value | Application setting |
|---|---|
| Bucket name `bridge-ph` | Non-secret `B2_BUCKET` |
| Endpoint `s3.us-west-001.backblazeb2.com` | Non-secret `B2_ENDPOINT_URL` |
| Region `us-west-001` | Non-secret `B2_REGION` |
| `keyID` | Podman secret `bridge_ph_pimascor_demo_b2_key_id` |
| `applicationKey` | Podman secret `bridge_ph_pimascor_demo_b2_application_key` |

The Backblaze bucket ID is not used by the S3-compatible API and does not need to be mounted into the application. The application key needs `listFiles`, `readFiles`, `writeFiles`, and `deleteFiles` for the restricted `pimascor/demo/` prefix. Use separate production credentials later.

Incident email uses the existing Resend secret. The non-secret recipients are
explicit in the API Quadlet:

```text
alyssa.d@bridge-ph.com       Bridge PH Admin, plain operational context
jk@delegateops.business     Developer, safe technical and Codex context
```

Production uses the same settings in its isolated API Quadlet and its own Resend
secret. No incident report contains form values, documents, credentials, secret
values, or full bank information.

The same Quadlet sets `PUBLIC_APP_URL` to the exact HTTPS application path and
`EMAIL_CODE_TTL_MINUTES=5`. Login emails contain a single-use code and one-click link;
the Resend key remains a Podman secret.

## 5. Build and install

For an already installed demo, use the guarded updater:

```bash
cd ~/bridge-ph/pimascor-demo/source
infra/scripts/update-demo.sh
```

It verifies secrets and migrations, installs the reviewed Quadlets, checks PostgreSQL, preserves local rollback material, builds the API and PWA, applies migrations, reloads the demo baseline, restarts Caddy, and probes HTTPS.

For a first deployment, build the API:

```bash
cd ~/bridge-ph/pimascor-demo/source
podman build --pull=missing --tag localhost/bridge-ph-pimascor-demo-api:demo apps/api
```

Export the PWA:

```bash
cd ~/bridge-ph/pimascor-demo/source
mkdir -p ~/bridge-ph/pimascor-demo/web-dist.new
podman build --pull=missing --file apps/web/Containerfile --output type=local,dest="$HOME/bridge-ph/pimascor-demo/web-dist.new" apps/web
install -d -m 700 ~/bridge-ph/pimascor-demo/web-dist
find ~/bridge-ph/pimascor-demo/web-dist -mindepth 1 -maxdepth 1 -exec rm -rf -- {} +
cp -a ~/bridge-ph/pimascor-demo/web-dist.new/. ~/bridge-ph/pimascor-demo/web-dist/
rm -rf -- ~/bridge-ph/pimascor-demo/web-dist.new
```

Install definitions:

```bash
install -m 600 infra/quadlet/demo/* ~/.config/containers/systemd/bridge-ph/pimascor-demo/
install -m 600 infra/systemd/bridge-ph-pimascor-demo-reset.timer ~/.config/systemd/user/
systemctl --user daemon-reload
```

Validate generated services:

```bash
systemd-analyze --user --generators=true verify bridge-ph-pimascor-demo-db.service bridge-ph-pimascor-demo-api.service bridge-ph-pimascor-demo-reset.service bridge-ph-pimascor-demo-reset.timer
```

## 6. Caddy connection

Caddy must share `bridge-ph-pimascor-demo-proxy` with the API and bind
`~/bridge-ph/pimascor-demo/web-dist` read-only at
`/srv/bridge-ph-pimascor-demo`.

The relevant site handlers are:

```Caddyfile
delegateops.business {
    handle /pimascor/demo {
        redir * /pimascor/demo/ 308
    }

    handle /pimascor/demo/api/* {
        uri strip_prefix /pimascor/demo
        header {
            >Cache-Control "private, no-store"
            >CDN-Cache-Control "no-store"
            >X-Robots-Tag "noindex, nofollow, noarchive"
        }
        reverse_proxy bridge-ph-pimascor-demo-api:8000
    }

    handle_path /pimascor/demo/* {
        header {
            >Content-Security-Policy "default-src 'none'; script-src 'self'; script-src-attr 'none'; style-src 'self'; style-src-attr 'unsafe-inline'; img-src 'self' data: blob:; font-src 'self' data:; connect-src 'self'; media-src 'self' blob:; object-src 'none'; frame-src 'self' blob:; frame-ancestors 'none'; worker-src 'self'; manifest-src 'self'; base-uri 'none'; form-action 'self'; upgrade-insecure-requests"
            >X-Robots-Tag "noindex, nofollow, noarchive"
        }
        root * /srv/bridge-ph-pimascor-demo

        route {
            try_files {path} /index.html

            @revalidate path / /index.html /sw.js /manifest.webmanifest /pimascor-app-icon.jpg /pimascor-logo.jpg /pimascor-icon-192.png /pimascor-icon-512.png /pimascor-icon-maskable-192.png /pimascor-icon-maskable-512.png /apple-touch-icon.png
            header @revalidate >Cache-Control "public, max-age=0, must-revalidate"

            @fingerprinted_assets path /assets/*
            header @fingerprinted_assets >Cache-Control "public, max-age=31536000, immutable"

            file_server
        }
    }
}
```

Keep the previously reviewed common security headers. The route-specific CSP intentionally allows `blob:` in `frame-src` because the protected PDF viewer creates an in-memory blob URL. `frame-ancestors 'none'` still prevents other sites from framing PIMASCOR. Validate and reload inside the existing Caddy container using its established commands.

The `delegateops.business` site block must retain `import common_security`.
One-click email verification needs no extra Caddy callback: the OTP is carried in
the URI fragment, which is not sent in the HTTP request, and the normal
`/pimascor/demo/` SPA handler completes verification. Keep the full PWA
revalidation matcher from `Caddyfile.reviewed`, including all PNG icons.

## 7. Start in dependency order

```bash
systemctl --user start bridge-ph-pimascor-demo-data-network.service bridge-ph-pimascor-demo-egress-network.service bridge-ph-pimascor-demo-proxy-network.service
systemctl --user start bridge-ph-pimascor-demo-db.service
systemctl --user start bridge-ph-pimascor-demo-api.service
systemctl --user enable --now bridge-ph-pimascor-demo-reset.timer
systemctl --user restart caddy.service
```

Check status:

```bash
systemctl --user status bridge-ph-pimascor-demo-db.service bridge-ph-pimascor-demo-api.service bridge-ph-pimascor-demo-reset.timer --no-pager -l
```

## 8. Accounts and baseline

Create one real account per role. Each email must be unique and reachable:

```bash
podman exec -it bridge-ph-pimascor-demo-api python -m pimascor_api.seed --username requester --email 'REQUESTER_EMAIL' --display-name 'Demo Requester' --role REQUESTER
podman exec -it bridge-ph-pimascor-demo-api python -m pimascor_api.seed --username gm --email 'GM_EMAIL' --display-name 'Demo GM' --role GM
podman exec -it bridge-ph-pimascor-demo-api python -m pimascor_api.seed --username dcs --email 'DCS_EMAIL' --display-name 'Demo DCS' --role DCS
podman exec -it bridge-ph-pimascor-demo-api python -m pimascor_api.seed --username mich --email 'MICH_EMAIL' --display-name 'Demo Mich' --role MICH
podman exec -it bridge-ph-pimascor-demo-api python -m pimascor_api.seed --username admin --email 'ADMIN_EMAIL' --display-name 'PIMASCOR Administrator' --role ADMIN
```

Load the synthetic baseline now:

```bash
systemctl --user start bridge-ph-pimascor-demo-reset.service
```

The reset deletes objects below `pimascor/demo/documents/`, replaces mutable business/configuration data, preserves users/passwords, and revokes sessions. It does not restore a backup.

Confirm 03:00 Philippine time:

```bash
systemctl --user list-timers bridge-ph-pimascor-demo-reset.timer --all
```

## 9. Backblaze object layout

Bucket: `bridge-ph`.

```text
pimascor/
├── demo/
│   └── documents/
│       └── liquidations/{liquidation-id}/{yyyy}/{mm}/{evidence-id}.{ext}
├── documents/
│   └── liquidations/{liquidation-id}/{yyyy}/{mm}/{evidence-id}.{ext}
└── backups/
    └── restic/
```

- Demo uses `pimascor/demo/`.
- Production documents use `pimascor/documents/`.
- Production encrypted backups use `pimascor/backups/restic/`.
- Object keys use lowercase prefixes and opaque IDs. The original filename stays in PostgreSQL for display and audit, not in the object key.
- Each PDF/JPEG/PNG may be up to 100 MB. Validation reads bounded chunks, and `%h/bridge-ph/pimascor-demo/data/uploads-tmp` is the private disk-backed spool used while Boto3 performs a managed multipart transfer.
- S3 storage is flat. These are prefixes, not real folders. Do not pre-create them; the first object upload creates the visible hierarchy automatically.
- The production PostgreSQL dump is staged locally and captured inside Restic. Do not create a duplicate `pimascor/db` backup tree.

## 10. Verification

```bash
curl --fail --show-error https://delegateops.business/pimascor/demo/api/v1/health
curl --fail --show-error --output /dev/null https://delegateops.business/pimascor/demo/
podman ps --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}'
```

Expected:

- HTTPS and API health succeed.
- Only Caddy shows published host ports.
- Document Library loads for Admin, GM, DCS, and Mich.
- A Liquidation PDF/JPEG/PNG upload appears in the library and opens through
  the authenticated, no-store, view-only stream. No download control is shown.
- A file larger than 100 MB is rejected with HTTP 413; a file at or below the limit does not exhaust the API container's memory or `/tmp` space.
- Requester cannot browse other users' documents.
- A Requester creates a quotation, GM approves it, and client acceptance with a
  signed PDF/JPEG/PNG enables a linked Budget Request.
- Mich reviews the submitted Budget Request before it enters the GM queue.
- DCS records a payment only after selecting a configured funding source and
  attaching PDF/JPEG/PNG proof; Requesters cannot open the DCS payment workspace.
- Mich cannot close a Liquidation until original physical documents are
  confirmed and the matching variance proof is present.
- Admin opens Administration → Activity Monitor, sees non-Admin staff events by default, and can enable **Include Admin activity**. Requester, GM, DCS, and Mich receive HTTP 403 from `/api/v1/admin/activity`.
- Admin can add/deactivate an approved funding source; DCS can select it for payment but cannot maintain the source list. Use fictional data in the demo.
- Trigger a harmless API error while signed in. Confirm **Dismiss** closes without
  creating a client report, audit event, or email.
- Trigger it again and select **Report for investigation**. Confirm the dialog closes
  after delivery, an `INC-` reference appears under **App problems**, and Resend
  delivered separate operational Admin and technical/Codex Developer messages.
- Firefox, Chrome/Edge, and Safari load the PWA; 320 px layouts reflow; reduced-motion disables non-essential animation.

## 11. Updates and rollback cleanup

After synchronizing the source, update, migrate, reload the demo baseline, restart
Caddy, and run the public health checks:

```bash
cd ~/bridge-ph/pimascor-demo/source && infra/scripts/update-demo.sh
```

List or remove accepted local rollback material interactively:

```bash
cd ~/bridge-ph/pimascor-demo/source && infra/scripts/cleanup-demo-rollback.sh
```

Delete only stored demo incident reports and their incident audit events:

```bash
podman exec bridge-ph-pimascor-demo-api python -m pimascor_api.incident_admin purge --confirm DELETE-DEMO-INCIDENTS
```

The incident cleanup cannot run in production and does not remove journald logs or
emails already accepted by Resend.

Run registry auto-update manually during a maintenance window:

```bash
podman auto-update --dry-run
podman auto-update --rollback
```

The locally built API uses the `local` policy; the PostgreSQL registry image is eligible for registry policy. Never run a database major-version update without its PostgreSQL upgrade procedure.

## 12. Normal operations

Logs:

```bash
journalctl --user -u bridge-ph-pimascor-demo-api.service -u bridge-ph-pimascor-demo-db.service -n 150 --no-pager -o cat
```

Reset logs:

```bash
journalctl --user -u bridge-ph-pimascor-demo-reset.service -n 100 --no-pager -o cat
```

Restart order:

```bash
systemctl --user restart bridge-ph-pimascor-demo-db.service
systemctl --user restart bridge-ph-pimascor-demo-api.service
systemctl --user restart caddy.service
```

Account administration:

```bash
podman exec -it bridge-ph-pimascor-demo-api python -m pimascor_api.account_admin list
podman exec -it bridge-ph-pimascor-demo-api python -m pimascor_api.account_admin set-password USERNAME
podman exec -it bridge-ph-pimascor-demo-api python -m pimascor_api.account_admin disable USERNAME
podman exec -it bridge-ph-pimascor-demo-api python -m pimascor_api.account_admin enable USERNAME
```

## 13. Fast troubleshooting

Generated service missing:

```bash
systemctl --user daemon-reload
systemd-analyze --user --generators=true verify bridge-ph-pimascor-demo-api.service
```

API or database failure:

```bash
systemctl --user status bridge-ph-pimascor-demo-db.service bridge-ph-pimascor-demo-api.service --no-pager -l
journalctl --user -u bridge-ph-pimascor-demo-db.service -u bridge-ph-pimascor-demo-api.service -b -n 200 --no-pager -o cat
```

PostgreSQL permission error: verify the exact mount is present in the installed database Quadlet:

```text
%h/bridge-ph/pimascor-demo/data/postgres/18/docker:/var/lib/postgresql/18/docker:U,Z
```

Backblaze `403`: verify endpoint, region, bucket, secret names, and that the application key permits `listFiles`, `readFiles`, `writeFiles`, and `deleteFiles` below `pimascor/demo/`.

## 14. Production boundary

Do not promote the demo by renaming it. Production receives separate Quadlets, networks, database, cookies, users, credentials, object prefix, retention, and acceptance evidence.

Production backup templates remain under `infra/quadlet/production/`. They use:

```text
s3:https://s3.us-west-001.backblazeb2.com/bridge-ph/pimascor/backups/restic
```

Enable them only after management approves recovery objectives and an isolated restore rehearsal succeeds.

## Official references

- Podman Quadlet: https://docs.podman.io/en/latest/markdown/podman-systemd.unit.5.html
- Podman secrets: https://docs.podman.io/en/latest/markdown/podman-secret.1.html
- Podman auto-update: https://docs.podman.io/en/latest/markdown/podman-auto-update.1.html
- Fedora CoreOS: https://docs.fedoraproject.org/en-US/fedora-coreos/
- Caddy directives: https://caddyserver.com/docs/caddyfile/directives
- PostgreSQL container: https://hub.docker.com/_/postgres
- Backblaze S3-compatible API: https://www.backblaze.com/docs/en/cloud-storage-call-the-s3-compatible-api
- S3 object keys and prefixes: https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-keys.html
- WCAG 2.2: https://www.w3.org/TR/WCAG22/
# Production deployment

The isolated production path is documented in `docs/PRODUCTION-VPS-DEPLOYMENT.md`.
Use `infra/scripts/deploy-production-vps.sh` from the Mac, then run
`infra/scripts/provision-production-secrets.sh` followed by
`infra/scripts/update-production.sh` under `/var/home/jk/bridge-ph/pimascor/source`
on the VPS. Production Quadlets belong only in
`~/.config/containers/systemd/bridge-ph/pimascor`; do not reuse demo units or
the demo database/object prefix. The secrets helper also creates the protected
account manifest consumed by the production account-bootstrap Quadlet; it never
stores initial user passwords.
