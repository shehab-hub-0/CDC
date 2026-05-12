# 🚀 Master Reset Script for CDC Project
# This script wipes all data from Postgres, Kafka, and ClickHouse
# and re-initializes the schema using your SQL files.

Write-Host "--- Starting Master Project Reset ---" -ForegroundColor Cyan

# Set Working Directory to Project Root
$PSScriptRoot = Split-Path -Parent $MyInvocation.MyCommand.Definition
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
Write-Host "Project Root: $ProjectRoot" -ForegroundColor Gray

# 1. Full Wipe (Containers & Volumes)
Write-Host "[1/6] Wiping all containers and ephemeral data..." -ForegroundColor Yellow
# docker compose down -v
echo "==============================="
echo "run 'docker compose down -v' if the docker containers are not down"
echo "==============================="

# 2. Start Services
Write-Host "[2/6] Starting infrastructure..." -ForegroundColor Yellow
docker compose up -d

# 3. Wait for Postgres
Write-Host "[3/6] Waiting for PostgreSQL to be ready..." -ForegroundColor Blue
$ready = $false
$retry = 0
while (-not $ready -and $retry -lt 30) {
    $check = docker exec postgres psql -U postgres -c "SELECT 1" 2>$null
    if ($check -match "1") { 
        $ready = $true 
    } else { 
        Start-Sleep -Seconds 2
        Write-Host "." -NoNewline 
        $retry++
    }
}
if (-not $ready) { Write-Error "Postgres failed to start"; exit }
Write-Host " Ready!" -ForegroundColor Green

# 4. Initialize Postgres Schema
Write-Host "[4/6] Initializing Postgres Schema (config/input_Schema.sql & config/scripts.sql)..." -ForegroundColor Yellow
# Run input_Schema.sql - Using -i for stdin
cat "config/input_Schema.sql" | docker exec -i postgres psql -U postgres -d financial_db
# Run scripts.sql (Audit Triggers)
cat "config/scripts.sql" | docker exec -i postgres psql -U postgres -d financial_db

# 5. Initialize ClickHouse Schema
Write-Host "[5/6] Initializing ClickHouse Schema (config/clickhouse-init.sql)..." -ForegroundColor Yellow
cat "config/clickhouse-init.sql" | docker exec -i clickhouse clickhouse-client -n

# 6. Re-register Debezium Connector & Superset Setup
Write-Host "[6/6] Re-registering Debezium & Setting up Superset..." -ForegroundColor Yellow
Write-Host "Waiting for APIs to stabilize (this may take 30-40 seconds)..." -ForegroundColor Blue
Start-Sleep -Seconds 30 
python scripts/setup_pipeline.py

Write-Host "`n✅ SUCCESS: Project has been reset and re-initialized!" -ForegroundColor Green
Write-Host "Next Steps:" -ForegroundColor White
Write-Host "1. Run data generator: python generator/main.py"
Write-Host "2. Run Spark pipeline in Jupyter"
Write-Host "3. Open Superset: http://localhost:8089"
