/** Lossless recordings stay off the critical path and retain their reviewed hash. */
export async function loadForestRecord(url, expectedHash, fetcher = fetch) {
  const response = await fetcher(url);
  if (!response.ok) throw Error(`Recording unavailable (${response.status})`);
  const compressed = await response.arrayBuffer();
  const stream = new Blob([compressed]).stream().pipeThrough(new DecompressionStream("gzip"));
  const raw = await new Response(stream).arrayBuffer();
  const digest = await crypto.subtle.digest("SHA-256", raw);
  const hash = [...new Uint8Array(digest)]
    .map((byte) => byte.toString(16).padStart(2, "0"))
    .join("");
  if (hash !== expectedHash) throw Error("Recording checksum differs from the reviewed export");
  return JSON.parse(new TextDecoder().decode(raw));
}
