# Memory history trust boundaries

This model covers the optional history adapter and named read endpoints. It does
not extend the standard collector's support or eBPF qualification claims.

## Assets and actors

Protected assets are the remote read credential, Kubernetes caller authority,
tenant workload names and immutable identities, accurate source semantics, and
the availability of live diagnosis. A namespace reader may submit hostile queries
or attempt another namespace's objects. A configured backend may fail, return
malformed/oversized data, duplicate series, stale samples or unexpected labels.

The operator controls the fixed backend URL, CA bundle, cluster label, scope
allow-list and viewer bindings. The backend is trusted to report measurements
honestly within that configured source contract. Structural validation cannot
prove that a compromised metric exporter measured the value it reports.

## Request and disclosure boundaries

1. The aggregation layer authenticates the caller and authorises the named trends
   subresource. The handler validates bounded query fields and enabled scopes.
2. A separate gate permits one history operation. Resolver checks additionally
   authorise the reader for each Pod and the required current owner chain.
3. Pod identities use live Kubernetes metadata and the collector's current Node
   inventory. Node-only reads require Node permission. Workloads retain current
   controller UID/generation and bounded current member identities.
4. The provider receives only fixed metric selectors for those immutable targets,
   escaped as PromQL string literals. No caller controls the URL, credentials,
   arbitrary expression, redirect or an unbounded range.
5. Verified HTTPS and a read-only credential protect the backend request. Byte,
   label, series, point and time limits apply even if the backend ignores its own
   requested limit. Matching values and timestamps come from one evaluation.
6. Unexpected identities, duplicate source series and ambiguous JSON fail closed.
   Raw backend warnings/errors, extra labels and cgroup paths are not disclosed.
7. The resolver repeats the named history-subresource, object and lifetime checks
   before the response is written.
   A replacement, changed cohort or revoked permission discards the result.
8. The client validates the response against its requested scope, source, metric,
   identities and bounds. Obsolete TUI requests are cancelled and late responses
   are ignored. Live-reader revocation clears retained history views.

## Privacy and availability controls

Queries necessarily send authorised workload identifiers to the operator's
configured metric service. That service may retain query logs under its own
policy. No caller identity, application path, arbitrary label or credential is
added to metrics, incident captures or application logs by this feature.

The history gate is separate from the live-read gate. The provider has one active
query, a five-second deadline and no retries; the API has a nine-second deadline.
The client uses a ten-second history deadline without changing ordinary live-read
timeouts. Earlier caller cancellation wins. State is bounded per request and no
new retention store or polling task is added.

Missing, disabled, unsupported, partial, stale and zero remain distinct. Provider
failure never silently substitutes cgroup charge for working set/RSS. Current
running container instances are the supported cohort; older or stopped instances
are excluded rather than rebound by name. Local fallback keeps its actual source
and configured freshness interval, capped at two minutes.

## Operational assumptions and verification

Protect the configured backend, its immutable identity enrichment, CA and bearer
Secret. A read-only token and fixed selectors limit what KubeMemLens requests;
they do not make an untrusted backend authoritative. Use network controls to
restrict remote egress where needed. No privilege, host access, exec permission or
existing viewer-role expansion is required. Explicit Node scope adds `get nodes`
acquisition; workload scope adds bounded controller/member acquisition.
The Node-history viewer cannot read the collector's separate Node inventory or
its container counts.

Verification covers cross-namespace/instance responses, revocation, replacement,
owner-chain changes, duplicates, malformed and oversized responses, maximum
profiles, cancellation, source switching, terminal bounds and chart permissions.
Local cluster install, denial, revocation and rollback checks passed in the
[qualification record](../qualification-results/memory-history-local-kind-2026-09-28/README.md).
See [the operator contract](../memory-history.md) for source and permission limits.
