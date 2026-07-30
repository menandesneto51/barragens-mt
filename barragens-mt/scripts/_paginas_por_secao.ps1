# Diagnostico de paginacao: mostra em que pagina cada titulo do relatorio comeca.
#
# Nao faz parte do pipeline. Serve para saber onde o texto transborda quando o
# documento estoura o limite de paginas do briefing.
#
# Uso: powershell -File scripts\_paginas_por_secao.ps1 <caminho.docx>

param(
    [Parameter(Mandatory = $true)][string]$Documento
)

$caminho = (Resolve-Path $Documento).Path
$word = $null
$doc = $null

try {
    $word = New-Object -ComObject Word.Application
    $word.Visible = $false
    $word.DisplayAlerts = 0
    $doc = $word.Documents.Open($caminho, $false, $true, $false)
    $doc.Repaginate()

    $wdActiveEndPageNumber = 3
    foreach ($p in $doc.Paragraphs) {
        $texto = $p.Range.Text.Trim()
        # Titulos: paragrafo curto e inteiramente em negrito.
        if ($texto.Length -eq 0 -or $texto.Length -gt 90) { continue }
        if (-not $p.Range.Bold) { continue }
        $pagina = $p.Range.Information($wdActiveEndPageNumber)
        Write-Output ("p{0,3}  {1}" -f $pagina, $texto)
    }
    Write-Output ("total: {0} paginas" -f $doc.ComputeStatistics(2))
}
finally {
    if ($doc) { $doc.Close($false) }
    if ($word) { $word.Quit() }
    if ($doc) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc) }
    if ($word) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word) }
    [GC]::Collect()
}
