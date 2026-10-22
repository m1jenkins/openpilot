<#
Moves the Mad Max commits on top of the latest sunnypilot release.

sunnypilot release branches are one squashed commit that is replaced on every release, so a normal
merge doesn't work. The madmax-base tag marks the release our commits currently sit on; this script
rebases madmax-base..madmax onto the new release and moves the tag. It never pushes.

Run from the repo root:
  powershell -ExecutionPolicy Bypass -File sunnypilot\madmax\sync_upstream.ps1
#>
param([string]$UpstreamBranch = "release-mici")

function Fail($msg) { Write-Host $msg -ForegroundColor Red; exit 1 }

if ((git rev-parse --abbrev-ref HEAD) -ne "madmax") { Fail "Check out the madmax branch first." }
if (git status --porcelain) { Fail "You have uncommitted changes. Commit or stash them first." }

$base = git rev-parse --verify -q "madmax-base^{commit}"
if (-not $base) { Fail "madmax-base tag not found. Run: git fetch origin --tags" }

git fetch upstream "+refs/heads/${UpstreamBranch}:refs/remotes/upstream/${UpstreamBranch}"
if ($LASTEXITCODE -ne 0) { Fail "Fetching sunnypilot $UpstreamBranch failed." }

$new = git rev-parse "upstream/$UpstreamBranch"
$newTitle = git log -1 --format=%s $new
if ($new -eq $base) { Write-Host "Already on the latest sunnypilot $UpstreamBranch ($newTitle)."; exit 0 }

$count = git rev-list --count "$base..HEAD"
Write-Host "Moving $count Mad Max commit(s) onto sunnypilot $UpstreamBranch ($newTitle)..."
git rebase --onto $new $base madmax
if ($LASTEXITCODE -ne 0) {
  Write-Host ""
  Write-Host "Conflicts. Fix the files listed above, then: git add <file>; git rebase --continue"
  Write-Host "When the rebase is done, run: git tag -f madmax-base $new"
  Write-Host "To give up and go back: git rebase --abort"
  exit 1
}

git tag -f madmax-base $new | Out-Null
Write-Host ""
Write-Host "Done. Your commits:   git log --oneline madmax-base..madmax"
Write-Host "Publish to GitHub:    git push --force-with-lease origin madmax; git push --force origin madmax-base"
