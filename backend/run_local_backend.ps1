param(
    [string]$ModelId = "",
    [string]$Device = "cuda",
    [string]$Quantization = "4bit",
    [string]$DType = "bfloat16",
    [bool]$CpuOffload = $true,
    [bool]$OffloadBuffers = $true,
    [int]$GpuMemoryLimitMB = 3500,
    [int]$CpuMemoryLimitMB = 16384,
    [int]$Port = 8000
)

$ErrorActionPreference = "Stop"

$localModelPath = "D:\hackathon\chatbot\models\gemma-4-E4B-it"
if ([string]::IsNullOrWhiteSpace($ModelId)) {
    if (Test-Path -LiteralPath $localModelPath) {
        $ModelId = $localModelPath
    } else {
        $ModelId = "google/gemma-4-E4B-it"
    }
}

$env:LLM_BACKEND = "mock-gemma"
$env:GEMMA_MODEL_ID = $ModelId
$env:GEMMA_DEVICE = $Device
$env:GEMMA_QUANTIZATION = $Quantization
$env:GEMMA_DTYPE = $DType
$env:GEMMA_DO_SAMPLE = "false"
$env:GEMMA_TOP_P = "0.95"
$env:GEMMA_MAX_NEW_TOKENS = "512"
$env:GEMMA_CPU_OFFLOAD = $CpuOffload.ToString().ToLower()
$env:GEMMA_OFFLOAD_BUFFERS = $OffloadBuffers.ToString().ToLower()
$env:GEMMA_GPU_MEMORY_LIMIT_MB = $GpuMemoryLimitMB
$env:GEMMA_CPU_MEMORY_LIMIT_MB = $CpuMemoryLimitMB

Write-Host "==> Local backend environment"
Write-Host "LLM_BACKEND=$env:LLM_BACKEND"
Write-Host "GEMMA_MODEL_ID=$env:GEMMA_MODEL_ID"
Write-Host "GEMMA_DEVICE=$env:GEMMA_DEVICE"
Write-Host "GEMMA_QUANTIZATION=$env:GEMMA_QUANTIZATION"
Write-Host "GEMMA_DTYPE=$env:GEMMA_DTYPE"
Write-Host "GEMMA_CPU_OFFLOAD=$env:GEMMA_CPU_OFFLOAD"
Write-Host "GEMMA_OFFLOAD_BUFFERS=$env:GEMMA_OFFLOAD_BUFFERS"
Write-Host "GEMMA_GPU_MEMORY_LIMIT_MB=$env:GEMMA_GPU_MEMORY_LIMIT_MB"
Write-Host "GEMMA_CPU_MEMORY_LIMIT_MB=$env:GEMMA_CPU_MEMORY_LIMIT_MB"
Write-Host "PORT=$Port"
Write-Host ""
Write-Host "Starting uvicorn with local Gemma backend..."

python -m uvicorn app.main:app --reload --host 0.0.0.0 --port $Port
