/** Keep the earlier teaching fixture addressable while the native trial leads. */
if (new URLSearchParams(location.search).get("story") === "legacy") await import("./case.mjs");
else await import("./forest-story.mjs");
