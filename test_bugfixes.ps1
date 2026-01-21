# Manual API Test Script
# Tests the 3 bug fixes

Write-Host "`n=== Bug Fix Testing ===" -ForegroundColor Cyan
Write-Host "Testing against: http://localhost:9000/analyze`n"

# Test 1: Vietnamese column names
Write-Host "Test 1: Vietnamese Column Names (locale=vi)" -ForegroundColor Yellow
$test1 = @"
{
  "input": "Tỷ lệ đạt kế hoạch FAC01 tháng 1/2026",
  "context": {
    "factoryCode": "FAC01",
    "locale": "vi"
  }
}
"@

try {
    $response1 = Invoke-RestMethod -Uri "http://localhost:9000/analyze" `
        -Method POST `
        -Headers @{ "Authorization" = "Bearer dev-key-123"; "Content-Type" = "application/json; charset=utf-8" } `
        -Body ([System.Text.Encoding]::UTF8.GetBytes($test1)) `
        -TimeoutSec 30
    
    Write-Host "✓ Status: 200 OK" -ForegroundColor Green
    Write-Host "✓ Rows returned: $($response1.planner_result.data.Count)"
    
    if ($response1.planner_result.data.Count -gt 0) {
        $row = $response1.planner_result.data[0]
        $vnColumns = $row.PSObject.Properties | Where-Object { $_.Name -match "lệ|suất|OEE" -and $_.Name -notmatch "Rate|percent" }
        Write-Host "✓ Vietnamese columns: $($vnColumns.Count)" -ForegroundColor Green
        $vnColumns | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor Cyan }
    }
} catch {
    Write-Host "✗ FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 2: English column names
Write-Host "`nTest 2: English Column Names (locale=en)" -ForegroundColor Yellow
$test2 = @"
{
  "input": "Achievement rate FAC01 January 2026",
  "context": {
    "factoryCode": "FAC01",
    "locale": "en"
  }
}
"@

try {
    $response2 = Invoke-RestMethod -Uri "http://localhost:9000/analyze" `
        -Method POST `
        -Headers @{ "Authorization" = "Bearer dev-key-123"; "Content-Type" = "application/json; charset=utf-8" } `
        -Body ([System.Text.Encoding]::UTF8.GetBytes($test2)) `
        -TimeoutSec 30
    
    Write-Host "✓ Status: 200 OK" -ForegroundColor Green
    Write-Host "✓ Rows returned: $($response2.planner_result.data.Count)"
    
    if ($response2.planner_result.data.Count -gt 0) {
        $row = $response2.planner_result.data[0]
        $enColumns = $row.PSObject.Properties | Where-Object { $_.Name -match "Achievement|Efficiency|OEE" -and $_.Name -notmatch "Rate$|percent" }
        Write-Host "✓ English columns: $($enColumns.Count)" -ForegroundColor Green
        $enColumns | ForEach-Object { Write-Host "  - $($_.Name)" -ForegroundColor Cyan }
    }
} catch {
    Write-Host "✗ FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

# Test 3: Follow-up query detection
Write-Host "`nTest 3: Follow-up Query Detection" -ForegroundColor Yellow
$test3 = @"
{
  "input": "thế còn tháng 1/2026",
  "context": {
    "factoryCode": "FAC01",
    "locale": "vi"
  }
}
"@

try {
    $response3 = Invoke-RestMethod -Uri "http://localhost:9000/analyze" `
        -Method POST `
        -Headers @{ "Authorization" = "Bearer dev-key-123"; "Content-Type" = "application/json; charset=utf-8" } `
        -Body ([System.Text.Encoding]::UTF8.GetBytes($test3)) `
        -TimeoutSec 30
    
    Write-Host "✓ Status: 200 OK" -ForegroundColor Green
    Write-Host "✓ Intent: $($response3.intent.intent)"
    
    if ($response3.intent.intent -ne "chat") {
        Write-Host "✓ PASS: Routed as data request (not chat)" -ForegroundColor Green
    } else {
        Write-Host "✗ FAIL: Routed to chat instead of data query" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ FAILED: $($_.Exception.Message)" -ForegroundColor Red
}

Write-Host "`n=== Test Complete ===" -ForegroundColor Cyan
