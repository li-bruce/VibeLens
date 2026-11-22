/** Retain browser-owned requests (including favicons) that page events can miss. */
export async function observeResources(page) {
  const responses = [],
    failures = [],
    consoleErrors = [],
    pageErrors = [];
  const session = await page.context().newCDPSession(page);
  await session.send("Network.enable");
  session.on("Network.responseReceived", ({ response, type }) => {
    const item = { url: response.url, status: response.status, type };
    responses.push(item);
    if (response.status >= 400) failures.push(item);
  });
  // Request failures have no HTTP status; preserve their actual URL separately.
  page.on("requestfailed", (request) =>
    failures.push({
      url: request.url(),
      status: null,
      type: request.resourceType(),
      error: request.failure()?.errorText,
    }),
  );
  page.on("console", (message) => {
    if (message.type() === "error")
      consoleErrors.push({ text: message.text(), location: message.location() });
  });
  page.on("pageerror", (error) => pageErrors.push(String(error.stack || error)));
  /** Subscribe before the action; a completed fetch can precede CDP delivery. */
  const waitForResponse = (url, timeout = 10000) => {
    const observed = responses.find((r) => r.url === url);
    if (observed) return Promise.resolve(observed);
    return new Promise((resolve, reject) => {
      const finish = ({ response, type }) => {
        if (response.url !== url) return;
        clearTimeout(timer);
        session.off("Network.responseReceived", finish);
        resolve({ url, status: response.status, type });
      };
      const timer = setTimeout(() => {
        session.off("Network.responseReceived", finish);
        reject(new Error(`No browser response for ${url}`));
      }, timeout);
      session.on("Network.responseReceived", finish);
    });
  };
  return { responses, failures, consoleErrors, pageErrors, waitForResponse };
}
