# Personal Knowledge Base Agent - System Startup Script
# Run this script from the project root directory

param(
    [switch]$SkipInstall,
    [switch]$BackendOnly,
    [switch]$FrontendOnly
)

$ErrorActionPreference = "Stop"
$ProjectRoot = $PSScriptRoot
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "       Personal Knowledge Base Agent - System Startup          " -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""

# Function to check if a command exists
function Test-Command($Command) {
    try {
        Get-Command $Command -ErrorAction Stop | Out-Null
        return $true
    } catch {
        return $false
    }
}

# Check prerequisites
Write-Host "[*] Checking prerequisites..." -ForegroundColor Cyan

if (-not (Test-Command "python")) {
    Write-Host "[!] Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

if (-not (Test-Command "node")) {
    Write-Host "[!] Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}

$pythonVersion = python --version 2>&1
$nodeVersion = node --version 2>&1
Write-Host "    Python: $pythonVersion" -ForegroundColor Gray
Write-Host "    Node.js: $nodeVersion" -ForegroundColor Gray

# Create .env file if it doesn't exist
$envFile = Join-Path $BackendDir ".env"
if (-not (Test-Path $envFile)) {
    Write-Host "[*] Creating .env file..." -ForegroundColor Cyan
    $envContent = @"
# Personal Knowledge Base Agent - Environment Configuration

# Groq API Key (required for LLM features)
# Get your key at: https://console.groq.com/keys
GROQ_API_KEY=

# Groq Model (default: llama-3.1-8b-instant)
GROQ_MODEL_NAME=llama-3.1-8b-instant

# Embedding Model (default: all-MiniLM-L6-v2)
MODEL_NAME=all-MiniLM-L6-v2

# Database paths (relative to backend/)
VECTOR_DB_PATH=data/vector_store
SQLITE_DB_PATH=data/episodic.db
"@
    $envContent | Out-File -FilePath $envFile -Encoding utf8
    Write-Host "    Created .env file" -ForegroundColor Yellow
    Write-Host "    [!] Please add your GROQ_API_KEY to the .env file" -ForegroundColor Yellow
}

# Create data directory
$dataDir = Join-Path $BackendDir "data"
if (-not (Test-Path $dataDir)) {
    New-Item -ItemType Directory -Path $dataDir | Out-Null
    Write-Host "    Created data directory" -ForegroundColor Gray
}

# Setup Backend
if (-not $FrontendOnly) {
    Write-Host ""
    Write-Host "[*] Setting up Backend..." -ForegroundColor Cyan
    
    Push-Location $BackendDir
    
    # Create virtual environment if it doesn't exist
    $venvDir = Join-Path $BackendDir "venv"
    if (-not (Test-Path $venvDir)) {
        Write-Host "    Creating virtual environment..." -ForegroundColor Gray
        python -m venv venv
    }
    
    # Activate virtual environment
    $activateScript = Join-Path $venvDir "Scripts\Activate.ps1"
    . $activateScript
    
    if (-not $SkipInstall) {
        Write-Host "    Installing Python dependencies..." -ForegroundColor Gray
        pip install -r requirements.txt --quiet
    }
    
    Pop-Location
}

# Setup Frontend
if (-not $BackendOnly) {
    Write-Host ""
    Write-Host "[*] Setting up Frontend..." -ForegroundColor Cyan
    
    Push-Location $FrontendDir
    
    # Create .env.local if it doesn't exist
    $frontendEnv = Join-Path $FrontendDir ".env.local"
    if (-not (Test-Path $frontendEnv)) {
        "NEXT_PUBLIC_API_URL=http://localhost:8000" | Out-File -FilePath $frontendEnv -Encoding utf8
        Write-Host "    Created .env.local" -ForegroundColor Gray
    }
    
    if (-not $SkipInstall) {
        $nodeModules = Join-Path $FrontendDir "node_modules"
        if (-not (Test-Path $nodeModules)) {
            Write-Host "    Installing Node.js dependencies..." -ForegroundColor Gray
            npm install --silent
        }
    }
    
    Pop-Location
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "                    Starting Services                          " -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""

# Start Backend
if (-not $FrontendOnly) {
    Write-Host "[*] Starting Backend (FastAPI)..." -ForegroundColor Cyan
    Write-Host "    URL: http://localhost:8000" -ForegroundColor Gray
    Write-Host "    API Docs: http://localhost:8000/docs" -ForegroundColor Gray
    
    $backendCmd = "Set-Location '$BackendDir'; & '$BackendDir\venv\Scripts\Activate.ps1'; Write-Host 'Backend Server Starting...' -ForegroundColor Green; uvicorn app.main:app --reload --host 0.0.0.0 --port 8000"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $backendCmd
}

# Give backend time to start
Start-Sleep -Seconds 3

# Start Frontend
if (-not $BackendOnly) {
    Write-Host "[*] Starting Frontend (Next.js)..." -ForegroundColor Cyan
    Write-Host "    URL: http://localhost:3000" -ForegroundColor Gray
    
    $frontendCmd = "Set-Location '$FrontendDir'; Write-Host 'Frontend Server Starting...' -ForegroundColor Green; npm run dev"
    Start-Process powershell -ArgumentList "-NoExit", "-Command", $frontendCmd
}

Write-Host ""
Write-Host "================================================================" -ForegroundColor Green
Write-Host "                    System Ready!                              " -ForegroundColor Green
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Frontend:  http://localhost:3000" -ForegroundColor White
Write-Host "  Backend:   http://localhost:8000" -ForegroundColor White
Write-Host "  API Docs:  http://localhost:8000/docs" -ForegroundColor White
Write-Host "================================================================" -ForegroundColor Green
Write-Host "  Close the terminal windows to stop the services" -ForegroundColor Gray
Write-Host "================================================================" -ForegroundColor Green
Write-Host ""

# Open browser
Start-Sleep -Seconds 2
Start-Process "http://localhost:3000"
