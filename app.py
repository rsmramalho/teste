import io
import math
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# ========== CONFIG ==========
st.set_page_config(page_title="Atlas Wall Builder", page_icon="🧱", layout="wide")
st.title("🧱 Atlas Wall Builder v1.2")
st.caption("Layout com recorte automático da porta, cortes em múltiplos e lista de peças.")

# ========== INPUTS ==========
st.sidebar.header("📏 Parede e Porta")
wall_w = st.sidebar.number_input("Largura da parede (mm)", 3000, 20000, 6040, 10)
wall_h = st.sidebar.number_input("Altura da parede (mm)", 2000, 6000, 3010, 10)

door_w = st.sidebar.number_input("Largura da porta (mm)", 0, 3000, 1200, 10)
door_h = st.sidebar.number_input("Altura da porta (mm)", 0, 4000, 2400, 10)
door_x_mode = st.sidebar.selectbox("Posição da porta", ["Centralizada", "Custom (slider)", "Alinhar à junta/grade"])
door_x_custom = st.sidebar.slider("Deslocamento da porta a partir da esquerda (mm)", 0, int(wall_w), int(wall_w//2), 10)

st.sidebar.header("🪵 Sheets")
sheet_w = st.sidebar.number_input("Largura do sheet (mm)", 300, 3000, 1200, 10)
sheet_h = st.sidebar.number_input("Altura do sheet (mm)", 300, 4000, 2400, 10)
gap     = st.sidebar.number_input("Junta entre sheets (mm)", 0, 50, 10, 1)

st.sidebar.header("⚙️ Opções")
layout_type = st.sidebar.selectbox("Tipo de layout", ["Vertical", "Horizontal", "Híbrido", "Otimizar automaticamente"])
grid_step   = st.sidebar.number_input("Grade de múltiplos (mm)", 50, 600, 300, 50)
auto_mod    = st.sidebar.checkbox("Ajustar parede para fechar módulos", True)
show_sizes   = st.sidebar.checkbox("Mostrar medidas nas peças", True)
show_numbers = st.sidebar.checkbox("Numerar peças", True)

# ========== HELPERS ==========
def snap_dimension(total, module, g):
    """fecha no maior múltiplo <= total (n*module + (n-1)*gap)"""
    if module + g <= 0: return total
    n = max(1, math.floor((total + g) / (module + g)))
    return n*module + (n-1)*g

def snap_to_grid(x, step):
    """alinha à grade (múltiplos)"""
    return round(x / step) * step

def rect_subtract(rect, hole):
    """
    Subtrai 'hole' de 'rect'. Ambos: (x, y, w, h), y=0 no piso.
    Retorna 0..4 retângulos restantes.
    """
    rx, ry, rw, rh = rect
    hx, hy, hw, hh = hole
    out = []

    # interseção
    ix = max(rx, hx)
    iy = max(ry, hy)
    ax = min(rx+rw, hx+hw)
    ay = min(ry+rh, hy+hh)
    if ix >= ax or iy >= ay:
        return [rect]  # sem sobreposição

    # esquerda
    if ix > rx:
        out.append((rx, ry, ix - rx, rh))
    # direita
    if ax < rx + rw:
        out.append((ax, ry, (rx + rw) - ax, rh))
    # baixo
    if iy > ry:
        out.append((ix, ry, ax - ix, iy - ry))
    # topo
    if ay < ry + rh:
        out.append((ix, ay, ax - ix, (ry + rh) - ay))

    return out

def pieces_intersecting_door(pieces, door):
    """Divide todas as peças que cruzam a porta."""
    result = []
    for r in pieces:
        sub = rect_subtract(r, door)
        result.extend(sub)
    return result

def build_grid(mode, W, H, sw, sh, g):
    """
    Cria peças-base (sem recorte da porta).
    - Vertical: colunas de sw, linhas de sh; topo = resto
    - Horizontal: linhas de sh, colunas de sw; topo = resto
    - Híbrido: 1 faixa base (sh) + topo resto
    Retorna lista de retângulos (x, y, w, h)
    """
    pieces = []
    if mode == "Vertical":
        cols = max(0, math.floor((W + g) / (sw + g)))
        rows = max(0, math.floor((H + g) / (sh + g)))
        rem_h = H - (rows*sh + max(0, rows-1)*g)

        x0 = 0
        for c in range(cols):
            y0 = 0
            for r in range(rows):
                pieces.append((x0, y0, sw, sh))
                y0 += sh + g
            if rem_h >= 1:
                pieces.append((x0, H - rem_h, sw, rem_h))
            x0 += sw + g

    elif mode == "Horizontal":
        cols = max(0, math.floor((W + g) / (sw + g)))
        rows = max(0, math.floor((H + g) / (sh + g)))
        rem_h = H - (rows*sh + max(0, rows-1)*g)

        y0 = 0
        for r in range(rows):
            x0 = 0
            for c in range(cols):
                pieces.append((x0, y0, sw, sh))
                x0 += sw + g
            y0 += sh + g
        if rem_h >= 1:
            x0 = 0
            for c in range(cols):
                pieces.append((x0, H - rem_h, sw, rem_h))
                x0 += sw + g

    else:  # Híbrido: base cheia sh + topo resto
        cols = max(0, math.floor((W + g) / (sw + g)))
        rem_h = H - (sh + g)
        x0 = 0
        for c in range(cols):
            pieces.append((x0, 0, sw, sh))
            x0 += sw + g
        if rem_h >= 1:
            x0 = 0
            for c in range(cols):
                pieces.append((x0, H - rem_h, sw, rem_h))
                x0 += sw + g

    return pieces

def format_mm(v): return f"{int(round(v))}"

# ========== AJUSTES ==========
if auto_mod:
    wall_w = snap_dimension(wall_w, sheet_w, gap)
    # garante pelo menos a banda superior (ex.: 600) se H > sheet_h
    if wall_h > sheet_h:
        wall_h = snap_dimension(wall_h, sheet_h, gap)

# posição da porta
if door_w > 0 and door_h > 0:
    if door_x_mode == "Centralizada":
        door_x = wall_w/2 - door_w/2
    elif door_x_mode == "Custom (slider)":
        door_x = max(0, min(door_x_custom, wall_w - door_w))
    else:  # alinhar à junta/grade
        # alinha à grade de sw + gap (juntas) e também à grade fina 'grid_step'
        raw = wall_w/2 - door_w/2
        door_x = snap_to_grid(raw, grid_step)
        # não ultrapassar limites
        door_x = max(0, min(door_x, wall_w - door_w))
else:
    door_x = 0

door_rect = (door_x, 0, door_w, door_h)

# ========== OTIMIZAÇÃO ==========
def calc_efficiency(W, H, d_w, d_h, sw, sh, g, mode):
    total = W * H
    base_pieces = build_grid(mode, W, H, sw, sh, g)
    used_area = sum(w*h for (_, _, w, h) in base_pieces)
    used_area -= d_w * d_h  # porta vira vazio
    used_area = max(0, used_area)
    eff = used_area / total if total > 0 else 0
    return eff, 1 - eff, used_area, base_pieces

effs = {}
candidates = ["Vertical", "Horizontal", "Híbrido"]
for lt in candidates:
    eff, waste, used, _ = calc_efficiency(wall_w, wall_h, door_w, door_h, sheet_w, sheet_h, gap, lt)
    effs[lt] = {"Aproveitamento (%)": round(eff*100, 2),
                "Desperdício (%)": round(waste*100, 2),
                "Área utilizada (m²)": round(used/1e6, 2)}
df_eff = pd.DataFrame(effs).T
best_layout = df_eff["Aproveitamento (%)"].idxmax() if not df_eff.empty else "Vertical"

mode_to_draw = best_layout if layout_type == "Otimizar automaticamente" else layout_type

# ========== CONSTRÓI PEÇAS + RECORTE ==========
base_pieces = build_grid(mode_to_draw, wall_w, wall_h, sheet_w, sheet_h, gap)
# subtrai a porta
cut_pieces = pieces_intersecting_door(base_pieces, door_rect)

# remove peças muito pequenas (≤ 5 mm em qualquer dimensão)
filtered = []
for (x,y,w,h) in cut_pieces:
    if w > 5 and h > 5:
        # aplica grade de múltiplos (opcional: só arredonda para baixo)
        w = snap_to_grid(w, grid_step)
        h = snap_to_grid(h, grid_step)
        if w >= grid_step and h >= grid_step:
            filtered.append((x, y, w, h))

# ========== DESENHO ==========
fig, ax = plt.subplots(figsize=(10, wall_h / wall_w * 10))
ax.set_xlim(0, wall_w); ax.set_ylim(0, wall_h); ax.set_aspect("equal"); ax.axis("off")

# contorno
ax.add_patch(Rectangle((0, 0), wall_w, wall_h, fill=False, lw=2, edgecolor="black"))

# peças
color = "#f3d8b6"
rows = []
for idx, (x,y,w,h) in enumerate(filtered, start=1):
    ax.add_patch(Rectangle((x, y), w, h, facecolor=color, edgecolor="black"))
    if show_numbers:
        ax.text(x+w/2, y+h/2, f"{idx}", ha="center", va="center", fontsize=10, weight="bold")
    if show_sizes:
        ax.text(x+w/2, y+h-16, f"{format_mm(w)}×{format_mm(h)}", ha="center", va="top", fontsize=8)
    rows.append({"#": idx, "Largura (mm)": int(round(w)), "Altura (mm)": int(round(h))})

# porta por cima (visível)
if door_w > 0 and door_h > 0:
    ax.add_patch(Rectangle((door_x, 0), door_w, door_h, facecolor="white", edgecolor="black", lw=1.8))
    ax.text(door_x + door_w/2, door_h/2, f"Porta\n{int(door_w)}×{int(door_h)}",
            ha="center", va="center", fontsize=11, weight="bold")

st.pyplot(fig)

# ========== TABELAS E EXPORTAÇÕES ==========
st.markdown("---")
st.subheader("📋 Lista de peças (após recorte)")
df_pieces = pd.DataFrame(rows)
if df_pieces.empty:
    st.info("Nenhuma peça após o recorte — ajuste as dimensões ou a grade.")
else:
    st.dataframe(df_pieces)

    # download CSV
    csv = df_pieces.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Baixar lista de peças (CSV)", data=csv, file_name="atlas_wall_cortes.csv", mime="text/csv")

st.subheader("📊 Comparativo de Eficiência (antes do recorte)")
st.dataframe(df_eff.style.highlight_max(subset=["Aproveitamento (%)"], color="#c4f0c2"))

# ajuste de modularidade (alerta)
mod_fit = (wall_w + gap) % (sheet_w + gap) if (sheet_w + gap) > 0 else 0
if mod_fit != 0:
    st.warning(
        f"⚠️ A largura da parede ({int(wall_w)} mm) não fecha com módulos de {int(sheet_w)}+{int(gap)} mm. "
        f"Considere ajustar para múltiplos de {int(sheet_w + gap)} mm."
    )

st.caption("© Atlas Frames — v1.2. O recorte usa grade de múltiplos (default 300 mm) e remove peças mínimas.")
