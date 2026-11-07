# Shared MongoDB acceptance — 2026-10-02

User authorized provisioning shared MongoDB and retesting FiftyOne persistence.
MongoDB was added through k8s-infra's maintained deployment entrypoint, separately
from ClearML's internal database. Shared resources remain running by design.

## Deployed state and checks

- Context `docker-desktop`, namespace `mongodb`, one ready `mongodb-0` pod running
  `mongo:8.0.17`, zero restarts at acceptance.
- PVC `data-mongodb-0`: Bound, 8 GiB, RWO, explicit `local-path` on NVMe.
- LoadBalancer `mongodb-lb`: host `localhost:27018`; cluster Service
  `mongodb.mongodb.svc.cluster.local:27017`.
- Host port allocation was serialized through the Git common-dir reservation
  lock, with WSL, Windows TCP/UDP, Docker published ports, Kubernetes services,
  Windows exclusions, and OS dynamic ranges inspected before reservation.
- Root and project passwords survived reconciliation. Root credentials stay in
  `mongodb-root` and optional ignored `mongodb-stand/.env`; project access is in
  `mongodb-clearml-yolo-access`. No credential values appear in tracked output.
- Project user has `readWrite` only on `clearml_yolo` and `clearml_yolo_tests`.
  Actual reads against unrelated database/admin collections failed with MongoDB
  authorization code 13. Host ping/server version verified authenticated access.
- Bootstrap clients were disposable SecretRef-equipped pods; no server exec.
  No bootstrap client remains. Existing shared services were preserved.
- `bash deploy.sh --validate`: 470 tests run, 5 existing unrelated skips, success;
  source Markdown local links and Python/shell helper checks passed.
- `bash mongodb-stand/deploy_mongodb.sh --check`: server-side dry run passed,
  stable credentials retained and explicit NVMe storage verified.
- `infra.py whoami-all --project clearml-yolo`: both stand Secrets present,
  ClearML authenticated; MongoDB's no-run-object row checks Secret keys only.
- Global environment helper: 30 tests passed. A real source selected the shared
  MongoDB application database and shared local lock directory without printing
  credentials; tag-scoped local scratch/ClearML cleanup then found no objects.

Independent review corrections also cover stale database exports: before credential
refresh, the environment helper clears the prior URI/database name. A failed refresh
or missing helper warns and leaves computation usable without retaining a previous
database selection.

The broader NVMe check observed Docker Desktop's `hostpath` also marked default.
The new stand explicitly selects `local-path`; unrelated defaults were preserved.

## Real FiftyOne verification

Before imports, test environment was loaded from the project Secret with
`FIFTYONE_DATABASE_NAME=clearml_yolo_tests` and a fresh task-owned local
`FIFTYONE_DATABASE_DIR`. Nine persistence tests passed, with 723 upstream
deprecation warnings, in 5.15 seconds. Each test's UUID-prefixed datasets were
removed and the dataset inventory returned to its initial state.

The exact reported row 225 was separately published with synthetic 1920×1464
media. Readback retained the zero-height detection, Unicode label, original
confidence and `dm_index=225`, and the receipt marked publication complete.
Its task-prefixed dataset was deleted afterward; the shared service was retained.

Initial verification exposed a URI path/MongoEngine database-name conflict.
Removing the URI's database path, keeping `authSource=clearml_yolo`, and rejecting
such paths in the env helper made application/test selection consistent. The nine
datasets written by that initial attempt were identified and individually removed
from the application database. No whole-database deletion was used.

No GPU model execution or real ClearML artifact-upload outcome is established.
Local file locks do not establish cross-host concurrency safety. Data was read
back from MongoDB, but a server restart/reboot durability test was not performed.
