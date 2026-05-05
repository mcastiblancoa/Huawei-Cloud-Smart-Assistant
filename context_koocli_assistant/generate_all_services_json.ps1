# ============================================================
# generate_all_services_json.ps1
# Genera un JSON por cada servicio de Huawei Cloud KooCLI
# ============================================================

# --- CONFIGURACION ---
$delayMs        = 200       # Pausa entre comandos (ms)
$skipExisting   = $true     # $true = saltar servicios que ya tienen JSON
$outputDir      = "services_schema"

# --- LISTA COMPLETA DE SERVICIOS ---
$allServices = @(
    "AAD", "AOM", "AOS", "APIG", "APM", "AS", "Anti-DDoS", "AstroZero",
    "BMS", "BSSINTL", "CAE", "CBH", "CBS", "CC", "CCE", "CCI", "CCM",
    "CDM", "CDN", "CES", "CFW", "COC", "CPH", "CPTS", "CSE", "CSMS",
    "CSS", "CTS", "CloudBuild", "CloudDC", "CloudPond", "CloudRTC",
    "CloudTest", "CodeArtsArtifact", "CodeArtsBuild", "CodeArtsCheck",
    "CodeArtsDeploy", "CodeArtsPipeline", "CodeArtsRepo", "CodeCheck",
    "DataArtsStudio", "DAS", "DBSS", "DC", "DCC", "DCS", "DDM", "DDS",
    "DIS", "DLI", "DNS", "DRS", "DWS", "DeH", "ECS", "EIP", "ELB",
    "EPS", "ER", "ESW", "EVS", "EdgeSec", "FRS", "FunctionGraph", "GA",
    "GES", "GaussDB", "GaussDBforNoSQL", "GaussDBforopenGauss", "HSS",
    "IAM", "IAMAccessAnalyzer", "IdentityCenter", "IdentityCenterOIDC",
    "IdentityCenterPortalAPI", "IdentityCenterSCIM", "IdentityCenterStore",
    "Image", "IoTDA", "IoTDM", "IMS", "KMS", "KPS", "Kafka", "LTS",
    "Live", "MPC", "MRS", "Marketplace", "Meeting", "ModelArts",
    "Moderation", "NAT", "OCR", "OMS", "Organizations", "ProjectMan",
    "RAM", "RDS", "RFS", "RGC", "RMS", "ROMA", "RabbitMQ", "RocketMQ",
    "SCM", "SFSTurbo", "SIS", "SMN", "SMNGLOBAL", "SMS", "STS", "SWR",
    "SecMaster", "ServiceStage", "TMS", "UCS", "UGO", "VOD", "VPC",
    "VPCEP", "VPN", "WAF", "Workspace", "Config", "DSC"
)

# --- CREAR DIRECTORIO DE SALIDA ---
if (-not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Path $outputDir | Out-Null
    Write-Host "Directorio creado: $outputDir" -ForegroundColor Cyan
}

# --- FUNCION: Obtener operaciones de un servicio ---
function Get-Operations {
    param([string]$Svc)

    try {
        $rawOutput = & hcloud $Svc 2>&1 | Out-String
    }
    catch {
        return @()
    }

    $lines = $rawOutput -split "\r?\n"
    $ops   = @()
    $capturing = $false

    foreach ($line in $lines) {
        if ($line -match "Available Operations:") {
            $capturing = $true
            continue
        }
        if ($capturing -and $line -match "^Run\s") {
            break
        }
        if ($capturing) {
            $tokens = $line.Trim() -split "\s+"
            foreach ($token in $tokens) {
                if ($token -match "^[A-Z][a-zA-Z0-9]+$") {
                    $ops += $token
                }
            }
        }
    }

    return $ops
}

# --- FUNCION: Obtener schema de una operacion ---
function Get-OperationSchema {
    param([string]$Svc, [string]$Op)

    try {
        $helpOutput = & hcloud $Svc $Op --help 2>&1 | Out-String
    }
    catch {
        return $null
    }

    $helpLines = $helpOutput -split "\r?\n"

    # Metodo HTTP
    $method = "UNKNOWN"
    foreach ($hl in $helpLines) {
        $trimmed = $hl.Trim()
        if ($trimmed -eq "POST" -or $trimmed -eq "GET" -or $trimmed -eq "PUT" -or $trimmed -eq "DELETE" -or $trimmed -eq "PATCH") {
            $method = $trimmed
            break
        }
    }

    # Descripcion
    $description = ""
    $inDesc = $false
    $descParts = @()
    foreach ($hl in $helpLines) {
        if ($hl -match "^\s*Description:") {
            $inDesc = $true
            continue
        }
        if ($inDesc) {
            if ($hl -match "^\s*Method:" -or $hl -match "^\s*Params:") {
                break
            }
            $t = $hl.Trim()
            if ($t -ne "") { $descParts += $t }
        }
    }
    $description = $descParts -join " "

    # Parametros
    $paramsList = @()
    $inParams = $false

    foreach ($hl in $helpLines) {
        if ($hl -match "^\s*Params:") {
            $inParams = $true
            continue
        }
        if ($inParams -and $hl -match "^\s*--([\w-]+)") {
            $paramName = $Matches[1]

            $isRequired = $false
            $paramType  = "string"
            $paramLoc   = ""

            if ($hl -match "required")   { $isRequired = $true }
            if ($hl -match "optional")   { $isRequired = $false }
            if ($hl -match "integer")    { $paramType = "integer" }
            if ($hl -match "boolean")    { $paramType = "boolean" }
            if ($hl -match "path")       { $paramLoc = "path" }
            if ($hl -match "body")       { $paramLoc = "body" }
            if ($hl -match "query")      { $paramLoc = "query" }

            $paramsList += @{
                name     = $paramName
                required = $isRequired
                type     = $paramType
                location = $paramLoc
            }
        }
    }

    return [ordered]@{
        operation   = $Op
        method      = $method
        description = $description
        command     = "hcloud $Svc $Op"
        parameters  = $paramsList
    }
}

# ============================================================
# PROCESO PRINCIPAL
# ============================================================

$totalServices = $allServices.Count
$svcCounter    = 0
$skipped       = 0
$failed        = 0
$success       = 0
$globalOpsTotal = 0
$startTime     = Get-Date

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Huawei Cloud KooCLI - Schema Generator for ALL Services"   -ForegroundColor Cyan
Write-Host "  Total servicios: $totalServices"                            -ForegroundColor Cyan
Write-Host "  Directorio salida: $outputDir"                              -ForegroundColor Cyan
Write-Host "  Saltar existentes: $skipExisting"                           -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

foreach ($svc in $allServices) {
    $svcCounter++

    # Nombre de archivo seguro (reemplazar caracteres problematicos)
    $safeName = $svc -replace "[^a-zA-Z0-9_-]", "_"
    $outFile  = Join-Path $outputDir "${safeName}.json"

    # Modo resume: saltar si ya existe
    if ($skipExisting -and (Test-Path $outFile)) {
        Write-Host "[$svcCounter/$totalServices] $svc - SKIP (ya existe)" -ForegroundColor DarkGray
        $skipped++
        continue
    }

    Write-Host "[$svcCounter/$totalServices] $svc - Obteniendo operaciones..." -ForegroundColor White

    # Obtener operaciones del servicio
    $operations = Get-Operations -Svc $svc

    if ($operations.Count -eq 0) {
        Write-Host "  -> Sin operaciones o error. Saltando." -ForegroundColor DarkYellow
        $failed++
        continue
    }

    Write-Host "  -> $($operations.Count) operaciones encontradas. Procesando..." -ForegroundColor Green

    # Procesar cada operacion
    $schemaList = @()
    $opCounter  = 0

    foreach ($op in $operations) {
        $opCounter++
        $pct = [math]::Round(($opCounter / $operations.Count) * 100)

        Write-Host "  [$opCounter/$($operations.Count)] $pct% - $op" -ForegroundColor DarkGray

        $opSchema = Get-OperationSchema -Svc $svc -Op $op

        if ($null -ne $opSchema) {
            $schemaList += $opSchema
        }

        Start-Sleep -Milliseconds $delayMs
    }

    # Guardar JSON del servicio
    $serviceSchema = [ordered]@{
        service       = $svc
        total_operations = $schemaList.Count
        generated_at  = (Get-Date -Format "yyyy-MM-dd HH:mm:ss")
        operations    = $schemaList
    }

    $serviceSchema | ConvertTo-Json -Depth 5 | Out-File -FilePath $outFile -Encoding UTF8

    $success++
    $globalOpsTotal += $schemaList.Count

    # Estadisticas parciales
    $elapsed = (Get-Date) - $startTime
    $avgPerSvc = if ($success -gt 0) { $elapsed.TotalSeconds / $success } else { 0 }
    $remaining = ($totalServices - $svcCounter) * $avgPerSvc
    $eta = if ($remaining -gt 0) { "{0:hh\:mm\:ss}" -f ([TimeSpan]::FromSeconds($remaining)) } else { "00:00:00" }

    Write-Host "  -> Guardado: $outFile ($($schemaList.Count) ops) | ETA restante: $eta" -ForegroundColor Green
    Write-Host ""
}

# ============================================================
# RESUMEN FINAL
# ============================================================

$totalElapsed = (Get-Date) - $startTime

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  RESUMEN FINAL"                                             -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Servicios procesados exitosamente: $success"               -ForegroundColor Green
Write-Host "  Servicios saltados (ya existian):  $skipped"               -ForegroundColor DarkGray
Write-Host "  Servicios fallidos:               $failed"                -ForegroundColor Red
Write-Host "  Total operaciones procesadas:      $globalOpsTotal"        -ForegroundColor White
Write-Host "  Tiempo total: $($totalElapsed.ToString('hh\:mm\:ss'))"     -ForegroundColor White
Write-Host "  Directorio de salida: $outputDir"                          -ForegroundColor White
Write-Host "============================================================" -ForegroundColor Cyan

# Generar archivo indice
$indexFile = Join-Path $outputDir "_index.json"
$indexData = @()
foreach ($f in (Get-ChildItem -Path $outputDir -Filter "*.json" | Where-Object { $_.Name -ne "_index.json" })) {
    $content = Get-Content $f.FullName -Raw -Encoding UTF8 | ConvertFrom-Json
    $indexData += [ordered]@{
        service         = $content.service
        total_operations = $content.total_operations
        file            = $f.Name
    }
}

$indexData | ConvertTo-Json -Depth 3 | Out-File -FilePath $indexFile -Encoding UTF8
Write-Host "  Indice generado: $indexFile" -ForegroundColor Green
Write-Host ""