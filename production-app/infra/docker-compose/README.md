# PIMASCOR demo on OrbStack

Use [`compose.yaml`](compose.yaml) as the sole demo Compose file. It runs one
API image serving the built PWA and one PostgreSQL service. The API joins the
private `pimascor-network` and existing external `cloudflared-network`; the
database joins only the private network. Nothing is published on a host port.

The public target is `https://pimascor.delegateops.business`. This guide
describes the intended manual deployment. Runtime, Tunnel, URL, secret access,
and document storage checks remain pending until the owner supplies the
external runtime configuration. Do not call the demo fully functional until
those checks pass.

The demo starts without R2 or Resend. Its synthetic email sink logs OTPs, but
document upload and protected viewing return unavailable until private R2
storage is configured and verified; without that, the demo is incomplete. Do
not enable public bucket access.

## Prepare private runtime files

Keep all secrets outside the checkout. Create the runtime folder and copy the
two required files:

```sh
mkdir -p ~/docker/portfolio/pimascor/images ~/docker/portfolio/pimascor/secrets
chmod 700 ~/docker/portfolio/pimascor/secrets
cp production-app/infra/docker-compose/compose.yaml ~/docker/portfolio/pimascor/compose.yaml
cp production-app/infra/docker-compose/secrets/postgres_password.txt.example ~/docker/portfolio/pimascor/secrets/postgres_password.txt
cp production-app/infra/docker-compose/secrets/database_url.txt.example ~/docker/portfolio/pimascor/secrets/database_url.txt
chmod 600 ~/docker/portfolio/pimascor/secrets/*.txt
```

Replace the placeholders with a URL-safe random password, using the same
password in both files. The URL format is:

```text
postgresql+psycopg://pimascor:YOUR_URL_SAFE_PASSWORD@db:5432/pimascor
```

Compose grants each service only the secret it needs. Docker Compose does not
remap UID, GID, or mode for file-backed secrets; restrictive host permissions
do not prove container readability. The API must read its secret as UID
10001, and PostgreSQL must read its password as UID 70. Prove both in the
runtime checks below. Never use mode 644. If either probe fails, stop and
resolve ownership while keeping files unreadable to other Mac users.

## Build and transfer the image

Run from the repository root. Build and export through the project Docker
Sandbox; do not build on the Mac host or in OrbStack:

```sh
jk-sbx-project implement 'docker build --platform linux/arm64 \
  --file production-app/infra/docker-compose/api.Containerfile.alpine \
  --tag pimascor-demo-api:latest \
  --build-arg VITE_BASE_PATH=/ \
  --build-arg VITE_API_URL=/api/v1 \
  --build-arg VITE_CSRF_COOKIE_NAME=bridge_ph_pimascor_demo_csrf \
  --build-arg VITE_DEPLOYMENT_TIER=demo \
  production-app'
jk-sbx-project implement 'docker image inspect pimascor-demo-api:latest --format "{{.RepoTags}} {{.Architecture}} {{.Id}}"'
jk-sbx-project implement 'mkdir -p production-app/var && docker image save --output production-app/var/pimascor-demo-api.tar pimascor-demo-api:latest'
gzip -c production-app/var/pimascor-demo-api.tar > ~/docker/portfolio/pimascor/images/pimascor-demo-api.tar.gz
gzip -t ~/docker/portfolio/pimascor/images/pimascor-demo-api.tar.gz
rm production-app/var/pimascor-demo-api.tar
```

Record the command results, image architecture, image ID/digest, and source
commit in `docs/agent/HANDOFF.notes.md`. Load the archive into OrbStack:

```sh
docker --context orbstack image load --input ~/docker/portfolio/pimascor/images/pimascor-demo-api.tar.gz
docker --context orbstack image inspect pimascor-demo-api:latest --format '{{.RepoTags}} {{.Architecture}} {{.Id}}'
```

Compose pins PostgreSQL to `18.6-alpine3.23` and its multi-platform manifest
digest. PostgreSQL 18 stores data below `/var/lib/postgresql/18/docker`; its
volume must target `/var/lib/postgresql`. Never point an initialized volume at
a different major version.

## Check runtime prerequisites before startup

Confirm the existing Tunnel container and network; do not create another
`cloudflared` service:

```sh
docker --context orbstack ps --filter name=cloudflared
docker --context orbstack network inspect cloudflared-network
cd ~/docker/portfolio/pimascor
docker --context orbstack compose config --quiet
```

Check secret access without displaying file contents:

```sh
docker --context orbstack compose run --rm --no-deps --entrypoint /bin/sh api \
  -c 'test "$(id -u)" = 10001 && test -r /run/secrets/database_url'
docker --context orbstack compose run --rm --no-deps --user 70:70 --entrypoint /bin/sh db \
  -c 'test "$(id -u)" = 70 && test -r /run/secrets/postgres_password'
```

If the external network, required secret files, or either permission probe is
missing or fails, stop here. Do not start services or relax secret modes.

## Initialize and start

Start PostgreSQL and wait for its health check:

```sh
docker --context orbstack compose up -d --pull never db
docker --context orbstack compose ps db
```

Run migration, account initialization, and synthetic reset explicitly as
separate one-off jobs. API restarts must never reset data:

```sh
docker --context orbstack compose run --rm api alembic upgrade head
docker --context orbstack compose run --rm api python -m pimascor_api.demo_initializer
docker --context orbstack compose run --rm api python -m pimascor_api.demo_reset
```

Then start the image already loaded in OrbStack:

```sh
docker --context orbstack compose up -d --no-build --pull never api
docker --context orbstack compose ps
docker --context orbstack compose logs --tail=80 api
```

Verify API health from the existing `cloudflared-network`. Configure the
existing Tunnel's hostname route to `http://pimascor-demo-api:8000`, ahead of
its 404 catch-all. Do not modify other hosted routes. Check the public health
endpoint, PWA shell/assets, login, API cache headers, and session cookie before
announcing the URL.

For complete document behavior, activate R2, create a private bucket and a
bucket-scoped Object Read & Write token, then configure the existing S3 client
with the account endpoint and region `auto`. The present Compose file does not
mount R2 credentials. After adding the demo-specific secret configuration,
test multipart upload, protected range view, delete, and reset cleanup. Keep
the bucket private. See [Cloudflare R2 S3 setup](https://developers.cloudflare.com/r2/get-started/s3/).

## Stop and rollback

Stop containers while keeping the database volume:

```sh
docker --context orbstack compose down
```

Never use `down --volumes` for routine rollback. Keep the previous API archive;
load it and recreate only the API after checking migration compatibility.

## References

- [Docker Compose service secrets](https://docs.docker.com/reference/compose-file/services/#secrets)
- [Official PostgreSQL image](https://hub.docker.com/_/postgres)
- [Docker image save](https://docs.docker.com/reference/cli/docker/image/save/)
- [Cloudflare R2 S3 setup](https://developers.cloudflare.com/r2/get-started/s3/)
- [Cloudflare Tunnel published application routing](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/)
