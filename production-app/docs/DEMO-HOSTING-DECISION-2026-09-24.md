# Demo hosting decision and operator guide — 2026-09-24

## Decision

Use the existing Mac mini M1, OrbStack, Docker Compose, and existing Cloudflare
Tunnel for the public synthetic demo at `https://pimascor.delegateops.business`.
Finish the in-progress Compose implementation in this checkout. Keep
PostgreSQL in a named OrbStack volume and run the current FastAPI API and built
React PWA in the same API image. Use Cloudflare R2 through its S3-compatible
endpoint for protected demo documents if full upload/view behavior is required.
Do not add a Worker solely to host this demo.

This is a hosting decision, not deployment evidence. The implementation is
published on the public portfolio repository's `main` branch. Independent
review found that `pimascor.delegateops.business` did not resolve in DNS. Mac
runtime state, Tunnel routing, R2 activation, and protected document behavior
remain unverified. Prove them before claiming a working demo.

### Why this path

- `apps/api/` is FastAPI, SQLAlchemy, Alembic, PostgreSQL (`psycopg`), and
  `boto3`; `apps/web/` is a Vite/React PWA. Existing production migrations use
  PostgreSQL-specific enums. The current application already expects a normal
  process and relational database.
- `infra/docker-compose/compose.yaml` and its runbook already model an API
  image, PostgreSQL, private network, external `cloudflared-network`, secrets,
  and no host port. These are work-in-progress files and require validation.
- [Workers Builds](https://developers.cloudflare.com/workers/ci-cd/builds/)
  can build and deploy on Git push after a Worker project and Git integration
  are configured. A repository push alone does not turn this FastAPI image into
  a Worker. Cloudflare's build would replace the *local build step*, not the
  need to compile the Vite assets or deploy the Worker.
- [Python Workers support FastAPI](https://developers.cloudflare.com/workers/languages/python/packages/fastapi/),
  but its Pyodide/PyEmscripten package environment and this app's PostgreSQL,
  SQLAlchemy, `psycopg`, `boto3`, background maintenance, and 100 MB upload
  path need a separate compatibility spike. This is not a drop-in deployment.
- [Cloudflare Containers](https://developers.cloudflare.com/containers/guides/deploy/)
  can build a Dockerfile in Workers Builds, but [require Workers Paid](https://developers.cloudflare.com/containers/platform/pricing/) and
  [all container disk is ephemeral](https://developers.cloudflare.com/containers/concepts/architecture/).
  Keeping this app's database inside a Cloudflare Container would lose data.

## Cloudflare service fit

| Service | Can bind to a Worker? | Fit for this app today |
| --- | --- | --- |
| [R2](https://developers.cloudflare.com/r2/api/workers/workers-api-usage/) | Yes, `r2_buckets` binding. Also offers an [S3 API](https://developers.cloudflare.com/r2/api/) that the existing `boto3` client can call from the Mac. | Useful for protected demo files. Use S3 from FastAPI on the selected homelab path; a Worker binding would require Worker code. |
| [D1](https://developers.cloudflare.com/d1/get-started/) | Yes, `d1_databases` binding. | SQLite-based replacement for PostgreSQL, not a connection to it. Existing migrations, types, and data access need a port and new acceptance tests. |
| [Hyperdrive](https://developers.cloudflare.com/hyperdrive/) | Yes, `hyperdrive` binding for an existing PostgreSQL/MySQL database. | Adds no value to the selected Mac API. For a Worker, private Mac PostgreSQL needs [Workers VPC and Tunnel](https://developers.cloudflare.com/hyperdrive/configuration/connect-to-private-database-vpc/) with TLS. [Documented known PostgreSQL versions stop at 17.x](https://developers.cloudflare.com/hyperdrive/reference/supported-databases-and-features/); this repo targets 18, so compatibility is unverified. |
| [KV](https://developers.cloudflare.com/kv/get-started/) | Yes, `kv_namespaces` binding. | Suitable for read-heavy configuration. [Eventual consistency](https://developers.cloudflare.com/kv/concepts/how-kv-works/) makes it unsuitable as the source of truth for this app's sessions, approvals, and payments. |
| [Containers](https://developers.cloudflare.com/containers/get-started/) | Yes, via a Worker and Durable Object class. Container code can call Worker bindings through [outbound handlers](https://developers.cloudflare.com/containers/configuration/workers-connections/). | Could host FastAPI with an external durable PostgreSQL service and external object storage. More moving parts and cost than OrbStack for this portfolio demo. |

Binding IDs are resource identifiers, not credentials. Runtime Worker bindings
are separate from Workers Builds build variables. Put only non-secret Vite
`VITE_*` values into the build settings. Put Worker runtime credentials in
[Worker Secrets](https://developers.cloudflare.com/workers/configuration/secrets/),
and Compose credentials in the external file secrets described below. Do not
put credentials in `compose.yaml`, `wrangler.jsonc`, a GitHub repository, or
the public Vite bundle.

## Executor slice: finish the OrbStack demo

1. Review the current unstaged and staged changes before editing. Use
   `infra/docker-compose/compose.yaml` as the one canonical Compose file;
   remove or mark older drafts as superseded. Preserve all unrelated work.
2. Keep non-secret runtime settings inside `compose.yaml`. Mount each secret
   file only into the service that needs it. Keep the runtime copy under the
   ignored `infra/docker-compose/.runtime/pimascor-demo/` folder, with
   owner-only directory access and restrictive file permissions. No `.env` file.
   **Probe readability as API UID 10001.** Docker Compose file secrets are
   bind mounts, and [Compose ignores `uid`, `gid`, and `mode` overrides for
   file-backed secrets](https://docs.docker.com/reference/compose-file/services/#secrets).
   `chmod 600` on the Mac alone does not prove the non-root container can read
   them. Resolve the mismatch without making secret files world-readable and
   test the final setup in OrbStack.
3. Pin the PostgreSQL major/version and image digest chosen for the demo; do
   not use a floating `postgres:alpine` tag. Check the volume target against
   that image's current official data-directory guidance before first start.
   Never repoint an initialized database volume to a different major image.
4. Keep database migration, synthetic account initialization, and demo reset
   explicit. Restarting the API must not reset business data. Preserve
   `DEPLOYMENT_TIER=demo`, secure session cookies, CSRF checks, demo-only entry,
   same-origin `/api/v1`, disabled full archive, and synthetic email behavior.
5. Complete the PWA static serving and SPA fallback in FastAPI, with `/api/v1`
   taking precedence. Build with `VITE_BASE_PATH=/`,
   `VITE_API_URL=/api/v1`, and `VITE_DEPLOYMENT_TIER=demo`. Keep document
   responses private; do not cache API/session responses at Cloudflare.
6. For complete document behavior, create one private R2 bucket and configure
   existing `boto3` with R2 S3 endpoint, region `auto`, bucket, and object
   prefix. The current `config.py` checks demo storage values against the
   legacy B2 bucket name `bridge-ph` and prefix `pimascor/demo`; either create
   that R2 bucket name or make the smallest demo-only validation adjustment.
   Preserve the production B2 contract. Test multipart upload, range read,
   protected view, delete, and reset cleanup before claiming R2 support.
7. Add a release check for the public URL, plus a rollback that retains the
   prior image archive and the PostgreSQL volume. Never run `compose down -v`
   as a routine rollback. The reviewer owns browser and rendered QA.

## Manual deployment: selected homelab path

These steps follow the finished implementation. The executor must update
`infra/docker-compose/README.md` with the exact proven commands; its current
commands are a draft, not verified operational evidence.

1. In the Cloudflare dashboard, check that `delegateops.business` is an
   active zone and inspect the existing Tunnel's management mode and current
   `cloudflared` container. Do not create a second Tunnel. Confirm the
   external Docker network named `cloudflared-network` exists and the
   `cloudflared` container is attached to it. Confirm `pimascor` has no
   conflicting DNS record or route.
2. If enabling R2, in **Storage & databases > R2 > Overview**, activate R2,
   create a private demo bucket, and create a user API token scoped to **Object
   Read & Write** on only that bucket. Copy its Access Key ID, Secret Access
   Key, and `https://<ACCOUNT_ID>.r2.cloudflarestorage.com` endpoint to the Mac's
   private secret files/settings. Do not enable public bucket access. See the
   [official R2 S3 setup](https://developers.cloudflare.com/r2/get-started/s3/).
3. In the project Docker Sandbox, run the final Containerfile build and API/web
   checks. Export the built image archive, then load it into OrbStack using
   `docker --context orbstack image load --input <archive>`. OrbStack and the
   Docker Sandbox are separate image stores. Record the image's commit and
   architecture before loading it.
4. Copy only the reviewed `compose.yaml` to the ignored
   `infra/docker-compose/.runtime/pimascor-demo/` folder in the checkout.
   Keep its generated PostgreSQL password and matching SQLAlchemy database
   URL in separate files; use `chmod 700` on the secrets directory and
   `chmod 600` on each file. Do not replace credentials for an existing
   database volume. Add R2 key files only if R2 is enabled. Never display
   secret contents in logs or test output. Prove the API and database
   containers can read their own files as their non-root users.
5. From the runtime folder, run `docker --context orbstack compose config
   --quiet` and the non-root secret-read probe from the runbook. Start only
   `db`; wait for its health check. Run Alembic migration, demo account
   initialization, and synthetic data reset as three explicit one-off jobs.
   Then start `api` with `--no-build --pull never` and verify its health check
   plus a local request from a container on `cloudflared-network`.
6. Publish `pimascor.delegateops.business` through the existing Tunnel as
   `http://pimascor-demo-api:8000`. For a dashboard-managed Tunnel, use
   **Networking > Tunnels > existing tunnel > Add published application**;
   for a locally managed Tunnel, add its `ingress` rule ahead of the 404
   catch-all and route the hostname to the Tunnel. Use the existing management
   mode only. A published route connects the public hostname through an
   outbound-only Tunnel; see [Cloudflare's published-app guide](https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/routing-to-tunnel/).
7. From outside the Mac, check HTTPS, `/api/v1/health`, the PWA shell and
   fingerprinted assets, demo Admin entry, Requester/GM/DCS/Mich workspace
   access, a permitted and a forbidden action, quotation preview, document
   upload/protected view if R2 is enabled, and a deliberate restart without
   data reset. Check API response `Cache-Control` and login cookies. Record
   response codes, image digest/commit, time, and screenshots in the review
   notes; no passwords or OTPs.
8. For rollback, keep the previous image archive; load it and recreate only
   `api`. Check migration compatibility first. Retain the database volume and
   secrets. If the Tunnel route fails, remove only this hostname's route;
   leave Linkwarden, Vaultwarden, and Docuseal routes alone.

The Mac must remain powered on, OrbStack and `cloudflared` must remain running,
and the internet connection must work for the public URL to remain available.
This is an operational property of the selected homelab, not a code defect.

## Conditional Cloudflare-native route, if hosting needs change

Do not provision these resources for the selected demo. If the Mac can no
longer host it, first implement and validate a small Worker/Container slice.

1. Add a Worker entrypoint, `wrangler.jsonc`, and package/build commands under
   a dedicated monorepo root. Keep `name` in Wrangler equal to the dashboard
   Worker name. Configure Vite static assets and a real API route. For
   FastAPI-in-Worker, run a package compatibility spike first; for Containers,
   use a Worker and Durable Object class and keep PostgreSQL external.
2. In **Workers & Pages > Create application > Import a repository**, connect
   `ItsAdventureTime/portfolio-pimascor`, set the correct root directory and
   `main` branch, a Vite build command, and `npx wrangler deploy` as the deploy
   command. Workers Builds will compile in Cloudflare on each push. A Container
   Dockerfile can also build there. Preview/version upload does not update
   Container images. See [Builds configuration](https://developers.cloudflare.com/workers/ci-cd/builds/configuration/)
   and [Container deployment](https://developers.cloudflare.com/containers/guides/deploy/).
3. If needed, create R2 bucket, D1 database, and KV namespace in the dashboard
   or with `wrangler r2 bucket create`, `wrangler d1 create`, and
   `wrangler kv namespace create`. Record only the generated resource IDs in
   Wrangler `r2_buckets`, `d1_databases`, and `kv_namespaces`. A D1 migration
   is mandatory before pointing app traffic at it. KV must not replace
   transactional data or sessions.
   The matching Wrangler entries have this shape; use only resources the new
   Worker code actually calls:

   ```jsonc
   {
     "r2_buckets": [{ "binding": "DOCUMENTS", "bucket_name": "<BUCKET>" }],
     "d1_databases": [{ "binding": "DB", "database_name": "<NAME>", "database_id": "<D1_ID>" }],
     "kv_namespaces": [{ "binding": "CONFIG", "id": "<KV_ID>" }],
     "hyperdrive": [{ "binding": "HYPERDRIVE", "id": "<HYPERDRIVE_ID>" }]
   }
   ```

   The dashboard alternative is **Workers & Pages > Worker > Settings >
   Bindings > Add**: select R2, D1, KV, or Hyperdrive and select the matching
   resource. Keep binding names identical to names used in Worker code.
   Use distinct demo resources, including for preview builds. Consult the
   [R2](https://developers.cloudflare.com/r2/api/workers/workers-api-usage/),
   [D1](https://developers.cloudflare.com/d1/get-started/),
   [KV](https://developers.cloudflare.com/kv/get-started/), and
   [Hyperdrive](https://developers.cloudflare.com/hyperdrive/get-started/)
   setup guides at implementation time.
4. If retaining PostgreSQL behind a Worker, configure private database access
   through Workers VPC/Tunnel, database TLS, then Hyperdrive and its Worker
   binding. Verify PostgreSQL 18 compatibility independently before relying
   on Hyperdrive. Do not publish port 5432 to the internet merely to simplify
   configuration.
   For Containers, provision Workers Paid, add a Worker `Container` class,
   container image/Dockerfile entry, and a Durable Object binding in Wrangler;
   deploy with `wrangler deploy` on the production branch. Keep the container
   stateless and run PostgreSQL on durable external storage. The container
   cannot directly use `env.DB` or `env.DOCUMENTS` as a Python SDK object;
   expose only required operations through Worker outbound handlers or use
   a separately authenticated external service.
5. Build and validate the complete candidate at its `workers.dev` URL. Only
   after the candidate passes should the operator move
   `pimascor.delegateops.business` from the Tunnel CNAME to a Worker Custom
   Domain. [Custom Domains cannot be created on a hostname that still has a
   CNAME](https://developers.cloudflare.com/workers/configuration/routing/custom-domains/).
   Keep the Tunnel configuration available for rollback.

## Finish criteria and evidence

The implementation handoff is the repository-root `docs/agent/HANDOFF.md`.
Completion requires
the Docker Sandbox checks, OrbStack health and secret-read check, external URL
and browser role checks, R2 document checks if enabled, and a remote Git SHA
match. If R2 is not enabled, mark document workflows incomplete and do not
call the whole demo fully functional. No Cloudflare account or Mac runtime
check has been performed by this planner.
