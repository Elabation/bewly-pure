$ErrorActionPreference = 'Stop'
Push-Location $PSScriptRoot
try {
    & python -X utf8 engine/publish_discovery.py
    if ($LASTEXITCODE -ne 0) { throw 'Review build failed.' }
    & python -X utf8 engine/serve_discovery.py
} finally {
    Pop-Location
}
