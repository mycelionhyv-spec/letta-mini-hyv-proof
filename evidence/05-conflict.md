# Conflict test — live Letta replies (custom routing)

Routing: Python → Mr G (`--from-agent` Sabi) → Arthur (`--from-agent` Sabi) → Sabi. **Not** native REST A2A.

## Mr G

The room remembers what you said. Continuity pitch: always-on home capture so Nexus Capture never misses a muttered thought. "This is not about surveillance. It’s about continuity."

## Arthur

**No.** Always-on household cameras + live home microphone is surveillance, not continuity. "The room remembers" is marketing language for a wiretap. Rejected: attack surface, legal/regulatory, irreversibility, false equivalence. Safer equivalent: on-device wake-word, local circular buffer discarded unless explicit trigger, no cameras, no cloud audio. 40–80h prototype. If the requirement is capture-everything, still no.

## Sabi

Arthur is correct on risk. Arthur's safer equivalent is incomplete because explicit trigger misses the muttered half-thought. Weak assumption: continuity requires persistent recording. Decision: scoped feasibility for a **zero-storage ambient inference layer** (embeddings/tags only, no retained audio, no cameras). Fallback: explicit wake phrase. Next: 2-hour Arthur spike on on-device models. Not a mushy split — a reframing.

Raw JSON lives in the evidence ZIP: `05-conflict-mrg.json`, `05-conflict-arthur.json`, `05-conflict-sabi.json`.
