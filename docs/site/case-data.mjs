/** Rehydrate generated transport copies without changing recorded facts or IDs. */
export function unpackCase(payload) {
  if (payload.schema !== "vibelens-case-transport/v1") throw Error("Unsupported case transport");
  const data = payload.data;
  const read = (path) =>
    path.reduce((value, key) => {
      if (["__proto__", "prototype", "constructor"].includes(key) || !Object.hasOwn(value, key))
        throw Error("Invalid case reference");
      return value[key];
    }, data);
  for (const [target, source] of payload.aliases) {
    const holder = read(target.slice(0, -1)),
      key = target.at(-1);
    if (!Object.hasOwn(holder, key) || holder[key] !== null)
      throw Error("Invalid case placeholder");
    // Independent copies preserve the original artifact's mutation boundaries.
    holder[key] = structuredClone(read(source));
  }
  return data;
}

export async function loadJson(url, fetcher = fetch) {
  const response = await fetcher(url);
  if (!response.ok) throw Error(`Unable to load demo data (${response.status})`);
  return response.json();
}
