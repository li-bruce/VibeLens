/** Standalone observer control client for Node and browser-native probes.
 * No command invokes application functions or edits declarations/source.
 */
export class BOCaptureClient {
  constructor(probe) {
    this.bo_probe = probe;
    this.bo_stopped = false;
    this.bo_errors = 0;
  }
  async bo_exchange(action, extra = {}) {
    const probe = this.bo_probe;
    const send = () =>
      fetch(probe.bo_endpoint + "/api/bo/capture", {
        method: "POST",
        signal: AbortSignal.timeout(2000),
        headers: { "Content-Type": "application/json", "X-BO-Token": probe.bo_token },
        body: JSON.stringify({
          protocol: "bo-capture-control/v1",
          project_id: probe.bo_project.project_id,
          build_id: probe.bo_build,
          producer_id: probe.bo_producer,
          action,
          ...extra,
        }),
      });
    // Guard the instrumented call synchronously; never suppress unrelated work
    // while its HTTP promise is pending. OTel propagates its own context scope.
    const previous = probe.bo_internal;
    let pending;
    probe.bo_internal = true;
    try {
      pending = probe.bo_tracing ? probe.bo_tracing.internal(send) : send();
    } finally {
      probe.bo_internal = previous;
    }
    const response = await pending;
    if (!response.ok) throw Error("Capture control rejected: " + response.status);
    const text = await response.text();
    if (text.length > 24576) throw Error("Capture control response exceeds limit");
    const value = JSON.parse(text);
    if (
      !value ||
      Object.keys(value).sort().join(",") !== "commands,protocol" ||
      value.protocol !== "bo-capture-control/v1" ||
      !Array.isArray(value.commands) ||
      value.commands.length > 64 ||
      value.commands.some((command) => !command || typeof command.id !== "string")
    )
      throw Error("Invalid capture control response");
    return value;
  }
  async start() {
    await this.bo_exchange("register");
    this.bo_running = this.bo_poll();
    return this;
  }
  async bo_poll() {
    while (!this.bo_stopped) {
      try {
        const reply = await this.bo_exchange("poll");
        for (const command of reply.commands) {
          let ok = false;
          const keys = Object.keys(command).sort().join(",");
          if (command.action === "scope" && keys === "action,id,nodes") {
            this.bo_probe.bo_set_scope(command.nodes);
            ok = true;
          } else if (
            command.action === "flush" &&
            keys === "action,id,timeout_ms" &&
            Number.isInteger(command.timeout_ms) &&
            command.timeout_ms > 0 &&
            command.timeout_ms <= 30000
          ) {
            ok = await this.bo_probe.flush(command.timeout_ms);
          }
          await this.bo_exchange("ack", {
            ack: { id: command.id, ok: !!ok, health: this.bo_probe.bo_health() },
          });
        }
      } catch {
        this.bo_errors++;
      }
      if (!this.bo_stopped) await new Promise((resolve) => setTimeout(resolve, 100));
    }
  }
  async close() {
    this.bo_stopped = true;
    await this.bo_running;
  }
}
