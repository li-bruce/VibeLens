"""Compare a normal coding iteration with real pre-iteration source and data.

Use immutable accepted snapshots, fresh source hashes, the current code index and
read-only SQLite facts. Constraint probes run only on a disposable database copy.
"""

from contextlib import closing
import gzip
import hashlib
import json
from pathlib import Path
import sqlite3
import sys
import tempfile
import zipfile

ROOT = Path(__file__).resolve().parents[1]
TRIAL = ROOT.parent / "VibeLensTrials/lifecycle-dialogue-20261031"
BASE = ROOT / "docs/review/dialogue-acceptance-20261031/iteration/original-v1-ready"
sys.path.insert(0, str(ROOT / "skills/vibelens/scripts"))
from bo_observer.graph.behavior_model import capture, digest


def read(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def dictionaries(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from dictionaries(child)
    elif isinstance(value, list):
        for child in value:
            yield from dictionaries(child)


def main():
    output = ROOT / "docs/review/dialogue-acceptance-20261031/iteration" / sys.argv[1]
    output.mkdir(parents=True, exist_ok=True)
    target = output / "structure-and-data-update.json"
    if target.exists():
        raise ValueError("Retain old results and use a new phase for a rerun")
    with gzip.open(BASE / "view.json.gz", "rt", encoding="utf-8") as stream:
        before = json.load(stream)
    before_source = read(BASE / "snapshot.json")
    legacy = read(BASE / "authoritative-rows.json")
    old_columns = read(BASE / "authoritative-columns.json")
    old_structure = read(BASE / "sqlite-structure.json")
    with zipfile.ZipFile(BASE / "source-and-contracts.zip") as archive:
        before_code = json.loads(archive.read(".stategraph/code-graph.json"))
        before_contracts = {
            name: json.loads(archive.read(name))
            for name in ("sync.json", "mapping.json", "acceptance.json", "whitebox.json")
        }
    model = read(TRIAL / "bo_stategraph/project.json")["model"]
    code = read(TRIAL / ".stategraph/code-graph.json")
    active = read(TRIAL / ".stategraph/active.json")
    accepted = read(TRIAL / active["change"] / "accepted.json")
    checks = []
    result = {
        "phase": sys.argv[1],
        "before_build": before["manifest"]["build_id"],
        "accepted": accepted,
        "checks": checks,
    }

    def check(name, passed, facts):
        checks.append({"name": name, "passed": bool(passed), "facts": facts})
        assert passed, name

    try:
        current_verification = read(TRIAL / active["change"] / "verification.json")
        current_build = capture(TRIAL, model)["build_id"]
        check(
            "Actual source and accepted verification identify the same current build",
            current_build == accepted["build_id"]
            and digest(current_verification) == accepted["verification_hash"]
            and current_verification["valid"],
            {"source_build": current_build, "accepted": accepted},
        )
        check(
            "A new accepted build follows the business request",
            accepted["build_id"] != result["before_build"],
            active,
        )
        old_snapshots = [
            before_source,
            read(
                ROOT
                / "docs/review/dialogue-acceptance-20261031/iteration/original-v1-before-browser/snapshot.json"
            ),
        ]
        preserved = {}
        for snapshot in old_snapshots:
            for name, expected in snapshot["source_hashes"].items():
                if name.endswith("/baseline.json"):
                    preserved[name] = (
                        hashlib.sha256((TRIAL / name).read_bytes()).hexdigest() == expected
                    )
        check(
            "Earlier acceptance baselines remain immutable",
            bool(preserved) and all(preserved.values()),
            preserved,
        )
        removed = []
        for name, fields in (
            ("sync.json", ("probe_modes", "required_probes", "required_runtime_probes")),
            ("mapping.json", ("cases", "modes", "fields")),
            ("acceptance.json", ("checks",)),
            ("whitebox.json", ("checks",)),
        ):
            current = read(TRIAL / name)
            for field in fields:
                for item in before_contracts[name].get(field, []):
                    if item not in current.get(field, []):
                        removed.append({"file": name, "field": field, "item": item})
        check("Protected probes, cases, fields and expectations are retained", not removed, removed)
        current_features = {item["id"]: item for item in model["implementation"]["features"]}
        removed_coverage = []
        for feature in before["model"]["implementation"]["features"]:
            current = current_features.get(feature["id"], {})
            for field in ("nodes", "sources", "parameters", "cases", "requirements"):
                for item in feature.get(field, []):
                    if item not in current.get(field, []):
                        removed_coverage.append(
                            {"feature": feature["id"], "field": field, "item": item}
                        )
        check(
            "Previously accepted feature sources, parameters and witnesses remain required",
            not removed_coverage,
            removed_coverage,
        )
        old_states, states = set(before["model"]["machine"]["values"]), set(
            model["machine"]["values"]
        )
        check(
            "The state declaration adds the new waiting branch and retains original states",
            old_states < states,
            {"before": sorted(old_states), "after": sorted(states)},
        )
        old_nodes = {node["id"] for node in before["model"]["nodes"]}
        nodes = {node["id"] for node in model["nodes"]}
        fixed = {
            "login",
            "upload",
            "share",
            "review",
            "download",
            "pending",
            "granted",
            "rejected",
            "cancelled",
            "revoked",
        }
        check(
            "Core business/state identities stay stable",
            fixed <= old_nodes & nodes,
            {"added": sorted(nodes - old_nodes), "removed": sorted(old_nodes - nodes)},
        )
        check(
            "The independent code index updates with the source",
            code["revision"] != before_code["revision"] and not code["errors"],
            {
                "before": before_code["revision"],
                "after": code["revision"],
                "nodes": len(code["nodes"]),
                "edges": len(code["edges"]),
                "errors": code["errors"],
            },
        )
        changed = [
            name
            for name, digest in before_source["source_hashes"].items()
            if (TRIAL / name).is_file()
            and hashlib.sha256((TRIAL / name).read_bytes()).hexdigest() != digest
        ]
        check(
            "Native application sources change",
            any(name.startswith("app/") for name in changed),
            changed,
        )
        old_policy, policy = before["model"]["policy"], model["policy"]
        old_operations = {item["id"]: item for item in old_policy["operations"]}
        operations = {item["id"]: item for item in policy["operations"]}
        rule_nodes = {item["id"] for item in policy["nodes"]}
        policy_cases_removed = {
            name: sorted(set(item["cases"]) - set(operations.get(name, {}).get("cases", [])))
            for name, item in old_operations.items()
            if set(item["cases"]) - set(operations.get(name, {}).get("cases", []))
        }
        check(
            "New policy branches update the declaration while retaining shared rules and old cases",
            policy != old_policy
            and {"return_share", "resubmit_share", "supplement_details"} <= set(operations)
            and {item["id"] for item in old_policy["nodes"]} <= rule_nodes
            and all(item["root"] in rule_nodes for item in operations.values())
            and not policy_cases_removed,
            {"operations": sorted(operations), "removed_cases": policy_cases_removed},
        )
        database = (TRIAL / "data/application.sqlite3").as_uri() + "?mode=ro"
        with closing(sqlite3.connect(database, uri=True)) as connection:
            connection.row_factory = sqlite3.Row
            for name, rows in legacy["tables"].items():
                actual = {
                    row["id"]: dict(row) for row in connection.execute(f'SELECT * FROM "{name}"')
                }
                missing = [row["id"] for row in rows if row["id"] not in actual]
                differences = [
                    {
                        "id": row["id"],
                        "field": field,
                        "before": value,
                        "after": actual[row["id"]].get(field),
                    }
                    for row in rows
                    if row["id"] in actual
                    for field, value in row.items()
                    if actual[row["id"]].get(field) != value
                ]
                check(
                    "Existing " + name + " survive migration unchanged",
                    not missing and not differences,
                    {"old_rows": len(rows), "missing": missing, "differences": differences},
                )
            structure = [
                dict(zip(("type", "name", "table", "sql"), row))
                for row in connection.execute(
                    "SELECT type, name, tbl_name, sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY type, name"
                )
            ]
            check(
                "Native database structure follows the new state/data model",
                structure != old_structure,
                {"before": old_structure, "after": structure},
            )
            names = [
                row[0]
                for row in connection.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
                )
            ]
            columns = {
                name: {
                    row["name"]
                    for row in connection.execute(
                        'PRAGMA table_info("' + name.replace('"', '""') + '")'
                    )
                }
                for name in names
            }
            added = {
                name: sorted(fields - set(old_columns.get(name, [])))
                for name, fields in columns.items()
                if fields - set(old_columns.get(name, []))
            }
            catalog = read(TRIAL / "bo_stategraph/database-catalog.json")
            resources = [
                item
                for item in dictionaries(catalog["catalogs"])
                if "fields" in item and "name" in item
            ]

            def field_names(resource):
                fields = resource["fields"]
                if isinstance(fields, dict):
                    return set(fields)
                return {field["name"] if isinstance(field, dict) else field for field in fields}

            missing = {
                name: fields
                for name, fields in added.items()
                if not any(
                    item["name"] == name and set(fields) <= field_names(item) for item in resources
                )
            }
            check(
                "Fresh database metadata contains any new native fields/tables",
                not missing,
                {"added": added, "missing": missing},
            )
            check(
                "Database metadata includes the new state constraint",
                all(state in json.dumps(catalog["catalogs"]) for state in states - old_states),
                sorted(states - old_states),
            )
            with tempfile.TemporaryDirectory(
                prefix="dialogue-db-constraints-", dir=ROOT / ".validation"
            ) as directory:
                with closing(sqlite3.connect(Path(directory) / "copy.sqlite3")) as copy:
                    connection.backup(copy)
                    copy.execute("PRAGMA foreign_keys=ON")
                    sample = legacy["tables"]["shares"][0]["id"]
                    for name, sql, value in (
                        ("state enum", "UPDATE shares SET state=? WHERE id=?", "unmodeled-state"),
                        (
                            "recipient foreign key",
                            "UPDATE shares SET recipient_id=? WHERE id=?",
                            "missing-user",
                        ),
                    ):
                        rejected = False
                        try:
                            copy.execute(sql, (value, sample))
                            copy.commit()
                        except sqlite3.IntegrityError:
                            rejected = True
                        finally:
                            copy.rollback()
                        check(
                            "Existing native constraint retained: " + name,
                            rejected,
                            {"isolated_copy": True},
                        )
        missing_blobs, changed_blobs = [], []
        for identifier, expected in legacy["blobs"].items():
            path = (TRIAL / "data/files" / identifier).resolve()
            path.relative_to((TRIAL / "data/files").resolve())
            if not path.is_file():
                missing_blobs.append(identifier)
            elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                changed_blobs.append(identifier)
        check(
            "Existing uploaded bytes survive unchanged",
            not missing_blobs and not changed_blobs,
            {"files": len(legacy["blobs"]), "missing": missing_blobs, "changed": changed_blobs},
        )
        result["passed"] = True
    except Exception as error:
        result.update(passed=False, error=repr(error))
    target.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(
        json.dumps(
            {"passed": result["passed"], "checks": len(checks), "error": result.get("error")}
        )
    )
    raise SystemExit(0 if result["passed"] else 1)


if __name__ == "__main__":
    main()
