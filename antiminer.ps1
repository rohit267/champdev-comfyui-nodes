<#
  antiminer.ps1 — Windows counterpart of antiminer.sh. Detect, kill, and remove
  crypto-miners on ComfyUI Windows boxes, and install a scheduled-task watchdog
  that keeps them dead. Conservative: a path whitelist protects the real stack
  (Program Files, WindowsApps, System32, python_embeded, browsers).

  ---------------------------------------------------------------------------
  IOCs observed on 183.6.88.86 (2026-08-27) — same kryptex/pearl operator as 117:
    Miner : C:\Windows\Temp\srb\SRBMiner-Multi-*\SRBMiner-MULTI.exe
            --algorithm pearl --pool stratum+ssl://prl.kryptex.network:8048
            --wallet krxXGNVPW4.<box-ip>-4090
    Task  : "XDMiner" -> C:\ProgramData\Microsoft\DeviceSync\srb\start_srb.bat
    Run   : HKCU\...\Run "ComfyUIEnhancedService" -> comfyui-utils\comfyui_enhanced_boot.pyw
    (the .pyw is a hidden dropper that re-creates the miner + task on ComfyUI boot)

  Same box, 2026-11-07 — "C17 guard v7" strain, built specifically to dodge this
  script: no wallet/pool on the miner's own command line (passed via env vars
  instead), miner binary renamed to blend into a system folder, 6 redundant
  copies of the guard script under different disguises, and 3 scheduled tasks
  with innocuous-sounding names:
    Miner : C:\Windows\System32\drivers\etc\winlogon.dat --worker <id>
            (name/path don't match real winlogon.exe; config in sibling wl.ini)
    Guard copies (kill one, five more relaunch it), one per path below, each
    with its own scheduled task (name harmless, Action points at the file):
            C:\ProgramData\C17Guard\c17guard.ps1
            C:\Windows\System32\drivers\etc\winstore.ps1
            C:\Users\*\AppData\Local\Microsoft\Windows\Caches\d3dcache.ps1
            C:\Windows\System32\spool\drivers\color\srgbcolor.ps1
            C:\ProgramData\Microsoft\Windows\Ringtones\ringtones.ps1
            C:\ProgramData\Microsoft\Diagnosis\ETLLogs\c17diag.ps1
    Pool  : relay stratum+tcp://103.106.191.165:3333, falls back to
            stratum+ssl://prl-sg.kryptex.network:8048 (23.88.2.85/15.235.224.175/40.160.29.14)
    Hosts : poisons C:\Windows\System32\drivers\etc\hosts — points its own pool
            domains straight at an IP (dodges DNS-based blocking) and sinks every
            rival mining-pool domain to 127.0.0.1 (keeps the GPU to itself)
  ---------------------------------------------------------------------------

  Usage (run in an elevated PowerShell / as SYSTEM):
    powershell -ExecutionPolicy Bypass -File antiminer.ps1 scan       # report only (DEFAULT)
    powershell -ExecutionPolicy Bypass -File antiminer.ps1 clean      # kill + remove + block, once
    powershell -ExecutionPolicy Bypass -File antiminer.ps1 install    # clean now + 5-min watchdog task
    powershell -ExecutionPolicy Bypass -File antiminer.ps1 uninstall  # remove the watchdog
    powershell -ExecutionPolicy Bypass -File antiminer.ps1 selftest   # classifier check, no admin
#>
param([string]$Action = "scan")
$ErrorActionPreference = "SilentlyContinue"

# ---- known-bad indicators ---------------------------------------------------
$MinerNames = 'SRBMiner-MULTI|SRBMiner|xmrig|gpu-alloc|procwatch|nbminer|t-rex|phoenixminer|lolminer|rigel|gminer|xmr-stak|cpuminer|teamredminer|XDMiner'
# command line (overrides the whitelist — a miner arg on any binary is still a miner)
$MinerCmd   = 'stratum|kryptex|pearlhash|--algorithm pearl|--pool |--wallet |fleet-id|nicehash|:7048|:8048|:3333|SRBMiner|enhanced_boot|start_srb'
$MinerDirs  = @("$env:windir\Temp\srb", "$env:ProgramData\Microsoft\DeviceSync\srb", "$env:ProgramData\Microsoft\DeviceSync")
# volatile locations no real GPU app runs from
$VolatileRe = '\\Windows\\Temp\\|\\AppData\\Local\\Temp\\|\\ProgramData\\.*\\srb\\'
$BadTaskRe  = 'XDMiner|miner|kryptex|srb|DeviceSync|c17|C17MinerGuard|C17MinerBoot|WinDefenderAssist|ColorCalibrationSvc|RingtoneSyncHelper|DiagTrackHelper'
$BadRunRe   = 'enhanced_boot|start_srb|\\srb\\|DeviceSync\\srb|SRBMiner|xmrig|kryptex'
# payload files referenced by a bad Run entry (delete these, keep the interpreter)
$PayloadRe  = 'enhanced_boot|start_srb|srb|SRBMiner|xmrig|miner|kryptex'
$C2IPs      = @('95.216.136.4','166.117.41.217','192.227.253.100','35.71.142.47','103.106.191.165','23.88.2.85','15.235.224.175','40.160.29.14')
$Whitelist  = 'Program Files|WindowsApps|\\System32\\|\\SysWOW64\\|Microsoft\\Edge|Google\\Chrome|python_embeded|\\Windows\\explorer\.exe|SunloginClient|AweSun|OneDrive'

# "C17 guard v7" (2026-11-07): the miner's own cmdline carries no pool/wallet (env vars
# instead) and it's renamed to blend in, so $MinerCmd/$MinerNames can't see it — these are
# exact disguised paths, checked by equality, not by name or command line.
$MinerFiles = @(
  "$env:windir\System32\drivers\etc\winlogon.dat", "$env:windir\System32\drivers\etc\winlogon.bak",
  "$env:windir\System32\drivers\etc\winstore.dat",  "$env:windir\System32\drivers\etc\winstore.ps1",
  "$env:windir\System32\drivers\etc\wl.ini",
  "$env:windir\System32\spool\drivers\color\srgbsvc.dat", "$env:windir\System32\spool\drivers\color\srgbcolor.ps1",
  "$env:ProgramData\Microsoft\Windows\Ringtones\ringsvc.dat", "$env:ProgramData\Microsoft\Windows\Ringtones\ringtones.ps1",
  "$env:ProgramData\Microsoft\Diagnosis\ETLLogs\diagsvc.dat", "$env:ProgramData\Microsoft\Diagnosis\ETLLogs\c17diag.ps1",
  "$env:ProgramData\C17Guard\c17guard.ps1", "$env:ProgramData\C17Guard\guard.log",
  "C:\Users\*\AppData\Local\Microsoft\Windows\Caches\d3dsvc.dat", "C:\Users\*\AppData\Local\Microsoft\Windows\Caches\d3dcache.ps1",
  "$env:windir\System32\DriverStore\FileRepository\*\c17svc.ps1"
)
# split each path on its literal '*' wildcard, escape the literal parts, rejoin with a
# "any non-backslash chars" class — escaping the whole string first mangles the '*' itself.
$MinerFileRe = ($MinerFiles | ForEach-Object {
  ($_ -split '\*' | ForEach-Object { [regex]::Escape($_) }) -join '[^\\]+'
}) -join '|'
# domains the malware either points at its own pool IP (dodges DNS blocks) or sinks to
# 127.0.0.1 (blocks rival miners from the same GPU) — strip any hosts line naming one.
$BadHostsRe = 'luckypool|suprnova|alphapool\.tech|c3pool|supportxmr|minergate|herominers|2miners\.com|nanopool\.org|ethermine\.org|flexpool\.io|f2pool\.com|poolin\.com|antpool\.com|viabtc\.com|btc\.com|sparkpool\.com|slushpool\.com|braiins\.com|hashvault\.pro|moneroocean|minexmr\.com|xmrpool\.eu|kryptex|startcode\.cyou|pearl[-.]'
$HostsFile  = "$env:windir\System32\drivers\etc\hosts"

$Root = Join-Path $env:ProgramData "antiminer"
$Log  = Join-Path $Root "antiminer.log"
$Self = $MyInvocation.MyCommand.Path
$SrcUrl = if ($env:SRC_URL) { $env:SRC_URL } else { "https://static.champdev.in/antiminer.ps1" }

function Log($m) {
  $line = "[{0}] {1}" -f (Get-Date -Format "yyyy-MM-dd HH:mm:ss"), $m
  Write-Host $line
  try { New-Item -ItemType Directory -Force -Path $Root | Out-Null; Add-Content -Path $Log -Value $line } catch {}
}
function Is-Admin {
  try { return ([Security.Principal.WindowsPrincipal][Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltinRole]::Administrator) } catch { return $false }
}
function Require-Admin { if (-not (Is-Admin)) { Write-Host "run elevated (Administrator) or as SYSTEM"; exit 1 } }

# ---- classifier -------------------------------------------------------------
# returns a reason string if the process is a miner, else $null
function Test-MinerProc($p) {
  $path = $p.ExecutablePath; $cmd = $p.CommandLine; $name = $p.Name
  if ($cmd -and ($cmd -match $MinerCmd)) { return "cmdline: $cmd" }      # overrides whitelist
  if ($name -and ($name -match $MinerNames)) { return "name: $name" }
  if ($path) {
    if ($path -match $MinerFileRe) { return "disguised miner file: $path" }  # stealth cmdline, caught by path
    foreach ($d in $MinerDirs) { if ($path.ToLower().StartsWith($d.ToLower())) { return "miner dir: $path" } }
    if (($path -match $VolatileRe) -and ($path -notmatch $Whitelist)) { return "volatile path: $path" }
  }
  return $null
}

function Get-Miners {
  Get-CimInstance Win32_Process | ForEach-Object {
    $r = Test-MinerProc $_
    if ($r) { [pscustomobject]@{ Pid=$_.ProcessId; Name=$_.Name; Path=$_.ExecutablePath; Reason=$r } }
  }
}

function Get-BadTasks {
  # The payload is often in Arguments, not Execute — a task that runs the whitelisted
  # pythonw.exe/powershell.exe with a disguised script path as its argument is invisible
  # if only Execute is checked. Check the whole command line (+ a fake task-folder name
  # like \Microsoft\Windows\DeviceSync\, cloned to look like a real Windows folder) instead.
  Get-ScheduledTask | Where-Object {
    $line = "$($_.Actions.Execute) $($_.Actions.Arguments)"
    ($_.TaskName -match $BadTaskRe) -or ($_.TaskPath -match $BadTaskRe) -or
    ($line -match 'srb|SRBMiner|miner|\\Temp\\|DeviceSync\\srb') -or
    ($line -match $MinerFileRe)
  }
}

function Clean-Hosts {
  if (-not (Test-Path $HostsFile)) { return }
  $lines = Get-Content $HostsFile
  $bad = $lines | Where-Object { $_ -match $BadHostsRe }
  if (-not $bad) { return }
  if (-not (Test-Path "$HostsFile.pre-antiminer-*")) {
    Copy-Item $HostsFile "$HostsFile.pre-antiminer-$(Get-Date -Format yyyyMMddHHmmss)"
  }
  $lines | Where-Object { $_ -notmatch $BadHostsRe } | Set-Content $HostsFile -Encoding ascii
  Log "stripped $($bad.Count) malicious hosts entries"
}

function Get-BadRun {
  $hits = @()
  foreach ($hive in 'HKLM','HKCU') {
    $rk = "${hive}:\Software\Microsoft\Windows\CurrentVersion\Run"
    $props = Get-ItemProperty $rk
    if (-not $props) { continue }
    foreach ($pr in $props.PSObject.Properties) {
      if ($pr.Name -like 'PS*') { continue }
      if ($pr.Value -match $BadRunRe) {
        $files = [regex]::Matches($pr.Value, '[A-Za-z]:\\[^"'']+?\.(pyw|bat|exe|ps1|vbs|cmd)') | ForEach-Object { $_.Value } | Where-Object { $_ -match $PayloadRe }
        $hits += [pscustomobject]@{ Hive=$hive; Key=$rk; Name=$pr.Name; Value=$pr.Value; Files=$files }
      }
    }
  }
  $hits
}

# ---- actions ----------------------------------------------------------------
function Do-Scan {
  Log "scan start"
  $m = Get-Miners
  if ($m) { Write-Host "SUSPECT miner processes:"; $m | Format-List | Out-String | Write-Host } else { Write-Host "no miner processes." }
  $t = Get-BadTasks
  if ($t) { Write-Host "malicious scheduled tasks:"; $t | Select-Object TaskName,@{n='Exec';e={$_.Actions.Execute}} | Format-Table -Auto | Out-String | Write-Host }
  $r = Get-BadRun
  if ($r) { Write-Host "malicious autoruns + dropper files:"; $r | Format-List Hive,Name,Value,Files | Out-String | Write-Host }
  Write-Host "dirs that would be removed:"; foreach ($d in $MinerDirs) { if (Test-Path $d) { Write-Host "  $d" } }
  Write-Host "disguised files that would be removed:"; foreach ($f in $MinerFiles) { Get-Item $f -ErrorAction SilentlyContinue | ForEach-Object { Write-Host "  $($_.FullName)" } }
  $badHosts = (Get-Content $HostsFile -ErrorAction SilentlyContinue) | Where-Object { $_ -match $BadHostsRe }
  if ($badHosts) { Write-Host "malicious hosts entries: $($badHosts.Count)" }
  Write-Host "firewall blocks that would be added: $($C2IPs -join ', ')"
  Log "scan done"
}

function Do-Clean {
  Log "clean start"
  # 1) kill miner processes
  foreach ($m in Get-Miners) {
    Log "killing pid=$($m.Pid) name=$($m.Name) [$($m.Reason)]"
    Stop-Process -Id $m.Pid -Force
  }
  # 2) remove malicious scheduled tasks
  foreach ($t in Get-BadTasks) {
    Log "removing task $($t.TaskName)"
    Unregister-ScheduledTask -TaskName $t.TaskName -Confirm:$false
  }
  # 3) remove bad Run entries + their dropper payload files
  foreach ($r in Get-BadRun) {
    foreach ($f in $r.Files) {
      if (Test-Path $f) {
        try { attrib -h -s -r $f 2>$null } catch {}
        Remove-Item -Force $f; Log "removed dropper $f"
      }
    }
    Remove-ItemProperty -Path $r.Key -Name $r.Name; Log "removed autorun $($r.Hive)\...\Run\$($r.Name)"
  }
  # 4) remove miner directories
  foreach ($d in $MinerDirs) {
    if (Test-Path $d) {
      try { takeown /f $d /r /d y 2>$null | Out-Null } catch {}
      Remove-Item -Recurse -Force $d; Log "removed dir $d"
    }
  }
  # 5) remove disguised miner/guard files living outside $MinerDirs (one-by-one, not a whole dir)
  foreach ($f in $MinerFiles) {
    Get-Item $f -ErrorAction SilentlyContinue | ForEach-Object {
      try { attrib -h -s -r $_.FullName 2>$null } catch {}
      Remove-Item -Force $_.FullName; Log "removed disguised file $($_.FullName)"
    }
  }
  # 6) undo the hosts-file pool hijack/sinkhole
  Clean-Hosts
  # 7) drop Defender exclusions the malware may have added for those paths
  foreach ($d in $MinerDirs) { Remove-MpPreference -ExclusionPath $d -ErrorAction SilentlyContinue }
  # 8) block egress to known C2/pool infra
  foreach ($ip in $C2IPs) {
    if (-not (Get-NetFirewallRule -DisplayName "antiminer-block-$ip" -ErrorAction SilentlyContinue)) {
      New-NetFirewallRule -DisplayName "antiminer-block-$ip" -Direction Outbound -RemoteAddress $ip -Action Block | Out-Null
      Log "blocked egress to $ip"
    }
  }
  Log "clean done"
}

function Do-Install {
  Require-Admin
  New-Item -ItemType Directory -Force -Path $Root | Out-Null
  $dst = Join-Path $Root "antiminer.ps1"
  if ($Self -and (Test-Path $Self)) { Copy-Item -Force $Self $dst }
  elseif (-not (Test-Path $dst)) {
    try { Invoke-WebRequest -UseBasicParsing $SrcUrl -OutFile $dst } catch { Write-Host "install: no local file and cannot fetch $SrcUrl"; exit 1 }
  }
  Do-Clean   # kill + remove NOW; the watchdog only keeps them dead
  # 5-minute watchdog scheduled task, running as SYSTEM
  $cmd = "powershell.exe -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$dst`" clean"
  schtasks /create /tn "AntiMinerGuard" /tr $cmd /sc MINUTE /mo 5 /ru SYSTEM /rl HIGHEST /f | Out-Null
  schtasks /run /tn "AntiMinerGuard" | Out-Null
  Log "installed watchdog task 'AntiMinerGuard' (every 5 min). log: $Log"
}

function Do-Uninstall {
  Require-Admin
  schtasks /delete /tn "AntiMinerGuard" /f | Out-Null
  Log "uninstalled watchdog task"
}

function Do-Selftest {
  $script:fail = 0
  function chk($n,$cond) { if ($cond) { Write-Host "ok   $n" } else { Write-Host "FAIL $n"; $script:fail = 1 } }
  chk "SRBMiner cmdline flagged"   ('"C:\Windows\Temp\srb\SRBMiner-MULTI.exe" --algorithm pearl --pool stratum+ssl://prl.kryptex.network:8048' -match $MinerCmd)
  chk "enhanced_boot flagged"      ('pythonw.exe comfyui_enhanced_boot.pyw' -match $MinerCmd)
  chk "start_srb run flagged"      ('C:\ProgramData\Microsoft\DeviceSync\srb\start_srb.bat' -match $BadRunRe)
  chk "legit comfy cmd NOT flagged" (-not ('E:\ComfyUI\python_embeded\python.exe main.py --listen' -match $MinerCmd))
  chk "chrome NOT flagged"         (-not ('C:\Program Files\Google\Chrome\Application\chrome.exe' -match $VolatileRe))
  chk "temp exe is volatile"       ('C:\Windows\Temp\srb\x.exe' -match $VolatileRe)
  chk "python_embeded whitelisted" ('E:\ComfyUI\python_embeded\python.exe' -match $Whitelist)
  chk "stealth winlogon.dat flagged by path despite clean cmdline" ("$env:windir\System32\drivers\etc\winlogon.dat" -match $MinerFileRe)
  chk "disguised guard copy (Caches) flagged"   ("C:\Users\bob\AppData\Local\Microsoft\Windows\Caches\d3dcache.ps1" -match $MinerFileRe)
  chk "real System32 file NOT flagged as disguised" (-not ("$env:windir\System32\drivers\etc\hosts" -match $MinerFileRe))
  chk "C17MinerGuard task name flagged"   ('C17MinerGuard' -match $BadTaskRe)
  chk "WinDefenderAssist task name flagged" ('WinDefenderAssist' -match $BadTaskRe)
  chk "luckypool hosts line flagged"   ('103.199.106.122 pearl-hk.luckypool.io' -match $BadHostsRe)
  chk "real hosts line NOT flagged"    (-not ('127.0.0.1 localhost' -match $BadHostsRe))
  chk "DeviceSync task folder flagged" ('\Microsoft\Windows\DeviceSync\' -match $BadTaskRe)
  chk "c17svc.ps1 in Arguments flagged" ("$env:windir\System32\DriverStore\FileRepository\prnms001.inf_x86_msvc\c17svc.ps1" -match $MinerFileRe)
  if ($script:fail -eq 0) { Write-Host "selftest passed" } else { Write-Host "selftest FAILED"; exit 1 }
}

# ---- dispatch ---------------------------------------------------------------
switch ($Action.ToLower()) {
  "scan"      { Do-Scan }
  "clean"     { Require-Admin; Do-Clean }
  "install"   { Do-Install }
  "uninstall" { Do-Uninstall }
  "selftest"  { Do-Selftest }
  default     { Write-Host "usage: antiminer.ps1 {scan|clean|install|uninstall|selftest}"; exit 2 }
}
