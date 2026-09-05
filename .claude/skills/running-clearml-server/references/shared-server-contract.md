# Shared ClearML server contract

`clearml-yolo` uses the existing local self-hosted ClearML service:

| Service | Endpoint |
| --- | --- |
| Web UI | `http://localhost:8580` |
| API | `http://localhost:8008` |
| File server | `http://localhost:8081` |

The UI uses port 8580 because port 8080 is occupied by the CVAT Traefik service
on this machine. SDK credentials are user-local in `~/clearml.conf` and are not
repository content. Keep them private and leave credential rotation, server
data, and deployment lifecycle to the service owner.

For a ClearML-backed pipeline, verify the configured credentials with
`./scripts/check_env.sh` from the repository. It performs the meaningful
authenticated check; `debug.ping` is only a reachability signal.
