# Makes Innovate Assure start automatically when you log in (like your current Task Scheduler setup).
# Run once:  right-click > Run with PowerShell
$start = Join-Path $PSScriptRoot "start.bat"
$action = New-ScheduledTaskAction -Execute "cmd.exe" -Argument "/c `"$start`""
$trigger = New-ScheduledTaskTrigger -AtLogOn
Register-ScheduledTask -TaskName "Innovate Assure" -Action $action -Trigger $trigger -Description "Starts Innovate Assure" -Force | Out-Null
Write-Host "Done. Assure will start at every logon. To allow the team to reach it, allow port 8501 in Windows Firewall."
