/** Observe a native Node request listener before any middleware can reject it.
 * The project supplies source-bound route identities. No routing, permission,
 * state transition, response body or server lifecycle is owned by this adapter.
 */
import { AsyncLocalStorage } from "node:async_hooks";
import { bo_use_context_store } from "./bo_runtime.mjs";

const bo_wrapped = Symbol("vibelens.http.boundary");

/** Wrap once during bootstrap; return null from resolve for observer/unmapped routes.
 * resolve(request) returns { node, inputs?, context? }. It must use the project's
 * registered routes, without reading/consuming the request body. Default outputs
 * are status, completed and duration_ms; BOProbe copies only declared fields.
 */
export function bo_observeHttp(handler, { probe, resolve }) {
  if (typeof handler !== "function" || typeof resolve !== "function" || !probe?.startSpan)
    throw new TypeError("HTTP observation requires a handler, probe and route resolver");
  if (handler[bo_wrapped]) throw new Error("HTTP handler is already observed");
  // Only the native probe's task-local context is initialized here. An optional
  // application-owned OTel context manager still takes precedence in BOProbe.
  bo_use_context_store(new AsyncLocalStorage());

  function bo_request(request, response, ...args) {
    let binding;
    try {
      binding = resolve(request);
    } catch {
      // Observation failures remain visible without changing the native response.
      probe.bo_errors++;
      probe.bo_last_error = { stage: "http_mapping", type: "ResolverError" };
      return handler.call(this, request, response, ...args);
    }
    if (binding == null) return handler.call(this, request, response, ...args);
    const started = performance.now();
    const activation = probe.startSpan(binding.node, () => ({ inputs: binding.inputs || {} }), {
      ...binding.context,
      parentCallId: null,
      parentEventId: null,
    });
    let closed = false;

    // finish means Node handed the response to its transport, not client receipt
    // or business success. A premature close may have no sent HTTP status at all.
    const values = () => ({
      outputs: {
        ...(response.headersSent ? { status: response.statusCode } : {}),
        completed: response.writableFinished,
        duration_ms: performance.now() - started,
      },
    });
    const detach = () => {
      closed = true;
      response.off("finish", complete);
      response.off("close", complete);
    };
    const complete = () => {
      if (closed) return;
      detach();
      activation.finish(values);
    };
    response.once("finish", complete);
    response.once("close", complete);
    try {
      return activation.runUntilEnd(() => handler.call(this, request, response, ...args));
    } catch (error) {
      detach();
      activation.fail(() => ({ ...values(), exception: probe.bo_exception(error) }));
      throw error;
    }
  }
  bo_request[bo_wrapped] = true;
  return bo_request;
}
