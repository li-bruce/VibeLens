/** Full files are fetched on demand; graph bindings only supply source locations. */
export function sourceLines(source, binding) {
  const selection = binding.selection;
  return source.split("\n").map((text, index) => {
    const number = index + 1;
    if (selection && number >= selection.line && number <= selection.end_line) {
      const start = number === selection.line ? selection.column : 0;
      const end = number === selection.end_line ? selection.end_column : text.length;
      return {
        number,
        text,
        active: true,
        parts: [
          { text: text.slice(0, start) },
          { text: text.slice(start, end), marked: true },
          { text: text.slice(end) },
        ],
      };
    }
    const active =
      !selection &&
      number >= (binding.line || 1) &&
      number <= (binding.end_line || binding.line || 1);
    return { number, text, active, parts: [{ text, marked: active }] };
  });
}

/** Keep distant file content as text blocks; only selected lines need DOM elements. */
export function renderSource(host, source, binding) {
  const fragment = host.ownerDocument.createDocumentFragment();
  let block = "";
  const flush = () => {
    if (block) fragment.append(host.ownerDocument.createTextNode(block));
    block = "";
  };
  for (const row of sourceLines(source, binding)) {
    const prefix = String(row.number).padStart(4) + "  ";
    if (!row.active) {
      block += prefix + row.text + "\n";
      continue;
    }
    flush();
    const line = host.ownerDocument.createElement("span");
    line.dataset.sourceLine = row.number;
    line.append(prefix);
    for (const part of row.parts) {
      if (!part.marked || !part.text) line.append(part.text);
      else {
        const mark = host.ownerDocument.createElement("mark");
        mark.textContent = part.text;
        line.append(mark);
      }
    }
    fragment.append(line, "\n");
  }
  flush();
  host.replaceChildren(fragment);
  return host.querySelector("[data-source-line]");
}
