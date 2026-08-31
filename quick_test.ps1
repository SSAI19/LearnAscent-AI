$baseURL = "http://127.0.0.1:8000/api"
$testEmail = "test-$(Get-Date -f 'yyyyMMddHHmmss')@example.com"
$testPassword = "test123"

Write-Host "Testing LearnAscent AI Phase A Backend API" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host ""

# Test 1: Signup
Write-Host "1. Testing POST /auth/signup..." -ForegroundColor Yellow
$signupBody = @{
    email = $testEmail
    password = $testPassword
} | ConvertTo-Json

try {
    $signup = Invoke-WebRequest -Uri "$baseURL/auth/signup" `
        -Method POST `
        -ContentType "application/json" `
        -Body $signupBody `
        -UseBasicParsing
    $signupResponse = $signup.Content | ConvertFrom-Json
    $token = $signupResponse.access_token
    $userId = $signupResponse.user_id
    Write-Host "   ✓ Signup successful" -ForegroundColor Green
}
catch {
    Write-Host "   ✗ Signup failed: $_" -ForegroundColor Red
    exit 1
}

# Test 2: Get me
Write-Host "2. Testing GET /auth/me..." -ForegroundColor Yellow
try {
    $me = Invoke-WebRequest -Uri "$baseURL/auth/me" `
        -Method GET `
        -Headers @{ "Authorization" = "Bearer $token" } `
        -UseBasicParsing
    $meResponse = $me.Content | ConvertFrom-Json
    Write-Host "   ✓ Get current user successful" -ForegroundColor Green
}
catch {
    Write-Host "   ✗ Get current user failed: $_" -ForegroundColor Red
    exit 1
}

# Test 3: Create profile
Write-Host "3. Testing POST /learner/profile..." -ForegroundColor Yellow
$profileBody = @{
    name = "Test Learner"
    experience_level = "beginner"
    target_career_code = "15-2051.00"
    target_career_title = "Data Scientists"
    available_minutes_per_day = 30
    target_duration_weeks = 12
    known_tools = @("Python")
} | ConvertTo-Json

try {
    $profile = Invoke-WebRequest -Uri "$baseURL/learner/profile" `
        -Method POST `
        -ContentType "application/json" `
        -Headers @{ "Authorization" = "Bearer $token" } `
        -Body $profileBody `
        -UseBasicParsing
    $profileResponse = $profile.Content | ConvertFrom-Json
    Write-Host "   ✓ Create learner profile successful" -ForegroundColor Green
    Write-Host "     Assessment Status: $($profileResponse.assessment_status)" -ForegroundColor Green
}
catch {
    Write-Host "   ✗ Create learner profile failed: $_" -ForegroundColor Red
    exit 1
}

# Test 4: Skill gap
Write-Host "4. Testing POST /engines/skill-gap..." -ForegroundColor Yellow
try {
    $gap = Invoke-WebRequest -Uri "$baseURL/engines/skill-gap" `
        -Method POST `
        -ContentType "application/json" `
        -Headers @{ "Authorization" = "Bearer $token" } `
        -Body '{"source":"essential_skills"}' `
        -UseBasicParsing
    $gapResponse = $gap.Content | ConvertFrom-Json
    Write-Host "   ✓ Skill gap analysis successful" -ForegroundColor Green
    Write-Host "     Gaps found: $($gapResponse.Count)" -ForegroundColor Green
}
catch {
    Write-Host "   ✗ Skill gap failed: $_" -ForegroundColor Red
    exit 1
}

# Test 5: Readiness
Write-Host "5. Testing POST /engines/readiness..." -ForegroundColor Yellow
try {
    $readiness = Invoke-WebRequest -Uri "$baseURL/engines/readiness" `
        -Method POST `
        -ContentType "application/json" `
        -Headers @{ "Authorization" = "Bearer $token" } `
        -UseBasicParsing
    $readinessResponse = $readiness.Content | ConvertFrom-Json
    Write-Host "   ✓ Readiness calculation successful" -ForegroundColor Green
    Write-Host "     Readiness Score: $($readinessResponse.readiness_score)/100" -ForegroundColor Green
}
catch {
    Write-Host "   ✗ Readiness failed: $_" -ForegroundColor Red
    exit 1
}

# Test 6: Roadmap
Write-Host "6. Testing POST /engines/roadmap..." -ForegroundColor Yellow
try {
    $roadmap = Invoke-WebRequest -Uri "$baseURL/engines/roadmap" `
        -Method POST `
        -ContentType "application/json" `
        -Headers @{ "Authorization" = "Bearer $token" } `
        -UseBasicParsing
    $roadmapResponse = $roadmap.Content | ConvertFrom-Json
    Write-Host "   ✓ Roadmap generation successful" -ForegroundColor Green
    Write-Host "     Milestones: $($roadmapResponse.milestones.Count)" -ForegroundColor Green
    Write-Host "     Total Topics: $($roadmapResponse.total_topics)" -ForegroundColor Green
    Write-Host "     Total Hours: $($roadmapResponse.total_estimated_hours)" -ForegroundColor Green
}
catch {
    Write-Host "   ✗ Roadmap failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host "✓✓✓ All Phase A API Tests Passed! ✓✓✓" -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan
