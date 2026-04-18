param(
    [string]$ModelId = "",
    [string]$Device = "cuda",
    [string]$Quantization = "",
    [string]$DType = "bfloat16",
    [Nullable[bool]]$CpuOffload = $null,
    [Nullable[bool]]$OffloadBuffers = $null,
    [int]$GpuMemoryLimitMB = 0,
    [int]$CpuMemoryLimitMB = 0,
    [ValidateSet("auto", "h100", "generic-cuda", "cpu")]
    [string]$HardwareProfile = "auto",
    [switch]$Reload,
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

function Get-DetectedGpuInfo {
    $nvidiaSmi = Get-Command "nvidia-smi" -ErrorAction SilentlyContinue
    if (-not $nvidiaSmi) {
        return $null
    }

    $firstLine = & $nvidiaSmi.Source --query-gpu=name,memory.total --format=csv,noheader,nounits 2>$null |
        Select-Object -First 1
    if (-not $firstLine) {
        return $null
    }

    if ($firstLine -notmatch "^\s*(.+?)\s*,\s*([0-9]+)\s*$") {
        return $null
    }

    return [pscustomobject]@{
        Name = $Matches[1].Trim()
        MemoryMB = [int]$Matches[2]
    }
}

function Resolve-HardwareProfile {
    param(
        [string]$RequestedProfile,
        [string]$ResolvedDevice,
        [object]$DetectedGpu
    )

    $deviceMode = $ResolvedDevice.Trim().ToLower()
    if ($deviceMode -eq "cpu") {
        return "cpu"
    }

    if ($RequestedProfile -ne "auto") {
        return $RequestedProfile
    }

    if ($DetectedGpu -and $DetectedGpu.Name -match "H100") {
        return "h100"
    }

    return "generic-cuda"
}

function Resolve-GpuMemoryLimit {
    param(
        [string]$Profile,
        [object]$DetectedGpu,
        [int]$RequestedLimit
    )

    if ($RequestedLimit -gt 0) {
        return $RequestedLimit
    }

    if ($Profile -eq "h100") {
        if ($DetectedGpu -and $DetectedGpu.MemoryMB -gt 0) {
            return [Math]::Floor($DetectedGpu.MemoryMB * 0.9)
        }
        return 71680
    }

    if ($Profile -eq "generic-cuda") {
        if ($DetectedGpu -and $DetectedGpu.MemoryMB -gt 0) {
            return [Math]::Max([Math]::Floor($DetectedGpu.MemoryMB * 0.75), 3072)
        }
        return 11000
    }

    return 0
}

function Resolve-CpuMemoryLimit {
    param(
        [string]$Profile,
        [int]$RequestedLimit
    )

    if ($RequestedLimit -gt 0) {
        return $RequestedLimit
    }

    switch ($Profile) {
        "h100" { return 0 }
        "generic-cuda" { return 24576 }
        "cpu" { return 65536 }
        default { return 0 }
    }
}

function Resolve-BoolSetting {
    param(
        [Nullable[bool]]$RequestedValue,
        [bool]$DefaultValue
    )

    if ($null -ne $RequestedValue) {
        return [bool]$RequestedValue
    }

    return $DefaultValue
}

# Load .env so DATABASE_URL and other secrets are available to the Python app
if (Test-Path -LiteralPath "$PSScriptRoot\.env") {
    Get-Content "$PSScriptRoot\.env" | ForEach-Object {
        if ($_ -match "^\s*([^#][^=]+?)\s*=\s*(.+?)\s*$") {
            [System.Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim('"'))
        }
    }
    Write-Host "==> Loaded .env"
}

if ([string]::IsNullOrWhiteSpace($ModelId)) {
    $ModelId = "google/gemma-4-E4B-it"
}

$detectedGpu = $null
if ($Device.Trim().ToLower() -in @("cuda", "auto")) {
    $detectedGpu = Get-DetectedGpuInfo
}

$resolvedProfile = Resolve-HardwareProfile `
    -RequestedProfile $HardwareProfile `
    -ResolvedDevice $Device `
    -DetectedGpu $detectedGpu

if (-not $PSBoundParameters.ContainsKey("Quantization") -or [string]::IsNullOrWhiteSpace($Quantization)) {
    if ($resolvedProfile -eq "h100") {
        $Quantization = "none"
    } elseif ($resolvedProfile -eq "generic-cuda") {
        $Quantization = "4bit"
    } else {
        $Quantization = "none"
    }
}

$resolvedCpuOffload = Resolve-BoolSetting `
    -RequestedValue $CpuOffload `
    -DefaultValue ($resolvedProfile -eq "generic-cuda")

$resolvedOffloadBuffers = Resolve-BoolSetting `
    -RequestedValue $OffloadBuffers `
    -DefaultValue ($resolvedProfile -eq "generic-cuda")

$resolvedGpuMemoryLimitMB = Resolve-GpuMemoryLimit `
    -Profile $resolvedProfile `
    -DetectedGpu $detectedGpu `
    -RequestedLimit $GpuMemoryLimitMB

$resolvedCpuMemoryLimitMB = Resolve-CpuMemoryLimit `
    -Profile $resolvedProfile `
    -RequestedLimit $CpuMemoryLimitMB

$env:LLM_BACKEND = "gemma_local"
$env:GEMMA_MODEL_ID = $ModelId
$env:GEMMA_DEVICE = $Device
$env:GEMMA_QUANTIZATION = $Quantization
$env:GEMMA_DTYPE = $DType
$env:GEMMA_DO_SAMPLE = "false"
$env:GEMMA_TOP_P = "0.95"
$env:GEMMA_MAX_NEW_TOKENS = "512"
$env:GEMMA_CPU_OFFLOAD = $resolvedCpuOffload.ToString().ToLower()
$env:GEMMA_OFFLOAD_BUFFERS = $resolvedOffloadBuffers.ToString().ToLower()
$env:GEMMA_GPU_MEMORY_LIMIT_MB = $resolvedGpuMemoryLimitMB
$env:GEMMA_CPU_MEMORY_LIMIT_MB = $resolvedCpuMemoryLimitMB

Write-Host "==> Gemma runtime environment"
Write-Host "LLM_BACKEND=$env:LLM_BACKEND"
Write-Host "GEMMA_MODEL_ID=$env:GEMMA_MODEL_ID"
Write-Host "GEMMA_DEVICE=$env:GEMMA_DEVICE"
Write-Host "GEMMA_QUANTIZATION=$env:GEMMA_QUANTIZATION"
Write-Host "GEMMA_DTYPE=$env:GEMMA_DTYPE"
Write-Host "GEMMA_CPU_OFFLOAD=$env:GEMMA_CPU_OFFLOAD"
Write-Host "GEMMA_OFFLOAD_BUFFERS=$env:GEMMA_OFFLOAD_BUFFERS"
Write-Host "GEMMA_GPU_MEMORY_LIMIT_MB=$env:GEMMA_GPU_MEMORY_LIMIT_MB"
Write-Host "GEMMA_CPU_MEMORY_LIMIT_MB=$env:GEMMA_CPU_MEMORY_LIMIT_MB"
Write-Host "HARDWARE_PROFILE=$resolvedProfile"
if ($detectedGpu) {
    Write-Host "DETECTED_GPU=$($detectedGpu.Name) ($($detectedGpu.MemoryMB) MiB)"
}
Write-Host "PORT=$Port"
Write-Host ""
Write-Host "Starting uvicorn with Gemma local runtime..."

$uvicornArgs = @(
    "-m", "uvicorn",
    "app.main:app",
    "--host", "0.0.0.0",
    "--port", "$Port"
)

if ($Reload.IsPresent) {
    $uvicornArgs += "--reload"
}

python @uvicornArgs
