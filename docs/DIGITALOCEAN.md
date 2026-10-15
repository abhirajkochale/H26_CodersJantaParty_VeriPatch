# DigitalOcean worker deployment

Use an **existing Ubuntu 24.04 Droplet** with at least 2 vCPU, 4 GB RAM, adequate disk, Docker-compatible Linux and outbound HTTPS. This integration does not create or bill resources automatically. Deployment and Droplet access are user-operated steps. Worker setup installs host packages and grants its dedicated account Docker access (administrative capability); use a disposable Droplet without other secrets/workloads.

1. Copy this repository to the existing Droplet using your normal authenticated deployment process.
2. From that checkout run `sudo bash worker/setup.sh`. This installs Docker/Git/Python, the worker under `/opt/veripatch`, and pulls `python:3.12-slim`. Host Python only coordinates; target execution always uses Python 3.12 in Docker.
3. Add your dedicated coordinator **public** SSH key to `/home/veripatch/.ssh/authorized_keys`. Prefix it with the forced command and restrictions:

```text
restrict,command="/opt/veripatch/bin/worker" ssh-ed25519 YOUR_PUBLIC_KEY
```

Ensure `.ssh` is mode 700, `authorized_keys` is mode 600, and both belong to `veripatch`. Never copy your private key into the worker job or container. Reconnect after group changes. Restrict inbound port 22 to your coordinator IP with the Droplet firewall. The worker exposes no public HTTP API.

4. Verify the Droplet's SSH fingerprint through the DigitalOcean console, then add the verified host key to your Mac's `known_hosts` using your normal SSH workflow. Do not disable host-key verification. A blindly accepted `ssh-keyscan` result is not identity verification.
5. Set these fields in the Mac's gitignored `.env`:

```dotenv
DO_SSH_HOST=YOUR_DROPLET_IP
DO_SSH_USER=veripatch
DO_SSH_PORT=22
DO_SSH_KEY_PATH=/absolute/path/to/dedicated_private_key
```

Key path is optional if your SSH agent has the key. The client uses `BatchMode=yes`, `StrictHostKeyChecking=yes`, a 10-second connection deadline and the single remote command `/opt/veripatch/bin/worker`.

6. Restart the coordinator, then run:

```bash
PYTHONPATH=app app/.venv/bin/python -m veripatch worker-smoke
PYTHONPATH=app app/.venv/bin/python -m veripatch analyze https://github.com/rishrek/LinkWatch --provider DIGITALOCEAN
```

Smoke validates worker protocol v1, real DigitalOcean metadata Droplet ID and Docker daemon availability. An SSH connection alone is insufficient. Analyze must execute a baseline; apply a reviewed proposal to execute cloud patched verification. Inspect actual logs and export a capsule to prove integration.

## Protocol and cleanup

UTF-8 JSON on stdin, exactly one JSON result on stdout. Supported actions: `smoke`, `verify`. Request includes `version`, public GitHub `url`, exact 40-character `commit`, structured `edits`, canonical SHA-256 `patch_hash`. Result includes worker version, provider, Droplet ID, exact commit/hash, runtime, container image ID, fixed profile, commands and counts. Errors return JSON and nonzero exit status; coordinator rejects invalid JSON, version/provider/commit/hash mismatches and SSH failures.

Each job has its own `/var/lib/veripatch/vp-*` directory. Only this directory is mounted into the container. Docker drops all capabilities, denies privilege escalation, limits CPU (2), RAM (2 GB), processes (128), individual file size (128 MB), uses a read-only root filesystem and a bounded temporary filesystem. Dependencies need outbound network; containers are not fully network-isolated. Per-command deadlines kill process groups. A 1,100-second Docker deadline forcibly removes the named container. `finally` removes per-job data after results are captured. Abrupt host shutdown may leave jobs; inspect and remove stopped `vp-*` containers/directories before a public demo.

## Troubleshooting and limits

- `DigitalOcean not configured.`: set host in `.env` and restart; no cloud verification occurred.
- SSH denied/unknown host: verify key, permissions, firewall and host fingerprint. Never bypass verification.
- Metadata failure: worker must actually be on a DigitalOcean Droplet with metadata available.
- Docker permission/daemon failure: reconnect after group change, check `systemctl status docker`.
- Image download/install timeout: inspect worker logs and outbound network/disk capacity.
- Worker version mismatch: deploy matching sources; never accept incompatible protocol silently.
- Containers share the host kernel and have outbound networking. For adversarial repositories, add infrastructure isolation and network policy. Do not co-host credentials or valuable workloads.

No cloud execution has been demonstrated until an actual configured Droplet returns successful worker results. LOCAL remains available independently.
