"""Check the trial's complete browser outcome independently of mapping reports.

The configured native gate can pass while an application interaction fails.
Keep those scopes separate and require both before canonical acceptance.
"""

REQUIRED_CHECKS = frozenset({
    "browser_on", "browser_off", "browser_fault", "upload_and_named_share",
    "revoke_hides_file_but_preserves_repeat_collection",
    "editor_has_no_file_privilege", "independent_board_publish_edit_read_delete",
})


def check_browser_outcome(browser, command, build):
    """Reject partial UI cases, failed commands and foreign build receipts."""
    errors = []
    if browser.get("build_id") != build:
        errors.append("browser build differs from candidate")
    if command.get("exit_code") != 0:
        errors.append("ordinary browser command failed")
    if browser.get("error") or browser.get("exception_type"):
        errors.append("browser retained an execution failure")
    checks = browser.get("checks", {})
    errors.extend("missing browser check: " + name
                  for name in sorted(REQUIRED_CHECKS) if checks.get(name) is not True)
    records = browser.get("recordings", [])
    if len(records) != 2 or len({r.get("id") for r in records}) != 2:
        errors.append("two distinct consecutive recordings are required")
    for record in records:
        if record.get("status") != "stopped" or not record.get("events") or record.get("gaps"):
            errors.append("incomplete ordinary recording: " + str(record.get("id")))
        settlement = record.get("settlement", {})
        if not settlement.get("flushed") or settlement.get("completed", -1) < settlement.get("target", 0):
            errors.append("unsettled stop prefix: " + str(record.get("id")))
    return errors
