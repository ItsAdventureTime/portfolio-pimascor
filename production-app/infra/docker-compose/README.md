# PIMASCOR demo on OrbStack

Use [`compose.yaml`](compose.yaml) as the sole demo Compose file. It runs one
API image serving the built PWA and one PostgreSQL service. The API joins the
private `pimascor-network` and existing external `cloudflared-network`. The
database joins only the private network. Nothing is published on a host port.

The public target is `https://pimascor.delegateops.business`. This is a manual
deployment guide. The steps have not passed on OrbStack yet. Confirm each
check below before sharing the URL.

The demo starts without R2 or Resend. Its synthetic email sink logs OTPs, but
document upload and protected viewing return unavailable until private R2
storage is configured and verified. The demo is incomplete until then. Do not
enable public bucket access.

## 1. Prepare private runtime files

Keep the runtime under `production-app/infra/docker-compose/.runtime/pimascor-demo/`
in this checkout. Git and Docker builds ignore the entire `.runtime` folder.
On this host, the prepared workspace contains a copied `compose.yaml`, a fresh
64-character hexadecimal PostgreSQL password, and a matching database URL.
Both secret files are mode `0600` inside a mode `0700` directory. The copy is
local to this machine and must never be committed or sent to GitHub.

On a new checkout, create the same files without printing the password:

```sh
( set -eu
runtime=production-app/infra/docker-compose/.runtime/pimascor-demo
umask 077
test ! -e "$runtime/secrets/postgres_password.txt"
test ! -e "$runtime/secrets/database_url.txt"
mkdir -p "$runtime/secrets" "$runtime/images"
chmod 700 production-app/infra/docker-compose/.runtime "$runtime" "$runtime/secrets" "$runtime/images"
cp production-app/infra/docker-compose/compose.yaml "$runtime/compose.yaml"
password=$(openssl rand -hex 32)
printf '%s' "$password" > "$runtime/secrets/postgres_password.txt"
printf 'postgresql+psycopg://pimascor:%s@db:5432/pimascor' "$password" > "$runtime/secrets/database_url.txt"
chmod 600 "$runtime/secrets/"*.txt
unset password
)
```

Do not rerun the generation block over an existing deployment. Check whether
the OrbStack volume `pimascor-demo_demo_postgres_data` already exists. If it
does, the new password may not match that database. Keep its existing
credentials and data until the owner chooses a migration or restore plan.

Compose grants each service only the secret it needs. Docker Compose does not
remap UID, GID, or mode for file-backed secrets. Restrictive host permissions
do not prove container readability. The API must read its secret as UID
10001, and PostgreSQL must read its password as UID 70. Prove both in the
runtime checks below. Never use mode 644. If either probe fails, stop and
resolve ownership while keeping files unreadable to other Mac users.

## 2. Build and transfer the image

Run from the repository root. Build and export through the project Docker
Sandbox. Do not build on the Mac host or in OrbStack:

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
gzip -c production-app/var/pimascor-demo-api.tar > production-app/infra/docker-compose/.runtime/pimascor-demo/images/pimascor-demo-api.tar.gz
gzip -t production-app/infra/docker-compose/.runtime/pimascor-demo/images/pimascor-demo-api.tar.gz
rm production-app/var/pimascor-demo-api.tar
```

Record the command results, image architecture, image ID/digest, and source
commit in `docs/agent/HANDOFF.notes.md`. Load the archive into OrbStack:

```sh
docker --context orbstack image load --input production-app/infra/docker-compose/.runtime/pimascor-demo/images/pimascor-demo-api.tar.gz
docker --context orbstack image inspect pimascor-demo-api:latest --format '{{.RepoTags}} {{.Architecture}} {{.Id}}'
```

Compose pins PostgreSQL to `18.6-alpine3.23` and its multi-platform manifest
digest. PostgreSQL 18 stores data below `/var/lib/postgresql/18/docker`. Its
volume must target `/var/lib/postgresql`. Never point an initialized volume at
a different major version.

## 3. Check runtime prerequisites before startup

Confirm the existing Tunnel container and network. Do not create another
`cloudflared` service:

```sh
docker --context orbstack ps --filter name=cloudflared
docker --context orbstack network inspect cloudflared-network
docker --context orbstack volume inspect pimascor-demo_demo_postgres_data
cd production-app/infra/docker-compose/.runtime/pimascor-demo
docker --context orbstack compose config --quiet
```

The volume check returns an error on a fresh installation. That is expected.
If it returns a volume, confirm which credentials belong to it before running
`compose up`.

Check secret access without displaying file contents:

```sh
docker --context orbstack compose run --rm --no-deps --entrypoint /bin/sh api \
  -c 'test "$(id -u)" = 10001 && test -r /run/secrets/database_url'
docker --context orbstack compose run --rm --no-deps --user 70:70 --entrypoint /bin/sh db \
  -c 'test "$(id -u)" = 70 && test -r /run/secrets/postgres_password'
```

If the external network, required secret files, or either permission probe is
missing or fails, stop here. Do not start services or relax secret modes.

## 4. Initialize and start

Start PostgreSQL and wait for its health check:

```sh
docker --context orbstack compose up --wait --wait-timeout 120 --pull missing db
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
docker --context orbstack compose exec api python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health', timeout=5)"
```

If API health fails, inspect its logs and stop before changing the public
route.

## 5. Connect the public hostname and check the demo

In Cloudflare, open the existing Tunnel and add a published application route
for `pimascor.delegateops.business` pointing to
`http://pimascor-demo-api:8000`. If the Tunnel is managed by a local config,
add that hostname before its 404 fallback instead. The hostname also needs a
DNS record pointing to the existing Tunnel. Do not change routes for other
apps. [Cloudflare's route guide](https://developers.cloudflare.com/tunnel/concepts/routing/)
shows both management paths.

From a different network, check the public route:

```sh
curl -fsS https://pimascor.delegateops.business/api/v1/health
curl -I https://pimascor.delegateops.business/
```

Open the URL in a browser. Enter as demo Admin, switch through Requester, GM,
DCS, and Mich, and confirm a forbidden action is rejected. Check the browser
console, the quotation preview, the response cache headers, and that business
data survives an API restart. Record the tested commit, image ID, time, and
results in `docs/agent/HANDOFF.notes.md`. An independent reviewer still needs
to check the public route, viewports, and protected document behavior.

## 6. Add private R2 storage for complete document behavior

The prepared `.runtime/pimascor-demo/secrets/` folder contains four unmounted
R2 placeholders for the account endpoint, private bucket name, access key ID,
and secret access key. Replace them only with values from Cloudflare. Create a
private R2 bucket and a user S3 token with Object Read & Write access scoped
to that bucket. Cloudflare supplies the endpoint and both keys. Do not enable
public bucket access. [Cloudflare's S3 setup](https://developers.cloudflare.com/r2/get-started/s3/)
has the current dashboard steps.

The current `compose.yaml` mounts only the database secrets. Its application
storage settings still use B2 names and require the demo bucket `bridge-ph`
with prefix `pimascor/demo`. The next implementation agent must wire the R2
values into Compose and verify upload, protected range view, delete, and reset
cleanup before this demo can claim working document flows. Do not mount
placeholder values or announce complete document support.

## 7. Stop and rollback

Stop containers while keeping the database volume:

```sh
docker --context orbstack compose down
```

Never use `down --volumes` for routine rollback. Keep the previous API archive.
Load it and recreate only the API after checking migration compatibility.

## References

- [Docker Compose service secrets](https://docs.docker.com/reference/compose-file/services/#secrets)
- [Official PostgreSQL image](https://hub.docker.com/_/postgres)
- [Docker image save](https://docs.docker.com/reference/cli/docker/image/save/)
- [Cloudflare R2 S3 setup](https://developers.cloudflare.com/r2/get-started/s3/)
- [Cloudflare Tunnel published application routing](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/)
