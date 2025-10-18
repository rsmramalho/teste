import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
import math

st.set_page_config(page_title="Atlas Wall Builder", page_icon="🧱", layout="wide")

st.image("https://www.atlasframes.com.au/wp-content/uploads/2023/06/atlas-frames-logo.png", width=250)
st.title("🧱 Atlas Wall Builder")
st.markdown("Calcule automaticamente o **layout ideal de plywood sheets** com o mínimo de desperdício e total simetria.")

# --- Sidebar inputs ---
st.sidebar.header("📏 Medidas da Parede e Porta")

wall_w = st.sidebar.number_input("Largura da parede (mm)", 3000, 10000, 6000, 10)
wall_h = st.sidebar.number_input("Altura da parede (mm)", 2000, 4000, 3000, 10)

door_w = st.sidebar.number_input("Largura da porta (mm)", 600, 2000, 1200, 10)
door_h = st.sidebar.number_input("Altura da porta (mm)", 1800, 3000, 2400, 10)

st.sidebar.header("🪵 Medidas dos Sheets")
sheet_w = st.sidebar.number_input("Largura do sheet (mm)", 600, 2400, 1200, 10)
sheet_h = st.sidebar.number_input("Altura do sheet (mm)", 1200, 3000, 2400, 10)

gap = st.sidebar.number_input("Espaçamento entre sheets (mm)", 0, 50, 10, 1)
show_sizes = st.sidebar.checkbox("Mostrar medidas nas peças", True)
show_numbers = st.sidebar.checkbox("Numerar peças", True)

# --- Layout types ---
layout_type = st.sidebar.selectbox("Tipo de layout", ["Vertical", "Horizontal", "Híbrido", "Otimizar automaticamente"])

# --- Function to calculate efficiency ---
def calc_efficiency(wall_w, wall_h, door_w, door_h, sheet_w, sheet_h, gap, layout_type):
    total_wall_area = wall_w * wall_h
    door_area = door_w * door_h

    if layout_type == "Vertical":
        cols = math.floor((wall_w + gap) / (sheet_w + gap))
        rows = math.floor((wall_h + gap) / (sheet_h + gap))
        used_area = cols * rows * sheet_w * sheet_h

    elif layout_type == "Horizontal":
        cols = math.floor((wall_w + gap) / (sheet_w + gap))
        rows = math.floor((wall_h + gap) / (sheet_h + gap))
        used_area = cols * rows * sheet_w * sheet_h

    else:  # Hybrid
        cols = math.floor((wall_w + gap) / (sheet_w + gap))
        used_area = cols * sheet_w * (sheet_h + sheet_h / 2)  # base + metade no topo

    used_area -= door_area
    efficiency = used_area / total_wall_area
    waste = 1 - efficiency
    return efficiency, waste

# --- Optimization logic ---
effs = {}
for lt in ["Vertical", "Horizontal", "Híbrido"]:
    eff, waste = calc_efficiency(wall_w, wall_h, door_w, door_h, sheet_w, sheet_h, gap, lt)
    effs[lt] = {"Aproveitamento (%)": round(eff * 100, 2), "Desperdício (%)": round(waste * 100, 2)}

best_layout = max(effs, key=lambda k: effs[k]["Aproveitamento (%)"])

if layout_type == "Otimizar automaticamente":
    layout_type = best_layout

# --- Draw wall and layout ---
fig, ax = plt.subplots(figsize=(10, wall_h / wall_w * 10))
ax.set_xlim(0, wall_w)
ax.set_ylim(0, wall_h)
ax.set_aspect("equal")
ax.axis("off")

# Wall outline
ax.add_patch(Rectangle((0, 0), wall_w, wall_h, fill=False, lw=2, edgecolor="black"))

# Door
door_x = wall_w / 2 - door_w / 2
ax.add_patch(Rectangle((door_x, 0), door_w, door_h, facecolor="white", edgecolor="black", lw=1.5))
ax.text(door_x + door_w / 2, door_h / 2, f"Porta\n{door_w:.0f}×{door_h:.0f}", ha="center", va="center", fontsize=10)

# Layout drawing logic
piece_num = 1
color = "#f3d8b6"

if layout_type == "Vertical":
    x = 0
    while x + sheet_w <= wall_w + 0.1:
        y = 0
        while y + sheet_h <= wall_h + 0.1:
            ax.add_patch(Rectangle((x, y), sheet_w, sheet_h, facecolor=color, edgecolor="black"))
            if show_numbers:
                ax.text(x + sheet_w / 2, y + sheet_h / 2, str(piece_num), ha="center", va="center", fontsize=9, weight="bold")
            if show_sizes:
                ax.text(x + sheet_w / 2, y + sheet_h - 20, f"{sheet_w:.0f}×{sheet_h:.0f}", ha="center", va="top", fontsize=7)
            piece_num += 1
            y += sheet_h + gap
        x += sheet_w + gap

elif layout_type == "Horizontal":
    y = 0
    while y + sheet_h <= wall_h + 0.1:
        x = 0
        while x + sheet_w <= wall_w + 0.1:
            ax.add_patch(Rectangle((x, y), sheet_w, sheet_h, facecolor=color, edgecolor="black"))
            if show_numbers:
                ax.text(x + sheet_w / 2, y + sheet_h / 2, str(piece_num), ha="center", va="center", fontsize=9, weight="bold")
            if show_sizes:
                ax.text(x + sheet_w / 2, y + sheet_h - 20, f"{sheet_w:.0f}×{sheet_h:.0f}", ha="center", va="top", fontsize=7)
            piece_num += 1
            x += sheet_w + gap
        y += sheet_h + gap

else:  # Hybrid
    x = 0
    while x + sheet_w <= wall_w + 0.1:
        ax.add_patch(Rectangle((x, 0), sheet_w, sheet_h, facecolor=color, edgecolor="black"))
        if show_numbers:
            ax.text(x + sheet_w / 2, sheet_h / 2, str(piece_num), ha="center", va="center", fontsize=9, weight="bold")
        if show_sizes:
            ax.text(x + sheet_w / 2, sheet_h - 20, f"{sheet_w:.0f}×{sheet_h:.0f}", ha="center", va="top", fontsize=7)
        piece_num += 1
        x += sheet_w + gap

    y = sheet_h + gap
    while y + (sheet_h / 2) <= wall_h + 0.1:
        x = 0
        while x + sheet_w <= wall_w + 0.1:
            ax.add_patch(Rectangle((x, y), sheet_w, sheet_h / 2, facecolor=color, edgecolor="black"))
            if show_numbers:
                ax.text(x + sheet_w / 2, y + sheet_h / 4, str(piece_num), ha="center", va="center", fontsize=9, weight="bold")
            if show_sizes:
                ax.text(x + sheet_w / 2, y + sheet_h / 2 - 20, f"{sheet_w:.0f}×{sheet_h/2:.0f}", ha="center", va="top", fontsize=7)
            piece_num += 1
            x += sheet_w + gap
        y += (sheet_h / 2) + gap

st.pyplot(fig)

# Summary and optimization table
st.markdown("---")
st.subheader("📊 Comparativo de Eficiência")
st.table(effs)
st.success(f"🔹 **Layout mais eficiente:** {best_layout} "
           f"({effs[best_layout]['Aproveitamento (%)']}% aproveitamento, "
           f"{effs[best_layout]['Desperdício (%)']}% desperdício)")
