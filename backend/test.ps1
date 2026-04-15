param(
    [string]$BaseUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"

chcp 65001 | Out-Null
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

Write-Host "==> Testing /health"
Invoke-RestMethod -Uri "$BaseUrl/health" -Method Get | ConvertTo-Json

Write-Host "`n==> Testing /chat (TDEE + macros)"
$body = @{
  user_id = "user-001"
  session_id = "session-001"
  message = "Tinh TDEE va macro cho toi"
  profile_patch = @{
    age = 24
    sex = "male"
    height_cm = 175
    weight_kg = 72
    activity_level = "moderate"
    goal = "muscle_gain"
  }
} | ConvertTo-Json -Depth 5

$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
$response = Invoke-RestMethod -Uri "$BaseUrl/chat" -Method Post -ContentType "application/json; charset=utf-8" -Body $bytes
$response | ConvertTo-Json -Depth 6

Write-Host "`n==> Testing /chat persistence (same user, no profile_patch)"
$persistBody = @{
  user_id = "user-001"
  session_id = "session-002"
  message = "Tinh TDEE cho toi"
} | ConvertTo-Json -Depth 5

$persistBytes = [System.Text.Encoding]::UTF8.GetBytes($persistBody)
$persistResponse = Invoke-RestMethod -Uri "$BaseUrl/chat" -Method Post -ContentType "application/json; charset=utf-8" -Body $persistBytes
$persistResponse | ConvertTo-Json -Depth 6

Write-Host "`n==> Testing /chat (meal guidance)"
$mealBody = @{
  user_id = "user-001"
  session_id = "session-004"
  message = "Goi y lich an cho toi"
} | ConvertTo-Json -Depth 5

$mealBytes = [System.Text.Encoding]::UTF8.GetBytes($mealBody)
$mealResponse = Invoke-RestMethod -Uri "$BaseUrl/chat" -Method Post -ContentType "application/json; charset=utf-8" -Body $mealBytes
$mealResponse | ConvertTo-Json -Depth 8

Write-Host "`n==> Testing /chat (workout planner)"
$workoutBody = @{
  user_id = "user-001"
  session_id = "session-003"
  message = "Lap lich tap cho toi"
  profile_patch = @{
    workout_days_per_week = 4
    train_location = "gym"
    injuries = @("knee")
  }
} | ConvertTo-Json -Depth 5

$workoutBytes = [System.Text.Encoding]::UTF8.GetBytes($workoutBody)
$workoutResponse = Invoke-RestMethod -Uri "$BaseUrl/chat" -Method Post -ContentType "application/json; charset=utf-8" -Body $workoutBytes
$workoutResponse | ConvertTo-Json -Depth 8

Write-Host "`n==> Done"
