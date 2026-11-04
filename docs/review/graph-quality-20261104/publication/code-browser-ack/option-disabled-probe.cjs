/** Isolate option-state inspection; use no application server or external URL. */
const { chromium } = require("playwright");
const { writeFileSync } = require("node:fs");

async function main() {
  const browser = await chromium.launch({
    executablePath:
      process.env.BO_BROWSER_EXECUTABLE ||
      "C:/Program Files/Google/Chrome/Application/chrome.exe",
    headless: true,
  });
  try {
    const page = await browser.newPage();
    await page.setContent(
      '<label>View<select id="labeled"><option value="overview">Overview</option>' +
        '<option value="code" disabled>Code</option></select></label>' +
        '<select id="unlabeled"><option value="overview">Overview</option>' +
        '<option value="code" disabled>Code</option></select>',
    );
    const results = [];
    for (const id of ["labeled", "unlabeled"]) {
      const option = page.locator("#" + id + ' option[value="code"]');
      results.push({
        id,
        optionProperty: await option.evaluate((node) => node.disabled),
        optionAttribute: await option.getAttribute("disabled"),
        optionIsDisabled: await option.isDisabled(),
        selectIsDisabled: await page.locator("#" + id).isDisabled(),
        html: await option.evaluate((node) => node.outerHTML),
      });
    }
    const output =
      JSON.stringify(
        {
          playwright: require("playwright/package.json").version,
          browser: browser.version(),
          results,
        },
        null,
        2,
      ) + "\n";
    if (process.argv[2]) writeFileSync(process.argv[2], output, { flag: "wx" });
    process.stdout.write(output);
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
