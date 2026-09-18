# Creates a "Persian Lyric Sync" shortcut on the desktop pointing at the packaged app.
# Build first: uv run pyinstaller PersianLyricSync.spec --noconfirm
$root = Split-Path -Parent $PSScriptRoot
$exe = Join-Path $root "dist\PersianLyricSync\PersianLyricSync.exe"
if (-not (Test-Path $exe)) { throw "Not built yet: $exe" }

$desktop = [Environment]::GetFolderPath("Desktop")
$link = Join-Path $desktop "Persian Lyric Sync.lnk"
$shell = New-Object -ComObject WScript.Shell
$shortcut = $shell.CreateShortcut($link)
$shortcut.TargetPath = $exe
$shortcut.WorkingDirectory = Split-Path -Parent $exe
$shortcut.IconLocation = "$exe,0"
$shortcut.Description = "Persian lyric video maker"
$shortcut.Save()
Write-Output "Shortcut: $link"
