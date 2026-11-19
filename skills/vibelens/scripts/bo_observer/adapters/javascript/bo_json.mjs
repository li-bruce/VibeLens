/** Preserve the portable JSON boundary before JSON.parse discards duplicate keys. */
export function bo_parseJson(raw) {
  const text = raw.toString("utf8").replace(/^\uFEFF/, "");
  let offset = 0;
  const space = () => {
    while (/\s/.test(text[offset] ?? "") && offset < text.length) offset++;
  };
  function string() {
    const start = offset++;
    while (offset < text.length) {
      const current = text[offset++];
      if (current === "\\") offset++;
      else if (current === '"') return JSON.parse(text.slice(start, offset));
    }
    throw Error("invalid_json_string");
  }
  function value(depth = 0) {
    if (depth > 256) throw Error("json_depth_limit");
    space();
    const kind = text[offset];
    if (kind === '"') {
      string();
      return;
    }
    if (kind === "{" || kind === "[") {
      offset++;
      const close = kind === "{" ? "}" : "]";
      const keys = new Set();
      space();
      if (text[offset] === close) {
        offset++;
        return;
      }
      while (offset < text.length) {
        if (kind === "{") {
          space();
          if (text[offset] !== '"') throw Error("invalid_json_key");
          const key = string();
          if (keys.has(key)) throw Error("duplicate_json_key");
          keys.add(key);
          space();
          if (text[offset++] !== ":") throw Error("invalid_json_separator");
        }
        value(depth + 1);
        space();
        const next = text[offset++];
        if (next === close) return;
        if (next !== ",") throw Error("invalid_json_separator");
      }
      throw Error("invalid_json_container");
    }
    const token = /^(?:true|false|null|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?)/.exec(
      text.slice(offset),
    );
    if (!token) throw Error("invalid_json_value");
    offset += token[0].length;
    if (/^-?\d/.test(token[0])) {
      const numeric = Number(token[0]);
      if (!Number.isFinite(numeric) || (/^-?\d+$/.test(token[0]) && !Number.isSafeInteger(numeric)))
        throw Error("nonportable_json_number");
    }
  }
  value();
  space();
  if (offset !== text.length) throw Error("invalid_json_trailing");
  return JSON.parse(text);
}
