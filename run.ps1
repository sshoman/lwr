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

    # ZIP permits a comment after its end record. Find the EOCD and trim only
    # bytes beyond the declared comment, avoiding parser failures from stray
    # trailing data in a stored archive.
    $bundleBytes = [System.IO.File]::ReadAllBytes($bundle)
    $eocd = -1
    $minOffset = [Math]::Max(0, $bundleBytes.Length - 65557)
    for ($i = $bundleBytes.Length - 22; $i -ge $minOffset; $i--) {
        if ($bundleBytes[$i] -eq 0x50 -and $bundleBytes[$i + 1] -eq 0x4b -and
            $bundleBytes[$i + 2] -eq 0x05 -and $bundleBytes[$i + 3] -eq 0x06) {
            $eocd = $i
            break
        }
    }
    if ($eocd -lt 0) { throw 'Test 001 source bundle is not a valid ZIP archive.' }
    $commentLength = [BitConverter]::ToUInt16($bundleBytes, $eocd + 20)
    $validLength = $eocd + 22 + $commentLength
    if ($validLength -gt $bundleBytes.Length) { throw 'Test 001 source bundle has a truncated ZIP comment.' }
    if ($validLength -lt $bundleBytes.Length) {
        $cleanBundle = Join-Path $tempRoot 'source_bundle_clean.zip'
        $cleanBytes = New-Object byte[] $validLength
        [Array]::Copy($bundleBytes, 0, $cleanBytes, 0, $validLength)
        [System.IO.File]::WriteAllBytes($cleanBundle, $cleanBytes)
        $bundle = $cleanBundle
    }

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
