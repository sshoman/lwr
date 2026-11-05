$ErrorActionPreference = 'Stop'

$baseUrl = 'https://raw.githubusercontent.com/sshoman/lwr/main/tests/test_001_refutation_transfer/source_parts/'
$parts = @('part01.b64', 'part02.b64', 'part03.b64', 'part04.b64', 'part05.b64', 'part06.b64', 'part07.b64')
$expectedLength = 14076
$expectedSha256 = 'd75419f8f4631cc181e00474993457f49c4ae057cfff36efdfefee7a9a69c1f5'

$tempRoot = Join-Path $env:TEMP ('shaman-test001-' + [guid]::NewGuid().ToString('N'))
$extractPath = Join-Path $tempRoot 'runner'
$zipPath = Join-Path $tempRoot 'runner.zip'

try {
    New-Item -ItemType Directory -Path $tempRoot -Force | Out-Null

    $encoded = New-Object System.Text.StringBuilder
    foreach ($part in $parts) {
        $partPath = Join-Path $tempRoot $part
        Write-Host "Fetching $part from GitHub..."
        Invoke-WebRequest -Uri ($baseUrl + $part) -OutFile $partPath
        $chunk = [System.IO.File]::ReadAllText($partPath).Trim()
        if ($chunk -notmatch '^[A-Za-z0-9+/]+={0,2}$') {
            throw "Downloaded source part $part contains invalid base64 characters."
        }
        [void]$encoded.Append($chunk)
    }

    $base64 = $encoded.ToString()
    if ($base64.Length -ne $expectedLength) {
        throw "Source length check failed. Expected $expectedLength base64 characters, received $($base64.Length)."
    }

    $archiveBytes = [Convert]::FromBase64String($base64)
    [System.IO.File]::WriteAllBytes($zipPath, $archiveBytes)
    $actualSha256 = (Get-FileHash -LiteralPath $zipPath -Algorithm SHA256).Hash.ToLowerInvariant()
    if ($actualSha256 -ne $expectedSha256) {
        throw "Source integrity check failed. The downloaded runner does not match the published test."
    }

    Expand-Archive -LiteralPath $zipPath -DestinationPath $extractPath -Force
    $runner = Join-Path $extractPath 'run.py'
    if (-not (Test-Path $runner)) {
        throw 'Test 001 runner was not found inside the verified archive.'
    }

    # Gemini 3.8 no longer accepts deprecated sampling parameters.
    # Keep the archive checksum check above intact, then patch the extracted
    # temporary runner before execution.
    $runnerSource = [System.IO.File]::ReadAllText($runner)
    $deprecatedTemperature = [regex]::Matches($runnerSource, '(?m)^\s*"temperature":\s*0\.1,\r?\n')
    if ($deprecatedTemperature.Count -ne 1) {
        throw "Expected exactly one deprecated Gemini 3.8 temperature setting; found $($deprecatedTemperature.Count)."
    }
    $runnerSource = [regex]::Replace($runnerSource, '(?m)^\s*"temperature":\s*0\.1,\r?\n', '')
    [System.IO.File]::WriteAllText($runner, $runnerSource, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host 'Applied Gemini 3.8 compatibility fix: removed deprecated temperature parameter.'

    $runStamp = Get-Date -Format 'yyyyMMdd_HHmmss'
    $outputDir = Join-Path (Get-Location) ("shaman-results/test_001/run_$runStamp")

    $py = Get-Command py -ErrorAction SilentlyContinue
    if ($py) {
        & $py.Source -3 $runner --out $outputDir
    } else {
        $python = Get-Command python -ErrorAction SilentlyContinue
        if (-not $python) {
            throw 'Python 3.10 or newer is required. Install Python and run the same command again.'
        }
        & $python.Source $runner --out $outputDir
    }

    if ($LASTEXITCODE -ne 0) {
        throw "Test 001 exited with code $LASTEXITCODE. Any partial report is in $outputDir."
    }
} finally {
    if (Test-Path $tempRoot) {
        Remove-Item -LiteralPath $tempRoot -Recurse -Force -ErrorAction SilentlyContinue
    }
}
