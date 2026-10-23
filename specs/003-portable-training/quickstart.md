# Validation guide

Install the approved external dependency source copies, then install CY from its source checkout and cy-queue from its sibling checkout into the same environment. Neither package is assumed available from an index. Follow [development](../../docs/development.md) and [queue operations](../../docs/queue.md).

Run offline tests and architecture checks before native execution. Validate cy/cy-train help and configuration output without assets or queue setup; queue submit defaults to pipeline and accepts --command train. Run real backend training and queue/Agent tests only after the end-to-end/environment preflight, with explicit task-owned project/tags and output locations. Verify downloaded artifacts/models independently. Live Artifactory connectivity is excluded; local HTTP proxy construction/fallback tests remain required.
