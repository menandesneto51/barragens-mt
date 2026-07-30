"""Gera GIF animado da simulação volume → área (cenário Manso por padrão).

Saídas:
  figuras/simulacao_manso_volume_area.gif
  painel/media/simulacao_manso_volume_area.gif  (cópia para o painel)

Não é dam break: animação didática da lâmina equivalente.
"""

from __future__ import annotations

import csv
from pathlib import Path

import comum

try:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    from matplotlib import patches
    from matplotlib.animation import FuncAnimation, PillowWriter
except ImportError as exc:  # pragma: no cover
    raise SystemExit(f"matplotlib necessário: {exc}") from exc


def barragem_manso() -> dict:
    caminho = comum.DADOS_TRATADOS / "inventario_barragens_mt.csv"
    with caminho.open(encoding="utf-8-sig", newline="") as arquivo:
        for r in csv.DictReader(arquivo, delimiter=";"):
            nome = (r.get("nome") or "").upper()
            if "UHE MANSO" in nome and "LEITO DO RIO" in nome:
                return r
        raise SystemExit("UHE Manso (leito) não encontrada no inventário")


def main() -> None:
    b = barragem_manso()
    vol = float(str(b["capacidade_hm3"]).replace(",", "."))
    lat = float(str(b["latitude"]).replace(",", "."))
    lon = float(str(b["longitude"]).replace(",", "."))
    nome = b["nome"]
    profundidade = 2.0  # m — mesmo default do painel
    frames = 40
    frac_final = 0.5

    fig, ax = plt.subplots(figsize=(8.5, 7.2), dpi=120)
    fig.patch.set_facecolor("#f4efe8")
    ax.set_facecolor("#e8eef2")

    # Contexto: Cuiabá aproximado
    ax.scatter([-56.1], [-15.6], s=40, c="#0b6e4f", zorder=5, label="Cuiabá (ref.)")
    ax.scatter([lon], [lat], s=80, c="#9a3412", zorder=6, label="UHE Manso")

    circ = patches.Circle(
        (lon, lat),
        radius=0.01,
        facecolor="#fb923c",
        edgecolor="#c2410c",
        alpha=0.35,
        linewidth=1.5,
        linestyle="--",
        zorder=4,
    )
    ax.add_patch(circ)

    titulo = ax.set_title("", fontsize=12, pad=10)
    ax.set_xlabel("Longitude")
    ax.set_ylabel("Latitude")
    ax.legend(loc="upper right", fontsize=9)
    ax.set_aspect("equal", adjustable="box")
    ax.grid(True, alpha=0.25)
    ax.text(
        0.02,
        0.02,
        "SIMULAÇÃO — não é previsão de rompimento nem mancha do PAE\n"
        "área_km² = (volume_hm³ × fração) / profundidade_m",
        transform=ax.transAxes,
        fontsize=8,
        color="#7c2d12",
        va="bottom",
    )

    def atualizar(i: int):
        frac = frac_final * (i + 1) / frames
        liberado = vol * frac
        area = liberado / profundidade
        # graus ≈ km / 111
        raio_deg = (area / 3.14159265) ** 0.5 / 111.0
        circ.set_radius(max(raio_deg, 0.02))
        # janela acompanha o crescimento
        margem = max(raio_deg * 1.8, 0.35)
        ax.set_xlim(lon - margem, lon + margem * 1.4)
        ax.set_ylim(lat - margem * 1.3, lat + margem)
        titulo.set_text(
            f"{nome}\n"
            f"fração {frac*100:.0f}% · liberado {liberado:,.0f} hm³ · "
            f"área equiv. {area:,.0f} km² · lâmina {profundidade:.0f} m"
        )
        return (circ, titulo)

    anim = FuncAnimation(fig, atualizar, frames=frames, interval=120, blit=False)

    pasta_fig = comum.RAIZ / "figuras"
    pasta_media = comum.RAIZ / "painel" / "media"
    pasta_fig.mkdir(parents=True, exist_ok=True)
    pasta_media.mkdir(parents=True, exist_ok=True)
    destino = pasta_fig / "simulacao_manso_volume_area.gif"
    writer = PillowWriter(fps=8)
    anim.save(destino, writer=writer)
    copia = pasta_media / destino.name
    copia.write_bytes(destino.read_bytes())
    plt.close(fig)
    print(f"  gravado {destino.relative_to(comum.RAIZ)} ({destino.stat().st_size/1024:.0f} KB)")
    print(f"  cópia {copia.relative_to(comum.RAIZ)}")


if __name__ == "__main__":
    main()
