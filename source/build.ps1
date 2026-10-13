param([string]$Python = 'python')
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath '.venv\Scripts\python.exe')) {
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw 'Could not create Python virtual environment' }
}
$BuildPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
& $BuildPython -m pip install -r requirements.txt
if ($LASTEXITCODE -ne 0) { throw 'Dependency install failed' }
& $BuildPython make_audio.py
if ($LASTEXITCODE -ne 0) { throw 'Audio generation failed' }
& $BuildPython -m unittest -v test_game
if ($LASTEXITCODE -ne 0) { throw 'Tests failed' }
& $BuildPython -m PyInstaller --noconfirm NeonBreach.spec
if ($LASTEXITCODE -ne 0) { throw 'Build failed' }
Copy-Item -LiteralPath README.md,CREDITS.md,VALIDATION.md -Destination dist\NeonBreach
Copy-Item -LiteralPath licenses -Destination dist\NeonBreach -Recurse -Force
Write-Output 'Ready: dist\NeonBreach\NeonBreach.exe. Keep the _internal folder beside it.'
