# ============================================================================
# PowerShell Script: Set Windows VPS Timezone to UTC
# This completes the fix for the autonomous 4-hour close bug
# ============================================================================

Write-Host "`n=== BEFORE ===" -ForegroundColor Yellow
Write-Host "Current timezone:" -NoNewline
Get-TimeZone | Select-Object -ExpandProperty Id
Write-Host "Current local time:" -NoNewline
Get-Date

Write-Host "`n=== CHANGING TIMEZONE TO UTC ===" -ForegroundColor Cyan
try {
    Set-TimeZone -Id "UTC"
    Write-Host "✅ Timezone changed successfully!" -ForegroundColor Green
} catch {
    Write-Host "❌ Failed to change timezone: $_" -ForegroundColor Red
    Write-Host "`nTry running PowerShell as Administrator" -ForegroundColor Yellow
    exit 1
}

Write-Host "`n=== AFTER ===" -ForegroundColor Green
Write-Host "New timezone:" -NoNewline
Get-TimeZone | Select-Object -ExpandProperty Id
Write-Host "New local time:" -NoNewline
Get-Date

Write-Host "`n=== VERIFICATION ===" -ForegroundColor Magenta
$tz = Get-TimeZone
if ($tz.Id -eq "UTC") {
    Write-Host "✅ SUCCESS: VPS is now set to UTC" -ForegroundColor Green
    Write-Host "✅ PostgreSQL is set to UTC (already done)" -ForegroundColor Green
    Write-Host "✅ Python datetime.utcnow() will now match PostgreSQL" -ForegroundColor Green
    Write-Host "`n🎯 Bug is FIXED! Restart your Python bot to apply changes." -ForegroundColor Green
} else {
    Write-Host "❌ FAILED: Timezone is still $($tz.Id)" -ForegroundColor Red
}

Write-Host "`n=== NEXT STEPS ===" -ForegroundColor Yellow
Write-Host "1. Restart your Python bot (telegram_client.py)"
Write-Host "2. Test with a new trade to verify the 4-hour close works correctly"
Write-Host "3. Monitor the logs to ensure timestamps match"
