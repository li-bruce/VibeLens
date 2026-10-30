/** Read-only live inspection. The first snapshot is a baseline, never future evidence.
 * Capturing, seeking or changing this projection does not send business commands.
 */
export class LiveTrace {
  constructor(limit = 20000) {
    this.limit = limit;
    this.reset();
  }
  reset() {
    this.current = null;
    this.known = new Set();
  }
  observe(view, version, now = new Date().toISOString()) {
    if (view.stage === "design" || view.historical) return null;
    if (!this.current || this.version !== version) {
      this.version = version;
      this.known = new Set((view.events || []).map((event) => event.id));
      this.current = {
        schema: "stategraph-recording/v1",
        id: "live:" + version,
        status: "recording",
        transient: true,
        started_at: now,
        ended_at: null,
        context: structuredClone(view),
        final: structuredClone(view),
        events: [],
        commands: [],
        gaps: [],
        capture: { mode: "all" },
        build_id: view.manifest.build_id,
        run_id: view.health.run_id,
      };
    }
    const value = this.current;
    if (value.status === "limited") return value;
    for (const event of view.events || []) {
      if (this.known.has(event.id)) continue;
      if (value.events.length >= this.limit) {
        value.status = "limited";
        value.ended_at = value.observed_until;
        value.gaps.push("Live inspection limit reached; start a recording for a new interval.");
        break;
      }
      this.known.add(event.id);
      value.events.push(structuredClone(event));
    }
    // Native frames carry exact internal states. No state is inferred from drawing.
    if (value.status !== "limited") {
      value.final = structuredClone(view);
      value.observed_until = now;
      value.runtime_frames = structuredClone(view.runtime_frames || { frames: [] });
    }
    this.current = { ...value, events: [...value.events] };
    return this.current;
  }
}
