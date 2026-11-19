$ErrorActionPreference = "Stop"
python -m faro_risk.cli @args
exit $LASTEXITCODE
