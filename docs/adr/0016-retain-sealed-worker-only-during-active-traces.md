# ADR 0016: Retain the sealed worker only during active traces

Date: 28 September 2026
Status: implementation change; resource qualification pending

## Context

[ADR 0015](0015-reject-current-ebpf-candidate-on-idle-cost.md) rejected the measured
candidate on idle working set. The optional node service eagerly retained a
sealed 68.99 MiB worker image even with no active trace. The executable's
verification and sealing protect execution against installation-path replacement
and in-place modification; removing those protections is not an acceptable fix.

## Decision

Verify the accepted executable at service construction, then release that sealed
copy. Keep the accepted policy and programme directory as before. On the first
worker activation after an idle interval, reopen the installation-owned executable
path, verify its bytes against the unchanged signed policy, validate its static
ELF identity and seal a new executable descriptor before launching any process.

The runtime shares this immutable image between its at most two active workers.
Each worker owns a duplicated descriptor. After the last worker exits and releases
its descriptors, the runtime closes its retained image. Admission requests cannot
select the executable path, digest or programme. A changed installation fails the
next idle-to-active verification; an already sealed active image remains immutable.

Copying checks cancellation between bounded chunks. Runtime shutdown cancels
activation before waiting for its ownership lock, then prevents new work and
joins existing workers. Unconfirmed image cleanup quarantines the runtime and
cannot be reported as a successful close.

## Alternatives and consequences

Keeping an unsealed installation descriptor would not prevent in-place writes.
Retaining the complete sealed image while idle repeats the measured failure.
Creating a separate sealed copy for every concurrent worker would multiply its
memory cost. Sharing only during active work retains the integrity boundary and
removes the permanent idle copy.

Reactivation now incurs file I/O, hashing and sealing. The full active worker copy
still counts towards the trace's resource budget. This change alone does not prove
the 40 MiB idle or 64 MiB incremental active limits, activation latency, CPU cost,
loss, workload regression or teardown thresholds. Debug stripping alone was
insufficient for the previous eager design; any rebuilt worker needs new immutable
identity and measurements. No budget, accounting formula or support claim changes.

## Verification and rollout

Non-loading Linux tests exercise the production runtime with a signed programme
bundle and a static protocol fixture: startup validation, changed installation
rejection, concurrent image sharing, cancellation, last-exit release, denied target
cleanup and quarantine on unconfirmed close. These do not establish BPF correctness
or resource qualification for a new candidate.

Keep the previous five failed idle pairs and ADR 0015 intact. A new candidate must
receive its own complete measurements before a performance go decision. The
standard agent, chart and release distribution remain unaffected. Rolling back
this change restores eager retention and its known idle-budget failure; it does
not restore a qualified trace profile.
