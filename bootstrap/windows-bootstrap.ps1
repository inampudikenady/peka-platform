Write-Host "PEKA Windows bootstrap started"

$HostName = $env:COMPUTERNAME
$PekaServer = "10.50.1.4"
$LokiUrl = "http://$PekaServer`:3100/loki/api/v1/push"

$IpAddress = (
    Get-NetIPAddress -AddressFamily IPv4 |
    Where-Object {
        $_.IPAddress -notlike "169.*" -and
        $_.IPAddress -ne "127.0.0.1" -and
        $_.PrefixOrigin -ne "WellKnown"
    } |
    Select-Object -First 1 -ExpandProperty IPAddress
)

Write-Host "Host: $HostName"
Write-Host "IP: $IpAddress"

$TempDir = "$env:TEMP\peka-bootstrap"
New-Item -ItemType Directory -Force -Path $TempDir | Out-Null

Write-Host "Installing windows_exporter..."

$ExporterMsi = "$TempDir\windows_exporter.msi"

Invoke-WebRequest `
  -Uri "https://github.com/prometheus-community/windows_exporter/releases/download/v0.27.2/windows_exporter-0.27.2-amd64.msi" `
  -OutFile $ExporterMsi

Start-Process msiexec.exe -Wait -ArgumentList @(
    "/i"
    $ExporterMsi
    "/qn"
    "ENABLED_COLLECTORS=cpu,logical_disk,memory,net,os,service,system,process"
)

Start-Sleep -Seconds 5
Invoke-WebRequest http://localhost:9182/metrics -UseBasicParsing | Out-Null

Write-Host "windows_exporter installed"

Write-Host "Installing Promtail..."

$PromtailDir = "C:\promtail"
New-Item -ItemType Directory -Force -Path $PromtailDir | Out-Null

$PromtailZip = "$TempDir\promtail-windows-amd64.zip"
$PromtailExe = "$PromtailDir\promtail.exe"

Invoke-WebRequest `
  -Uri "https://github.com/grafana/loki/releases/download/v2.9.8/promtail-windows-amd64.zip" `
  -OutFile $PromtailZip

Expand-Archive -Path $PromtailZip -DestinationPath $TempDir -Force
Copy-Item "$TempDir\promtail-windows-amd64.exe" $PromtailExe -Force

@"
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: C:\promtail\positions.yml

clients:
  - url: $LokiUrl

scrape_configs:
  - job_name: windows-application
    windows_events:
      use_incoming_timestamp: true
      bookmark_path: C:\promtail\bookmark-application.xml
      eventlog_name: Application
      labels:
        job: windows-events
        host: $HostName
        channel: Application

  - job_name: windows-system
    windows_events:
      use_incoming_timestamp: true
      bookmark_path: C:\promtail\bookmark-system.xml
      eventlog_name: System
      labels:
        job: windows-events
        host: $HostName
        channel: System

  - job_name: windows-security
    windows_events:
      use_incoming_timestamp: true
      bookmark_path: C:\promtail\bookmark-security.xml
      eventlog_name: Security
      labels:
        job: windows-events
        host: $HostName
        channel: Security
"@ | Set-Content -Path "$PromtailDir\config.yml" -Encoding ASCII

Write-Host "Installing NSSM..."

$NssmZip = "$TempDir\nssm.zip"

Invoke-WebRequest `
  -Uri "https://nssm.cc/release/nssm-2.24.zip" `
  -OutFile $NssmZip

Expand-Archive -Path $NssmZip -DestinationPath $TempDir -Force

$NssmExe = Get-ChildItem `
  -Path $TempDir `
  -Recurse `
  -Filter nssm.exe |
  Where-Object { $_.FullName -match "win64" } |
  Select-Object -First 1 -ExpandProperty FullName

if (-not $NssmExe) {
    throw "NSSM executable not found"
}

if (Get-Service promtail -ErrorAction SilentlyContinue) {
    Stop-Service promtail -Force -ErrorAction SilentlyContinue
    & $NssmExe remove promtail confirm
    Start-Sleep -Seconds 2
}

& $NssmExe install promtail $PromtailExe "-config.file=$PromtailDir\config.yml"
& $NssmExe set promtail Start SERVICE_AUTO_START
& $NssmExe set promtail AppStdout "$PromtailDir\promtail.out.log"
& $NssmExe set promtail AppStderr "$PromtailDir\promtail.err.log"
& $NssmExe set promtail AppRotateFiles 1
& $NssmExe set promtail AppRotateOnline 1
& $NssmExe set promtail AppRotateBytes 10485760

Start-Service promtail

Start-Sleep -Seconds 5
Invoke-WebRequest http://localhost:9080/metrics -UseBasicParsing | Out-Null

Write-Host "Promtail installed and running"
Write-Host "PEKA Windows bootstrap completed"
