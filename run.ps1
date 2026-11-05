$ErrorActionPreference = 'Stop'

$repo = 'https://github.com/sshoman/lwr/archive/refs/heads/main.zip'
$tempRoot = Join-Path $env:TEMP ('shaman-tests-' + [guid]::NewGuid().ToString('N'))
$zipPath = Join-Path $tempRoot 'repo.zip'
$extractPath = Join-Path $tempRoot 'repo'

try {
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null
    Write-Host 'Downloading Shaman experiments from GitHub...'
    Invoke-WebRequest -Uri $repo -OutFile $zipPath
    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractPath -Force

    $repoRoot = Get-ChildItem -LiteralPath $extractPath -Directory | Select-Object -First 1
    if (-not $repoRoot) { throw 'Could not find the downloaded repository folder.' }

    $bundle = Join-Path $repoRoot.FullName 'tests/test_001_refutation_transfer/source_bundle.zip'
    if (-not (Test-Path $bundle)) { throw 'Test 001 source bundle is missing from the downloaded repository.' }
    Expand-Archive -LiteralPath $bundle -DestinationPath $repoRoot.FullName -Force

    $runner = Join-Path $repoRoot.FullName 'tests/test_001_refutation_transfer/run.py'
    if (-not (Test-Path $runner)) { throw 'Test 001 runner is missing from the extracted source bundle.' }

    $runStamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $outputDir = Join-Path (Get-Location) ("shaman-results/test_001/run_$runStamp")
    Push-Location $repoRoot.FullName
    try {
        $py = Get-Command py -ErrorAction SilentlyContinue
        if ($py) {
            & $py.Source -3 -m tests.test_001_refutation_transfer.run --out $outputDir
        } else {
            $python = Get-Command python -ErrorAction SilentlyContinue
            if (-not $python) { throw 'Python 3.10 or newer is required. Install Python, then run this same command again.' }
            & $python.Source -m tests.test_001_refutation_transfer.run --out $outputDir
        }
    } finally {
        Pop-Location
    }

    if ($LASTEXITCODE -ne 0) { throw "Test 001 exited with code $LASTEXITCODE. Check the partial report in shaman-results/test_001." }
} finally {
    if (Test-Path $tempRoot) { Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue }
}
