import io
import math
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# ---------- Config ----------
st.set_page_config(page_title="Atlas Wall Builder", page_icon="🧱", layout="wide")
st.title("🧱 Atlas Wall Builder")
st.caption("Calcule automaticamente o **layout ideal de plywood sheets** com o mínimo de desperdício e simetria.")

# ---------- Inputs ----------
st.sidebar.header("📏 Parede e Porta")
wall_w = st.sidebar.number_input("Largura da parede (mm)", 3000, 20000, 6000, 10)
wall_h = st.sidebar.number_input("Altura da parede (mm)", 2000, 6000, 3000, 10)
door_w = st.sidebar.number_input("Largura da porta (mm)", 0, 3000, 1200, 10)
door_h = st.sidebar.number_input("Altura da porta (mm)", 0, 4000, 2400, 10)

st.sidebar.header("🪵 Sheets")
sheet_w = st.sidebar.number_input("Largura do sheet (mm)", 300, 3000, 1200, 10)
sheet_h = st.sidebar.number_input("Altura do sheet (mm)", 300, 4000, 2400, 10)
gap     = st.sidebar.number_input("Junta entre sheets (mm)", 0, 50, 10, 1)

st.sidebar.header("⚙️ Opções")
layout_type = st.sidebar.selectbox("Tipo de layout", ["Vertical", "Horizontal", "Híbrido", "Otimizar automaticamente"])
show_sizes   = st.sidebar.checkbox("Mostrar medidas nas peças", True)
show_numbers = st.sidebar.checkbox("Numerar peças", True)

# ---------- Funções ----------
def calc_efficiency(w_w, w_h, d_w, d_h, s_w, s_h, g, mode):
    """Cálculo aproximado de área coberta por sheets inteiros (com gap) - remove área da porta."""
    total_wall_area = w_w * w_h
    door_area = max(0, min(d_w, w_w) * min(d_h, w_h))

    if mode in ("Vertical", "Horizontal"):
        cols = max(0, math.floor((w_w + g) / (s_w + g)))
        rows = max(0, math.floor((w_h + g) / (s_h + g)))
        used_area = cols * rows * s_w * s_h
    else:  # Híbrido: base com s_h e topo com s_h/2 (modelo simples)
        cols = max(0, math.floor((w_w + g) / (s_w + g)))
        used_area = cols * s_w * (s_h + max(0, s_h / 2))  # 1 banda cheia + meia banda

    used_area = max(0, used_area - door_area)
    efficiency = used_area / total_wall_area if total_wall_area > 0 else 0
    waste = max(0, 1 - efficiency)
    return efficiency, waste, used_area

def draw_layout(mode):
    fig, ax = plt.subplots(figsize=(10, wall_h / wall_w * 10))
    ax.set_xlim(0, wall_w); ax.set_ylim(0, wall_h); ax.set_aspect("equal"); ax.axis("off")

    # contorno da parede
    ax.add_patch(Rectangle((0, 0), wall_w, wall_h, fill=False, lw=2, edgecolor="black"))

    # porta (centralizada na largura)
    if door_w > 0 and door_h > 0:
        door_x = wall_w/2 - door_w/2
        ax.add_patch(Rectangle((door_x, 0), door_w, door_h, facecolor="white", edgecolor="black", lw=1.6))
        ax.text(door_x + door_w/2, door_h/2, f"Porta\n{int(door_w)}×{int(door_h)}", ha="center", va="center", fontsize=11)

    # peças
    piece_num = 1
    color = "#f3d8b6"

    if mode == "Vertical":
        x = 0
        while x + sheet_w <= wall_w + 0.1:
            y = 0
            while y + sheet_h <= wall_h + 0.1:
                ax.add_patch(Rectangle((x, y), sheet_w, sheet_h, facecolor=color, edgecolor="black"))
                if show_numbers: ax.text(x + sheet_w/2, y + sheet_h/2, f"{piece_num}", ha="center", va="center", fontsize=10, weight="bold")
                if show_sizes:   ax.text(x + sheet_w/2, y + sheet_h - 18, f"{int(sheet_w)}×{int(sheet_h)}", ha="center", va="top", fontsize=8)
                piece_num += 1
                y += sheet_h + gap
            x += sheet_w + gap

    elif mode == "Horizontal":
        y = 0
        while y + sheet_h <= wall_h + 0.1:
            x = 0
            while x + sheet_w <= wall_w + 0.1:
                ax.add_patch(Rectangle((x, y), sheet_w, sheet_h, facecolor=color, edgecolor="black"))
                if show_numbers: ax.text(x + sheet_w/2, y + sheet_h/2, f"{piece_num}", ha="center", va="center", fontsize=10, weight="bold")
                if show_sizes:   ax.text(x + sheet_w/2, y + sheet_h - 18, f"{int(sheet_w)}×{int(sheet_h)}", ha="center", va="top", fontsize=8)
                piece_num += 1
                x += sheet_w + gap
            y += sheet_h + gap

    else:  # Híbrido: faixa inferior cheia + topo com metade da altura do sheet
        # inferior
        x = 0
        while x + sheet_w <= wall_w + 0.1:
            ax.add_patch(Rectangle((x, 0), sheet_w, sheet_h, facecolor=color, edgecolor="black"))
            if show_numbers: ax.text(x + sheet_w/2, sheet_h/2, f"{piece_num}", ha="center", va="center", fontsize=10, weight="bold")
            if show_sizes:   ax.text(x + sheet_w/2, sheet_h - 18, f"{int(sheet_w)}×{int(sheet_h)}", ha="center", va="top", fontsize=8)
            piece_num += 1
            x += sheet_w + gap

        # superior
        y = sheet_h + gap
        h2 = max(0, sheet_h/2)
        while y + h2 <= wall_h + 0.1 and h2 > 0:
            x = 0
            while x + sheet_w <= wall_w + 0.1:
                ax.add_patch(Rectangle((x, y), sheet_w, h2, facecolor=color, edgecolor="black"))
                if show_numbers: ax.text(x + sheet_w/2, y + h2/2, f"{piece_num}", ha="center", va="center", fontsize=10, weight="bold")
                if show_sizes:   ax.text(x + sheet_w/2, y + h2 - 14, f"{int(sheet_w)}×{int(h2)}", ha="center", va="top", fontsize=8)
                piece_num += 1
                x += sheet_w + gap
            y += h2 + gap

    return fig

# ---------- Otimização ----------
# Calcula todos
effs = {}
for lt in ["Vertical", "Horizontal", "Híbrido"]:
    eff, waste, used = calc_efficiency(wall_w, wall_h, door_w, door_h, sheet_w, sheet_h, gap, lt)
    effs[lt] = {
        "Aproveitamento (%)": round(eff * 100, 2),
        "Desperdício (%)": round(waste * 100, 2),
        "Área utilizada (m²)": round(used/1e6, 2)
    }
df_eff = pd.DataFrame(effs).T
best_layout = df_eff["Aproveitamento (%)"].idxmax() if not df_eff.empty else "Vertical"

# Se usuário escolher "Otimizar automaticamente", desenha o vencedor
mode_to_draw = best_layout if layout_type == "Otimizar automaticamente" else layout_type

# ---------- Desenho ----------
fig = draw_layout(mode_to_draw)
st.pyplot(fig)

# ---------- Tabela + Export ----------
st.markdown("---")
st.subheader("📊 Comparativo de Eficiência")
st.dataframe(df_eff.style.highlight_max(subset=["Aproveitamento (%)"], color="#c4f0c2"))

st.success(
    f"🔹 **Layout mais eficiente:** {best_layout} "
    f"({df_eff.loc[best_layout, 'Aproveitamento (%)']}% de aproveitamento, "
    f"{df_eff.loc[best_layout, 'Desperdício (%)']}% de desperdício)"
)

# Exportar Excel
excel_buffer = io.BytesIO()
with pd.ExcelWriter(excel_buffer, engine="openpyxl") as writer:
    df_eff.to_excel(writer, sheet_name="Eficiência")
st.download_button(
    "📥 Baixar tabela (Excel)",
    data=excel_buffer.getvalue(),
    file_name="atlas_wall_efficiency.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
)

# ---------- Alerta de modularidade ----------
mod_fit = (wall_w + gap) % (sheet_w + gap) if (sheet_w + gap) > 0 else 0
if mod_fit != 0:
    st.warning(
        f"⚠️ A largura da parede ({int(wall_w)} mm) não fecha com módulos de {int(sheet_w)}+{int(gap)} mm. "
        f"Considere ajustar para múltiplo próximo de {int(sheet_w + gap)} mm para reduzir cortes."
    )

# Rodapé
st.caption("© Atlas Frames — protótipo. Este cálculo é aproximado; validação final deve considerar recortes de vãos, bordas e tolerâncias.")
