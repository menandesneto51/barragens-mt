# Conta as paginas do relatorio usando o proprio Word, via COM nativo do PowerShell.
#
# Nao faz parte do pipeline. Existe porque o briefing impoe minimo de 6 e maximo de 10
# paginas incluindo capa e referencias, com anexos fora da contagem, e nenhuma biblioteca
# de geracao de .docx sabe paginar: so o Word (ou um conversor equivalente) repagina.
#
# Uso: powershell -File scripts\_contar_paginas.ps1 <caminho.docx>

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

    # ReadOnly e AddToRecentFiles desligados para nao alterar nada no ambiente do usuario.
    $doc = $word.Documents.Open($caminho, $false, $true, $false)
    $doc.Repaginate()

    $wdStatisticPages = 2
    $totalPaginas = $doc.ComputeStatistics($wdStatisticPages)
    $totalPalavras = $doc.ComputeStatistics(0)

    Write-Output "arquivo: $([System.IO.Path]::GetFileName($caminho))"
    Write-Output "paginas totais (com anexos): $totalPaginas"
    Write-Output "palavras: $totalPalavras"

    # Localiza onde comecam os anexos, porque eles nao entram na contagem exigida.
    $wdActiveEndPageNumber = 3
    $intervalo = $doc.Content
    $busca = $intervalo.Find
    # Com MatchCase: os titulos primarios estao em caixa alta, e o corpo cita "Anexo A"
    # em caixa mista. Sem distinguir, a busca pararia na citacao e nao no titulo.
    $busca.Text = "ANEXO A"
    $busca.Forward = $true
    $busca.MatchCase = $true
    $busca.Wrap = 0

    if ($busca.Execute()) {
        $paginaAnexo = $intervalo.Information($wdActiveEndPageNumber)
        $paginasContadas = $paginaAnexo - 1
        Write-Output "anexos comecam na pagina: $paginaAnexo"
        Write-Output "paginas que contam (capa ate referencias): $paginasContadas"
        if ($paginasContadas -lt 6) {
            Write-Output "RESULTADO: ABAIXO DO MINIMO (exigido 6 a 10)"
        }
        elseif ($paginasContadas -gt 10) {
            Write-Output "RESULTADO: ACIMA DO MAXIMO (exigido 6 a 10)"
        }
        else {
            Write-Output "RESULTADO: DENTRO DO EXIGIDO (6 a 10)"
        }
    }
    else {
        Write-Output "nao localizei o inicio dos anexos"
    }
}
finally {
    if ($doc) { $doc.Close($false) }
    if ($word) { $word.Quit() }
    if ($doc) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc) }
    if ($word) { [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word) }
    [GC]::Collect()
}
