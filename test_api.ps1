#!/usr/bin/env powershell
<#
Phase A API Testing Script

This script tests all major API endpoints to verify the backend works correctly.
Usage: . .\test_api.ps1

Make sure the backend is running on http://127.0.0.1:8000 before running this script.
#>

$baseURL = "http://127.0.0.1:8000/api"
$testEmail = "test-$(Get-Date -f 'yyyyMMddHHmmss')@example.com"
$testPassword = "test123"
$token = ""
$userId = ""

Write-Host "╔═══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  LearnAscent AI - Phase A API Tests       ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""

# Test 1: Signup
Write-Host "[1] Testing POST /auth/signup" -ForegroundColor Yellow
try {
    $signupBody = @{
        email = $testEmail
        password = $testPassword
    } | ConvertTo-Json
    
    $signupResponse = Invoke-RestMethod -Uri "$baseURL/auth/signup" `
        -Method POST `
        -ContentType "application/json" `
        -Body $signupBody `
        -ErrorAction Stop
    
    $token = $signupResponse.access_token
    $userId = $signupResponse.user_id
    
    Write-Host "✓ Signup successful" -ForegroundColor Green
    Write-Host "  Email: $testEmail" -ForegroundColor Green
    Write-Host "  Token: $($token.Substring(0, 20))..." -ForegroundColor Green
}
catch {
    Write-Host "✗ Signup failed: $_" -ForegroundColor Red
    exit 1
}

# Test 2: Get current user
Write-Host "[2] Testing GET /auth/me" -ForegroundColor Yellow
try {
    $meResponse = Invoke-RestMethod -Uri "$baseURL/auth/me" `
        -Method GET `
        -Headers @{ "Authorization" = "Bearer $token" } `
        -ErrorAction Stop
    
    Write-Host "✓ Get current user successful" -ForegroundColor Green
    Write-Host "  User ID: $($meResponse.user_id)" -ForegroundColor Green
    Write-Host "  Email: $($meResponse.email)" -ForegroundColor Green
}
catch {
    Write-Host "✗ Get current user failed: $_" -ForegroundColor Red
    exit 1
}

# Test 3: Create learner profile
Write-Host "[3] Testing POST /learner/profile" -ForegroundColor Yellow
try {
    $profileBody = @{
        name = "Test Learner"
        experience_level = "beginner"
        target_career_code = "15-2051.00"
        target_career_title = "Data Scientists"
        education_status = "student"
        year_of_study = 2
        career_interests = @("Data Science", "Machine Learning")
        previous_courses = @("Python Basics")
        preferred_language = "en"
        available_minutes_per_day = 30
        target_duration_weeks = 12
        known_tools = @("Python")
    } | ConvertTo-Json
    
    $profileResponse = Invoke-RestMethod -Uri "$baseURL/learner/profile" `
        -Method POST `
        -ContentType "application/json" `
        -Headers @{ "Authorization" = "Bearer $token" } `
        -Body $profileBody `
        -ErrorAction Stop
    
    Write-Host "✓ Create learner profile successful" -ForegroundColor Green
    Write-Host "  Name: $($profileResponse.name)" -ForegroundColor Green
    Write-Host "  Target Career: $($profileResponse.target_career_title)" -ForegroundColor Green
    Write-Host "  Assessment Status: $($profileResponse.assessment_status)" -ForegroundColor Green
}
catch {
    Write-Host "✗ Create learner profile failed: $_" -ForegroundColor Red
    exit 1
}

# Test 4: Get learner profile
Write-Host "[4] Testing GET /learner" -ForegroundColor Yellow
try {
    $getProfileResponse = Invoke-RestMethod -Uri "$baseURL/learner" `
        -Method GET `
        -Headers @{ "Authorization" = "Bearer $token" } `
        -ErrorAction Stop
    
    Write-Host "✓ Get learner profile successful" -ForegroundColor Green
    Write-Host "  Name: $($getProfileResponse.name)" -ForegroundColor Green
    Write-Host "  Milestones: $($getProfileResponse.completed_milestones)/$($getProfileResponse.total_milestones)" -ForegroundColor Green
}
catch {
    Write-Host "✗ Get learner profile failed: $_" -ForegroundColor Red
    exit 1
}

# Test 5: Skill gap analysis
Write-Host "[5] Testing POST /engines/skill-gap" -ForegroundColor Yellow
try {
    $gapResponse = Invoke-RestMethod -Uri "$baseURL/engines/skill-gap" `
        -Method POST `
        -ContentType "application/json" `
        -Headers @{ "Authorization" = "Bearer $token" } `
        -Body "{`"source`": `"essential_skills`"}" `
        -ErrorAction Stop
    
    Write-Host "✓ Skill gap analysis successful" -ForegroundColor Green
    Write-Host "  Gaps found: $($gapResponse.Count)" -ForegroundColor Green
    if ($gapResponse.Count -gt 0) {
        Write-Host "  First gap: $($gapResponse[0].element) (gap: $($gapResponse[0].gap), priority: $($gapResponse[0].high_priority))" -ForegroundColor Green
    }
}
catch {
    Write-Host "✗ Skill gap analysis failed: $_" -ForegroundColor Red
    exit 1
}

# Test 6: Readiness calculation
Write-Host "[6] Testing POST /engines/readiness" -ForegroundColor Yellow
try {
    $readinessResponse = Invoke-RestMethod -Uri "$baseURL/engines/readiness" `
        -Method POST `
        -ContentType "application/json" `
        -Headers @{ "Authorization" = "Bearer $token" } `
        -ErrorAction Stop
    
    Write-Host "✓ Readiness calculation successful" -ForegroundColor Green
    Write-Host "  Readiness Score: $($readinessResponse.readiness_score)/100" -ForegroundColor Green
    Write-Host "  Next Action: $($readinessResponse.next_action)" -ForegroundColor Green
}
catch {
    Write-Host "✗ Readiness calculation failed: $_" -ForegroundColor Red
    exit 1
}

# Test 7: Roadmap generation
Write-Host "[7] Testing POST /engines/roadmap" -ForegroundColor Yellow
try {
    $roadmapResponse = Invoke-RestMethod -Uri "$baseURL/engines/roadmap" `
        -Method POST `
        -ContentType "application/json" `
        -Headers @{ "Authorization" = "Bearer $token" } `
        -ErrorAction Stop
    
    Write-Host "✓ Roadmap generation successful" -ForegroundColor Green
    Write-Host "  Target Career: $($roadmapResponse.target_career_title)" -ForegroundColor Green
    Write-Host "  Weeks Planned: $($roadmapResponse.weeks_planned)" -ForegroundColor Green
    Write-Host "  Total Topics: $($roadmapResponse.total_topics)" -ForegroundColor Green
    Write-Host "  Total Hours: $($roadmapResponse.total_estimated_hours)" -ForegroundColor Green
}
catch {
    Write-Host "✗ Roadmap generation failed: $_" -ForegroundColor Red
    exit 1
}

# Test 8: Assessment submission
Write-Host "[8] Testing POST /engines/assessment" -ForegroundColor Yellow
try {
    $assessmentBody = @{
        skill_element = "Computers and Electronics"
        score = 75.0
        weak_concepts = @("REST APIs", "Database design")
    } | ConvertTo-Json
    
    $assessmentResponse = Invoke-RestMethod -Uri "$baseURL/engines/assessment" `
        -Method POST `
        -ContentType "application/json" `
        -Headers @{ "Authorization" = "Bearer $token" } `
        -Body $assessmentBody `
        -ErrorAction Stop
    
    Write-Host "✓ Assessment submission successful" -ForegroundColor Green
    Write-Host "  Action: $($assessmentResponse.action)" -ForegroundColor Green
    Write-Host "  Skill: $($assessmentResponse.skill_element)" -ForegroundColor Green
    Write-Host "  Score: $($assessmentResponse.score)" -ForegroundColor Green
    Write-Host "  Message: $($assessmentResponse.message)" -ForegroundColor Green
}
catch {
    Write-Host "✗ Assessment submission failed: $_" -ForegroundColor Red
    exit 1
}

# Test 9: Occupation search
Write-Host "[9] Testing GET /engines/occupation-search" -ForegroundColor Yellow
try {
    $searchResponse = Invoke-RestMethod -Uri "$baseURL/engines/occupation-search?query=machine%20learning" `
        -Method GET `
        -ErrorAction Stop
    
    Write-Host "✓ Occupation search successful" -ForegroundColor Green
    Write-Host "  Matches found: $($searchResponse.Count)" -ForegroundColor Green
    if ($searchResponse.Count -gt 0) {
        Write-Host "  Top match: $($searchResponse[0].code) - $($searchResponse[0].title) (score: $($searchResponse[0].score))" -ForegroundColor Green
    }
}
catch {
    Write-Host "✗ Occupation search failed: $_" -ForegroundColor Red
    exit 1
}

# Test 10: Login
Write-Host "[10] Testing POST /auth/login" -ForegroundColor Yellow
try {
    $loginBody = @{
        email = $testEmail
        password = $testPassword
    } | ConvertTo-Json
    
    $loginResponse = Invoke-RestMethod -Uri "$baseURL/auth/login" `
        -Method POST `
        -ContentType "application/json" `
        -Body $loginBody `
        -ErrorAction Stop
    
    Write-Host "✓ Login successful" -ForegroundColor Green
    Write-Host "  Token: $($loginResponse.access_token.Substring(0, 20))..." -ForegroundColor Green
}
catch {
    Write-Host "✗ Login failed: $_" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "╔═══════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  ✓ All Phase A API Tests Passed!          ║" -ForegroundColor Cyan
Write-Host "╚═══════════════════════════════════════════╝" -ForegroundColor Cyan
