# Run from the maintained repository root. Only review output and .validation scratch are written.
$ErrorActionPreference = 'Stop'
$reviewPath = 'docs/review/graph-quality-20261104/trial-audit/source-scope-adoption'
python -B "$reviewPath/run_fixture.py" 2>&1 | Tee-Object -FilePath "$reviewPath/run.log"
if ($LASTEXITCODE -ne 0) { throw "Source-scope fixture failed with exit code $LASTEXITCODE" }
