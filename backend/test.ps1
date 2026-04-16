param(
    [string]$NodeUrl   = "http://127.0.0.1:3000",
    [string]$ChatbotUrl = "http://127.0.0.1:8000"
)

$ErrorActionPreference = "Stop"
chcp 65001 | Out-Null
$OutputEncoding = [System.Text.UTF8Encoding]::new()
[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new()

# ─────────────────────────────────────────────
# Helper
# ─────────────────────────────────────────────
function Print-Header($title) {
    Write-Host ""
    Write-Host "=" * 56
    Write-Host "  $title"
    Write-Host "=" * 56
}

# ─────────────────────────────────────────────
# 1. Node.js backend health
# ─────────────────────────────────────────────
Print-Header "1. Node.js backend /health"
Invoke-RestMethod -Uri "$NodeUrl/health" -Method Get | ConvertTo-Json

# ─────────────────────────────────────────────
# 2. Python chatbot health
# ─────────────────────────────────────────────
Print-Header "2. Python chatbot /health"
Invoke-RestMethod -Uri "$ChatbotUrl/health" -Method Get | ConvertTo-Json

# ─────────────────────────────────────────────
# 3. AUTH ROUTES: Register & Login & Update Profile
# ─────────────────────────────────────────────
Print-Header "3. Auth: Register test user"
$timestamp = [DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
$email = "testuser_$timestamp@example.com"
$password = "TestPass123!"

$registerBody = @{
    email     = $email
    username  = "testuser_$timestamp"
    password  = $password
    firstName = "Test"
    lastName  = "User"
} | ConvertTo-Json

$registerResponse = Invoke-RestMethod `
    -Uri "$NodeUrl/api/auth/register" `
    -Method Post `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($registerBody))

$userId = $registerResponse.user.id
Write-Host "Registered user_id : $userId"

Print-Header "Auth: Login test user"
$loginBody = @{
    email    = $email
    password = $password
} | ConvertTo-Json

$loginResponse = Invoke-RestMethod `
    -Uri "$NodeUrl/api/auth/login" `
    -Method Post `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($loginBody))

$token = $loginResponse.token
Write-Host "Logged in. Token: $($token.Substring(0, 30))..."
$headers = @{ Authorization = "Bearer $token" }

Print-Header "Auth: Update Profile"
$updateProfileBody = @{
    bio = "Trying to get fit"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "$NodeUrl/api/auth/profile" `
    -Method Put `
    -Headers $headers `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($updateProfileBody)) | ConvertTo-Json

# ─────────────────────────────────────────────
# 4. CHAT ROUTES: Python Chat endpoints
# ─────────────────────────────────────────────
Print-Header "4. Chat: TDEE + macros (profile patch)"
$chatBody = @{
    user_id    = $userId
    session_id = "session-tdee-$timestamp"
    message    = "Tinh TDEE va macro cho toi"
    profile_patch = @{
        age           = 25
        sex           = "male"
        height_cm     = 180
        weight_kg     = 75
        activity_level = "moderate"
        goal          = "muscle_gain"
    }
} | ConvertTo-Json -Depth 5

$chatResponse = Invoke-RestMethod `
    -Uri "$ChatbotUrl/chat" `
    -Method Post `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($chatBody))
Write-Host "Chat Response: $($chatResponse.reply.Substring(0, [math]::Min($chatResponse.reply.Length, 100)))..."

Print-Header "Chat: workout plan"
$workoutBody = @{
    user_id    = $userId
    session_id = "session-workout-$timestamp"
    message    = "Lap lich tap cho toi"
    profile_patch = @{
        workout_days_per_week = 3
        train_location        = "gym"
    }
} | ConvertTo-Json -Depth 5

$workoutResponse = Invoke-RestMethod `
    -Uri "$ChatbotUrl/chat" `
    -Method Post `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($workoutBody))
Write-Host "Chat Response: $($workoutResponse.reply.Substring(0, [math]::Min($workoutResponse.reply.Length, 100)))..."


# ─────────────────────────────────────────────
# 5. CHAT ROUTES: Node.js History Endpoints
# ─────────────────────────────────────────────
Print-Header "5. Node.js Chat Sessions"
$sessionsResponse = Invoke-RestMethod `
    -Uri "$NodeUrl/api/chat/sessions" `
    -Method Get `
    -Headers $headers 

$sessionsResponse | ConvertTo-Json -Depth 4
$testSessionId = $sessionsResponse.sessions[0].sessionId

Print-Header "Node.js Chat History"
Invoke-RestMethod `
    -Uri "$NodeUrl/api/chat/history?session_id=$testSessionId" `
    -Method Get `
    -Headers $headers | ConvertTo-Json -Depth 4

Print-Header "Node.js Chat Delete Session"
Invoke-RestMethod `
    -Uri "$NodeUrl/api/chat/sessions/$testSessionId" `
    -Method Delete `
    -Headers $headers | ConvertTo-Json -Depth 4


# ─────────────────────────────────────────────
# 6. FORUM ROUTES
# ─────────────────────────────────────────────
Print-Header "6. Forum: Create Post"
$postBody = @{
    title   = "My first workout program"
    content = "Does this look good for a beginner?"
} | ConvertTo-Json

$postResponse = Invoke-RestMethod `
    -Uri "$NodeUrl/api/forum" `
    -Method Post `
    -Headers $headers `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($postBody))

$postId = $postResponse.post.id
$postResponse | ConvertTo-Json -Depth 5

Print-Header "Forum: Add Comment"
$commentBody = @{
    content = "Looks good man!"
} | ConvertTo-Json

Invoke-RestMethod `
    -Uri "$NodeUrl/api/forum/$postId/comments" `
    -Method Post `
    -Headers $headers `
    -ContentType "application/json; charset=utf-8" `
    -Body ([System.Text.Encoding]::UTF8.GetBytes($commentBody)) | ConvertTo-Json -Depth 5

Print-Header "Forum: Like Post"
Invoke-RestMethod `
    -Uri "$NodeUrl/api/forum/$postId/like" `
    -Method Post `
    -Headers $headers | ConvertTo-Json

Print-Header "Forum: Get All Posts"
Invoke-RestMethod `
    -Uri "$NodeUrl/api/forum" `
    -Method Get | ConvertTo-Json -Depth 5

# ─────────────────────────────────────────────
# 7. WORKOUT ROUTES (Assuming public GET exercises)
# ─────────────────────────────────────────────
Print-Header "7. Workouts: Get Exercises Catalog"
Invoke-RestMethod `
    -Uri "$NodeUrl/api/workouts/exercises" `
    -Method Get | ConvertTo-Json -Depth 5

# ─────────────────────────────────────────────
# 8. VERIFY PROFILE
# ─────────────────────────────────────────────
Print-Header "8. Final Verification: Get Profile"
Invoke-RestMethod `
    -Uri "$NodeUrl/api/auth/profile" `
    -Method Get `
    -Headers $headers | ConvertTo-Json

Write-Host ""
Write-Host "==> All route tests passed!"
