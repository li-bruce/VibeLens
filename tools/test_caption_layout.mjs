/** Measured caption fitting keeps source text intact across scripts and scales. */
import assert from "node:assert/strict";
import { fitCaption } from "../skills/vibelens/assets/stategraph-viewer/caption-layout.js";

const measure = (value) =>
  Array.from(value).reduce((n, c) => n + (/[\u0000-\u007f]/u.test(c) ? 1 : 2), 0);
for (const raw of [
  "上传文件并选择审核同事",
  "Uploader and designated reviewer can download",
  "SharingService.authorize_designated_recipient",
  "Read 📁 and share 🔗 safely",
]) {
  const result = fitCaption(raw, { maxWidth: 12, maxLines: 2, measure });
  assert.ok(result.split("\n").length <= 2);
  assert.ok(result.split("\n").every((line) => measure(line) <= 12));
  assert.ok(
    !/[\ud800-\udbff](?![\udc00-\udfff])|(?<![\ud800-\udbff])[\udc00-\udfff]/u.test(result),
  );
}
assert.equal(fitCaption("read", { maxWidth: 4, measure }), "read");
assert.equal(fitCaption("上传", { maxWidth: 1, maxLines: 1, measure }), "");
assert.equal(fitCaption("a", { maxWidth: 0, measure }), "");
assert.equal(fitCaption("a", { maxWidth: 10, maxLines: 0, measure }), "");
assert.equal(fitCaption("one two three", { maxWidth: 7, measure }), "one two\nthree");
console.log("Measured caption bounds passed");
