"""Processa escalonamentos do ciclo de alerta (prazos vencidos).

Uso:
  python scripts/55_ciclo_alerta_escalonamento.py
  python executar.py 55
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from st_app.ciclo_alerta import (  # noqa: E402
    carregar_alertas,
    processar_escalonamentos,
    resumo_ciclo,
)


def main() -> int:
    antes = resumo_ciclo()
    eventos = processar_escalonamentos()
    depois = resumo_ciclo()
    print(
        f"alertas={depois['n_emitidos']} aguardando={depois['n_aguardando']} "
        f"escalonados={depois['n_escalonados']} max={depois['n_escalonado_maximo']} "
        f"eventos_agora={len(eventos)}"
    )
    if eventos:
        for e in eventos[:10]:
            print(
                f"  {e['id_alerta']}: {e['estado_anterior']} → {e['estado_novo']} "
                f"({e['motivo'][:60]})"
            )
    elif antes["n_aguardando"] == 0 and antes["n_escalonados"] == 0:
        al = carregar_alertas()
        if al.empty:
            print("sem alertas no ciclo — emita pela tela Alertabilidade / despacho")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
