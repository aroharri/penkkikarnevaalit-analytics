# Ajaa koko putken läpi: Supabase -> DuckDB -> dbt -> mittaristo.
#
#   .\refresh.ps1
#
# Pysähtyy ensimmäiseen virheeseen. Vaatii .env-tiedoston Supabase-tunnuksilla.

# Python ja dbt kirjoittavat lokinsa stderr-kanavaan. PowerShell tulkitsisi sen
# virheeksi jos ErrorActionPreference olisi Stop, joten luotetaan paluukoodeihin.
$ErrorActionPreference = "Continue"
$py = ".\.venv\Scripts\python.exe"
$dbt = ".\.venv\Scripts\dbt.exe"
$t0 = Get-Date

function Step($n, $text) {
    Write-Host ""
    Write-Host "[$n/3] $text" -ForegroundColor Cyan
    Write-Host ("-" * 60)
}

Step 1 "Poiminta: Supabase -> DuckDB raw"
& $py extract\supabase_to_duckdb.py
if ($LASTEXITCODE -ne 0) { Write-Host "Poiminta epaonnistui" -ForegroundColor Red; exit 1 }

Step 2 "Muunnokset ja testit: dbt build"
& $dbt build --profiles-dir .
if ($LASTEXITCODE -ne 0) { Write-Host "dbt build epaonnistui" -ForegroundColor Red; exit 1 }

Step 3 "Mittaristo: marts -> HTML"
& $py reports\build_dashboard.py
if ($LASTEXITCODE -ne 0) { Write-Host "Mittariston rakennus epaonnistui" -ForegroundColor Red; exit 1 }

$secs = [math]::Round(((Get-Date) - $t0).TotalSeconds, 1)
Write-Host ""
Write-Host "Valmis $secs sekunnissa." -ForegroundColor Green
Write-Host "  reports\haastemittaristo.html"
Write-Host ""
Write-Host "Avaa dokumentaatio erikseen:" -ForegroundColor DarkGray
Write-Host "  $py -m http.server 8081 --directory target"
