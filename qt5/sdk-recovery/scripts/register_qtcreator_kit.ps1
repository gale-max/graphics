param(
    [string]$SdkRoot = "D:\luna-sdk\qt5-5.15.19",
    [string]$QtCreatorRoot = "D:\luna-sdk\qt5-5.15.19\tools\QtCreator-20.0.1",
    [string]$WorkspaceRoot = "D:\workspace\luna-workspace",
    [string]$SettingsPath = "$env:APPDATA\QtProject\qtcreator"
)

$ErrorActionPreference = "Stop"
$settingsDirectory = $SettingsPath
if ([string]::IsNullOrWhiteSpace($settingsDirectory)) {
    $settingsDirectory = Join-Path ([Environment]::GetFolderPath("ApplicationData")) `
        "QtProject\qtcreator"
}

$sdkTool = Join-Path $QtCreatorRoot "sdktool.exe"
$qmake = Join-Path $SdkRoot "bin\qmake.exe"
$toolchain = Join-Path $WorkspaceRoot "tools\toolchains\aarch64-none-linux-gnu\bin"
$sysroot = Join-Path $WorkspaceRoot "tools\toolchains\aarch64-none-linux-gnu\aarch64-none-linux-gnu\libc"
$gcc = Join-Path $toolchain "aarch64-none-linux-gnu-gcc.exe"
$gxx = Join-Path $toolchain "aarch64-none-linux-gnu-g++.exe"
$gdb = Join-Path $toolchain "aarch64-none-linux-gnu-gdb.exe"

$qtId = "Luna.Qt.5.15.19.ARMv8A"
$cId = "Luna.ToolChain.Gcc.ARMv8A.C"
$cxxId = "Luna.ToolChain.Gcc.ARMv8A.Cxx"
$debuggerId = "Luna.Debugger.Gdb.ARMv8A"
$kitId = "Luna.Kit.ARMv8A"
$abi = "arm-linux-generic-elf-64bit"

foreach ($path in @($sdkTool, $qmake, $gcc, $gxx, $gdb, $sysroot)) {
    if (-not (Test-Path -LiteralPath $path)) {
        throw "缺少 Luna Qt Creator Kit 输入：$path"
    }
}

New-Item -ItemType Directory -Force -Path $settingsDirectory | Out-Null

function Invoke-SdkTool {
    param(
        [Parameter(Mandatory = $true)]
        [string[]]$Arguments,
        [switch]$AllowFailure
    )

    & $sdkTool "--sdkpath=$settingsDirectory" @Arguments
    if (($LASTEXITCODE -ne 0) -and (-not $AllowFailure)) {
        throw "sdktool 执行失败：$($Arguments -join ' ')"
    }
}

# 使用固定 ID 删除旧配置，使重复执行不会累积同名 Qt、编译器和 Kit。
Invoke-SdkTool -AllowFailure -Arguments @("rmKit", "--id", $kitId)
Invoke-SdkTool -AllowFailure -Arguments @("rmDebugger", "--id", $debuggerId)
Invoke-SdkTool -AllowFailure -Arguments @("rmTC", "--id", $cId)
Invoke-SdkTool -AllowFailure -Arguments @("rmTC", "--id", $cxxId)
Invoke-SdkTool -AllowFailure -Arguments @("rmQt", "--id", $qtId)

Invoke-SdkTool -Arguments @(
    "addTC", "--id", $cId, "--language", "C",
    "--name", "Luna ARMv8A GCC", "--path", $gcc,
    "--abi", $abi, "--supportedAbis", $abi
)
Invoke-SdkTool -Arguments @(
    "addTC", "--id", $cxxId, "--language", "Cxx",
    "--name", "Luna ARMv8A G++", "--path", $gxx,
    "--abi", $abi, "--supportedAbis", $abi
)
Invoke-SdkTool -Arguments @(
    "addDebugger", "--id", $debuggerId, "--name", "Luna ARMv8A GDB",
    "--engine", "1", "--binary", $gdb, "--abis", $abi
)
Invoke-SdkTool -Arguments @(
    "addQt", "--id", $qtId, "--name", "Luna Qt 5.15.19 ARMv8A",
    "--qmake", $qmake, "--type", "Qt4ProjectManager.QtVersion.Desktop",
    "--abis", $abi
)
Invoke-SdkTool -AllowFailure -Arguments @(
    "addKit", "--id", $kitId, "--name", "Luna ARMv8A",
    "--devicetype", "Desktop", "--Ctoolchain", $cId,
    "--Cxxtoolchain", $cxxId, "--debuggerid", $debuggerId,
    "--qt", $qtId, "--mkspec", "luna-armv8a", "--sysroot", $sysroot,
    "--env", "MAKEFLAGS=-j4"
)

# sdktool 默认把新增 Kit 标记成临时 SDK 项，Qt Creator 启动时会清理它。
[void][System.IO.Directory]::CreateDirectory("D:\luna-sdk\qt5-5.15.19\config-temp")
Copy-Item -LiteralPath "$settingsDirectory\profiles.xml" -Destination "D:\luna-sdk\qt5-5.15.19\config-temp\profiles.xml" -Force
python "$PSScriptRoot\persist_qtcreator_kit.py" --settings "D:\luna-sdk\qt5-5.15.19\config-temp" --kit-id $kitId
if ($LASTEXITCODE -ne 0) {
    throw "无法固化 Luna ARMv8A Kit"
}
Copy-Item -LiteralPath "D:\luna-sdk\qt5-5.15.19\config-temp\profiles.xml" -Destination "$settingsDirectory\profiles.xml" -Force

Write-Output "Luna ARMv8A Qt Creator Kit 已注册到 $settingsDirectory"
