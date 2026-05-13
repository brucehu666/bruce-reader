# 获取所有安装的语音（包括传统SAPI和新OneCore语音）

Write-Host "=== 正在检测系统语音 ==="
Write-Host ""

# 方法1: 传统SAPI语音
try {
    Write-Host "[传统 SAPI 语音]"
    $speaker = New-Object -ComObject SAPI.SpVoice
    $voices = $speaker.GetVoices()
    
    if ($voices.Count -eq 0) {
        Write-Host "  未找到传统SAPI语音"
    } else {
        for ($i = 0; $i -lt $voices.Count; $i++) {
            $voice = $voices.Item($i)
            Write-Host "  [$i] $($voice.GetDescription())"
        }
    }
} catch {
    Write-Host "  错误: $_"
}

Write-Host ""

# 方法2: OneCore语音（Windows 10+ 新引擎）- 使用不同的方式读取
try {
    Write-Host "[OneCore 语音（Windows 10+）]"
    $regPath = "HKLM:\SOFTWARE\Microsoft\Speech_OneCore\Voices\Tokens"
    
    if (Test-Path $regPath) {
        $voiceTokens = Get-ChildItem $regPath
        
        if ($voiceTokens.Count -eq 0) {
            Write-Host "  未找到OneCore语音"
        } else {
            $index = 0
            foreach ($token in $voiceTokens) {
                # 直接获取键名作为语音标识
                $voiceName = $token.Name.Split('\')[-1]
                Write-Host "  [$index] $voiceName"
                $index++
            }
        }
    } else {
        Write-Host "  OneCore语音注册表路径不存在"
    }
} catch {
    Write-Host "  错误: $_"
}

Write-Host ""
Write-Host "=== 检测完成 ==="