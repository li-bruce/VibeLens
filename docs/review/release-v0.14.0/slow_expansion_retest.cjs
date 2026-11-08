// Reproduce slow rendering only in the all-layer browser process.
if (process.argv[1]?.endsWith("test_expansion_relations_browser.mjs")) {
  const { chromium } = require("playwright");
  const launch = chromium.launch.bind(chromium);
  chromium.launch = async (options) => {
    const browser = await launch({
      ...options,
      args: [...(options?.args || []), "--use-angle=swiftshader"],
    });
    const newPage = browser.newPage.bind(browser);
    browser.newPage = async (options) => {
      const page = await newPage(options);
      await (
        await page.context().newCDPSession(page)
      ).send("Emulation.setCPUThrottlingRate", { rate: 6 });
      return page;
    };
    return browser;
  };
}
