param(
    [string] $SessionDb = $null,
    [int] $Commits = 10,
    [string] $Output = $null
)

function Run-Git {
    param([string[]] $Args)
    try {
        $out = git @Args 2>$null
        return $out -join "`n"
    } catch {
        return $null
    }
}

$repo = [ordered]@{}
$repo.branch = (Run-Git 'rev-parse' '--abbrev-ref' 'HEAD') -split "`n" | Select-Object -First 1
$repo.status_porcelain = Run-Git 'status' '--porcelain' '--branch'
$log = Run-Git 'log' '--oneline' '-n' $Commits
$repo.recent_commits = if ($log) { $log -split "`n" } else { @() }

$result = [ordered]@{
    generated_at = (Get-Date).ToUniversalTime().ToString('o')
    repo = $repo
}

if ($SessionDb) {
    $session = [ordered]@{}
    if (Test-Path $SessionDb) {
        $sqliteCmd = Get-Command sqlite3 -ErrorAction SilentlyContinue
        if ($sqliteCmd) {
            # Try to dump todos as CSV; requires sqlite3 in PATH
            $csv = & sqlite3 -header -newline "\n" -csv $SessionDb "SELECT id, title, status, description, created_at, updated_at FROM todos ORDER BY created_at;" 2>$null
            $rows = @()
            if ($csv) {
                $lines = $csv -split "`n" | Where-Object { $_ -ne '' }
                if ($lines.Count -gt 0) {
                    $header = $lines[0] -split ','
                    for ($i = 1; $i -lt $lines.Count; $i++) {
                        $vals = $lines[$i] -split ','
                        $obj = [ordered]@{}
                        for ($j = 0; $j -lt $header.Count; $j++) {
                            $obj[$header[$j]] = $vals[$j]
                        }
                        $rows += $obj
                    }
                }
            }
            $session.todos = $rows
        } else {
            $session.error = "sqlite3 not found on PATH; cannot read session DB."
        }
    } else {
        $session.error = "Session DB path not found: $SessionDb"
    }
    $result.session = $session
}

$json = $result | ConvertTo-Json -Depth 5
if ($Output) {
    $json | Out-File -FilePath $Output -Encoding UTF8
    Write-Output "Wrote progress JSON to $Output"
} else {
    Write-Output $json
}
