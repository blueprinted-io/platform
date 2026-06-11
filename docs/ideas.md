# Ideas

Unscheduled product ideas worth keeping. Not commitments — candidates to weigh
against the roadmap when planning a sprint. One `##` section per idea, newest
first. When an idea is adopted, move its content into the spec and replace the
section body with a one-line pointer; if rejected, note why rather than deleting.

---

## Capture-based ingestion (workflow recording as a source type)

**Added:** 2026-06-11 · **Status:** idea · **Inspiration:** Guidde (guidde.com), an AI
video-documentation SaaS — browser-extension capture, AI-generated guides.

### The observation

Our ingestion sources (PDF, HTML, JSON) are documents *about* workflows, and triage
has to guess how many tasks are buried in each chunk. A recorded workflow session is
already step-shaped: one session ≈ one task candidate, steps pre-segmented by the
user's actual clicks and navigation. Capture-based ingress would improve acquisition
fidelity at the point where our pipeline works hardest.

Guidde's bet is removing humans from creation entirely (capture → AI guide → publish).
Ours is the opposite — but their *capture* layer is better than anything we have for
acquisition, and it composes with our governance instead of competing with it: a
capture session produces draft candidates that flow through triage review → commit
like everything else. The trust gate stays intact.

### Three sizes

1. **Zero-backend version.** A browser extension that records clicks/inputs/page
   titles and emits our existing JSON import schema (v1.0): `{title, steps:
   [{action, target, context}, ...]}`. The JSON path already bypasses chunking and
   creates candidates synchronously — capture quality can be rough because everything
   lands as draft candidates behind the human gate. Pure client-side project.

2. **Fourth source type.** A `capture` ingestion alongside pdf/html/json accepting an
   event stream + per-step screenshots. Screenshots need the storage abstraction
   (local/MinIO) and image refs on steps. A real sprint, including a spec section.

3. **Full capture tooling.** Desktop/extension capture with editing before submission
   (closest to Guidde's Magic Capture). Only worth considering if 1 or 2 proves the
   acquisition-quality hypothesis.

### Design constraints to carry in

- **Redaction at capture time, not review time.** Screen capture ingests whatever is
  on screen — credentials, PII, customer data. Redact client-side before upload
  (Guidde calls this Magic Redaction). Fits the existing secrets posture.
- **Never confirmed.** Like all ingestion, capture produces task candidates at draft
  or submitted status only — the no-machine-can-confirm rule (§10.2) applies unchanged.
- **Steps carry provenance.** Source URL, timestamp, app context per step — the same
  frontmatter discipline as HTML ingestion.

### Where it sits

Weigh against the Sprint 13 deferred-product list when planning. Option 1 is small
enough to be a side-project sprint item; option 2 needs a spec version bump.
