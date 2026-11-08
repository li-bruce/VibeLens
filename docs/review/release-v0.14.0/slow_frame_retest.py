"""Repeat the genuine renderer checks with 1.4-second frames during capture.

Run from the repository root. Only frame scheduling is delayed; the test still
reads the same real recording, routes, arrow geometry and GPU color buffers.
"""

import runpy
import sys

from playwright.sync_api import Browser

new_page = Browser.new_page


def slow_page(self, *args, **kwargs):
    page = new_page(self, *args, **kwargs)
    page.add_init_script("""(() => {
      const request = window.requestAnimationFrame.bind(window);
      const cancel = window.cancelAnimationFrame.bind(window);
      const pending = new Map();
      let sequence = 0;
      window.requestAnimationFrame = callback => {
        const id = ++sequence, item = {timer: null, frame: null};
        pending.set(id, item);
        item.timer = setTimeout(() => {
          item.frame = request(now => {pending.delete(id); callback(now);});
        }, window.edgeColorProbe?.capture ? 1400 : 0);
        return id;
      };
      window.cancelAnimationFrame = id => {
        const item = pending.get(id);
        if (!item) return;
        clearTimeout(item.timer);
        if (item.frame !== null) cancel(item.frame);
        pending.delete(id);
      };
    })();""")
    return page


Browser.new_page = slow_page
sys.argv = ["tools/test_edge_colors_browser.py", *sys.argv[1:]]
runpy.run_path("tools/test_edge_colors_browser.py", run_name="__main__")
