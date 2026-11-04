/** Small layout hints from physical source locality and identifier spelling.
 * These hints never become graph relations. Each item checks a bounded set of
 * neighbors; display aliases and AI explanations do not participate.
 */
const metadata = new WeakMap();
const candidateLimit = 32;
const tokenLimit = 12;
const ignored = new Set(["api", "get", "post", "put", "delete", "function", "parameter", "code"]);

function describe(item) {
  const node = item.node || item;
  if (metadata.has(node)) return metadata.get(node);
  const source = node.source || {},
    path = String(source.path || "").replaceAll("\\", "/"),
    line = Number(source.selection?.line ?? source.line ?? source.start_line ?? 0),
    identifier = String(source.symbol || node.source_name || node.signature || node.id || ""),
    tokens = [
      ...new Set(
        identifier
          .replace(/([a-z])([A-Z])/g, "$1 $2")
          .toLowerCase()
          .match(/[\p{L}][\p{L}\p{N}]*/gu) || [],
      ),
    ]
      .filter((token) => token.length > 1 && !ignored.has(token))
      .sort()
      .slice(0, tokenLimit),
    value = { path, line: Number.isFinite(line) ? line : 0, tokens };
  metadata.set(node, value);
  return value;
}

/** Build once per layout request, then reuse across every nested local group. */
export function proximityNeighbors(edges) {
  const neighbors = new Map();
  for (const edge of edges) {
    if (edge.from === edge.to) continue;
    for (const [a, b] of [
      [edge.from, edge.to],
      [edge.to, edge.from],
    ]) {
      if (!neighbors.has(a)) neighbors.set(a, new Set());
      neighbors.get(a).add(b);
    }
  }
  return new Map([...neighbors].map(([id, ids]) => [id, [...ids].sort().slice(0, candidateLimit)]));
}

/** Rank a single existing type/owner group, with actual neighbors preferred.
 * Source files and identifier buckets only propose nearby candidates. Buckets
 * are capped so a common word cannot produce an all-pairs comparison.
 */
export function proximityOrder(items, edges = []) {
  if (items.length < 3) return items.slice().sort((a, b) => a.id.localeCompare(b.id));
  const ordered = items.slice().sort((a, b) => a.id.localeCompare(b.id)),
    byId = new Map(ordered.map((item) => [item.id, item])),
    facts = new Map(ordered.map((item) => [item.id, describe(item)])),
    candidates = new Map(ordered.map((item) => [item.id, new Set()])),
    adjacent = new Map(ordered.map((item) => [item.id, new Set()])),
    files = new Map(),
    buckets = new Map();
  const propose = (a, b) => {
    if (a !== b && candidates.get(a).size < candidateLimit) candidates.get(a).add(b);
  };
  const neighbors = edges instanceof Map ? edges : proximityNeighbors(edges);
  for (const item of ordered)
    for (const id of neighbors.get(item.id) || [])
      if (byId.has(id)) {
        adjacent.get(item.id).add(id);
        propose(item.id, id);
      }
  for (const item of ordered) {
    const fact = facts.get(item.id);
    if (fact.path) {
      if (!files.has(fact.path)) files.set(fact.path, []);
      files.get(fact.path).push(item.id);
    } else {
      for (const token of fact.tokens) {
        if (!buckets.has(token)) buckets.set(token, []);
        const bucket = buckets.get(token);
        if (bucket.length < candidateLimit) bucket.push(item.id);
      }
    }
  }
  for (const file of files.values()) {
    file.sort((a, b) => facts.get(a).line - facts.get(b).line || a.localeCompare(b));
    for (let i = 0; i < file.length; i++)
      for (let j = Math.max(0, i - 4); j <= Math.min(file.length - 1, i + 4); j++)
        propose(file[i], file[j]);
  }
  for (const bucket of buckets.values())
    for (const a of bucket) for (const b of bucket) propose(a, b);
  const score = (a, b) => {
    const left = facts.get(a),
      right = facts.get(b);
    if (adjacent.get(a).has(b)) return 10;
    if (left.path && left.path === right.path)
      return 2 + 1 / (1 + Math.abs(left.line - right.line) / 32);
    if (left.path || right.path) return 0;
    const overlap = left.tokens.filter((token) => right.tokens.includes(token)).length;
    return overlap / Math.max(1, left.tokens.length + right.tokens.length - overlap);
  };
  const remaining = new Set(ordered.map((item) => item.id)),
    result = [];
  let fallback = 0,
    current = ordered[0].id;
  while (remaining.size) {
    remaining.delete(current);
    result.push(byId.get(current));
    let next,
      best = 0;
    for (const id of candidates.get(current)) {
      if (!remaining.has(id)) continue;
      const value = score(current, id);
      if (value > best || (value === best && value > 0 && id.localeCompare(next) < 0)) {
        next = id;
        best = value;
      }
    }
    if (!next) {
      while (fallback < ordered.length && !remaining.has(ordered[fallback].id)) fallback++;
      next = ordered[fallback]?.id;
    }
    current = next;
  }
  return result;
}

/** Fold the local order into a compact serpentine grid for either XY or XZ.
 * The force solver keeps real links, bridge placement and collision as the
 * primary layout constraints; this function supplies initial/target positions.
 */
export function proximitySeeds(items, edges = [], span = 100) {
  if (!items.length) return new Map();
  const ordered = proximityOrder(items, edges),
    width = Math.ceil(Math.sqrt(ordered.length)),
    rows = Math.ceil(ordered.length / width),
    step = span / Math.max(1, width - 1, rows - 1);
  return new Map(
    ordered.map((item, index) => {
      const row = Math.floor(index / width),
        col = index % width;
      return [
        item.id,
        {
          x: ((row % 2 ? width - col - 1 : col) - (width - 1) / 2) * step,
          y: (row - (rows - 1) / 2) * step,
        },
      ];
    }),
  );
}
