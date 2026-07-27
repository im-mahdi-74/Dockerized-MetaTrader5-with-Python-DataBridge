# start.ps1

# This script is responsible for running both the streamer and API gateway services
Write-Host "Supervisor: Starting Streamer Bot..."
$StreamerJob = Start-Job -ScriptBlock { & "C:\Program Files\Python311\python.exe" "C:\app\streamer.py" }

# Wait a bit for MetaTrader to be launched by one of the scripts
Write-Host "Supervisor: Waiting 15 seconds for MetaTrader terminal to initialize..."
Start-Sleep -Seconds 15

Write-Host "Supervisor: Starting API Gateway Bot..."
$ApiGatewayJob = Start-Job -ScriptBlock { & "C:\Program Files\Python311\python.exe" "C:\app\api_gateway.py" }

Write-Host "Supervisor: All jobs started. Monitoring..."
# Main loop to continuously display logs and keep the container alive
while ($true) {
    Receive-Job -Job $StreamerJob
    Receive-Job -Job $ApiGatewayJob
    
    if ($StreamerJob.State -eq 'Failed' -or $ApiGatewayJob.State -eq 'Failed') {
        Write-Host "Supervisor: One of the jobs has failed. Check logs above for errors."
    }
    
    Start-Sleep -Seconds 2
}