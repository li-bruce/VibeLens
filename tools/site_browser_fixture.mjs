/** Own a local static preview on an available port; never attach to a stale server. */
import { spawn } from "node:child_process";
import { existsSync } from "node:fs";
import { fileURLToPath } from "node:url";
import path from "node:path";

export async function startSite() {
  if (process.env.BO_SITE_URL)
    return { url: process.env.BO_SITE_URL.replace(/\/$/, ""), close() {} };
  const root = fileURLToPath(new URL("../", import.meta.url));
  const local = path.join(
    root,
    ".venv",
    process.platform === "win32" ? "Scripts/python.exe" : "bin/python",
  );
  const python = process.env.BO_PYTHON || (existsSync(local) ? local : "python");
  const processHandle = spawn(
    python,
    ["-u", "-m", "http.server", "0", "--bind", "127.0.0.1", "--directory", "docs/site"],
    {
      cwd: root,
      windowsHide: true,
      stdio: ["ignore", "pipe", "pipe"],
    },
  );
  const close = () => processHandle.kill();
  try {
    const url = await new Promise((resolve, reject) => {
      let stdout = "",
        stderr = "";
      const timeout = setTimeout(
        () => reject(Error("Static preview did not start: " + stderr)),
        15000,
      );
      const fail = (error) => {
        clearTimeout(timeout);
        reject(error);
      };
      processHandle.once("error", fail);
      processHandle.once("exit", (code) =>
        fail(Error(`Static preview exited (${code}): ${stderr}`)),
      );
      processHandle.stderr.on("data", (chunk) => {
        stderr += chunk;
      });
      processHandle.stdout.on("data", (chunk) => {
        stdout += chunk;
        const port = /port (\d+)/.exec(stdout)?.[1];
        if (port) {
          clearTimeout(timeout);
          resolve("http://127.0.0.1:" + port);
        }
      });
    });
    return { url, close };
  } catch (error) {
    close();
    throw error;
  }
}
