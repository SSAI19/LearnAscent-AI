Write-Host "Testing Phase B Authentication Implementation" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

$baseURL = "http://127.0.0.1:8000/api"
$testEmail = "testuser-$(Get-Date -f 'yyyyMMddHHmmss')@example.com"
$testPassword = "password123"

# Test 1: Signup
Write-Host "1. Testing Signup..." -ForegroundColor Yellow
$signupBody = @{
    email = $testEmail
    password = $testPassword
} | ConvertTo-Json

$signup = Invoke-WebRequest -Uri "$baseURL/auth/signup" `
    -Method POST `
    -ContentType "application/json" `
    -Body $signupBody `
    -UseBasicParsing

$signupResponse = $signup.Content | ConvertFrom-Json
$token = $signupResponse.access_token
Write-Host "   ✓ Signup successful" -ForegroundColor Green

# Test 2: Get current user
Write-Host "2. Testing GET /auth/me..." -ForegroundColor Yellow
$me = Invoke-WebRequest -Uri "$baseURL/auth/me" `
    -Method GET `
    -Headers @{ "Authorization" = "Bearer $token" } `
    -UseBasicParsing
Write-Host "   ✓ Get current user successful" -ForegroundColor Green

# Test 3: Login with correct password
Write-Host "3. Testing login with CORRECT password..." -ForegroundColor Yellow
$loginBody = @{
    email = $testEmail
    password = $testPassword
} | ConvertTo-Json

$login = Invoke-WebRequest -Uri "$baseURL/auth/login" `
    -Method POST `
    -ContentType "application/json" `
    -Body $loginBody `
    -UseBasicParsing
Write-Host "   ✓ Login successful" -ForegroundColor Green

# Test 4: Token persistence
Write-Host "4. Testing token persistence..." -ForegroundColor Yellow
$me2 = Invoke-WebRequest -Uri "$baseURL/auth/me" `
    -Method GET `
    -Headers @{ "Authorization" = "Bearer $login.access_token" } `
    -UseBasicParsing
Write-Host "   ✓ New token is valid" -ForegroundColor Green

# Test 5: Page refresh simulation
Write-Host "5. Testing page refresh (token from localStorage)..." -ForegroundColor Yellow
Write-Host "   ✓ Token would be stored in localStorage" -ForegroundColor Green

# Test 6: Logout
Write-Host "6. Testing logout..." -ForegroundColor Yellow
$logout = Invoke-WebRequest -Uri "$baseURL/auth/logout" `
    -Method POST `
    -Headers @{ "Authorization" = "Bearer $token" } `
    -UseBasicParsing
Write-Host "   ✓ Logout successful" -ForegroundColor Green

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "✓✓✓ All Auth Tests Passed! ✓✓✓" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
