import io
import math
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# ========== CONFIG ==========
st.set_page_config(page_title="Atlas Wall Builder", page_icon="🧱", layout="wide")
st.title("🧱 Atlas Wall Builder v1.2.2")
st.caption("Recorte automático da porta, cortes em múltiplos, preenchimento das laterais e lista de peças.")

# ========== INPUTS ==========
st.sidebar.header("📏 Parede e Porta")
wall_w = st.sidebar.number_input("Largura da parede (mm)", 3000, 20000, 6040, 10)
wall_h = st.sidebar.number_input("Altura da parede (mm)", 2000, 6000, 3010, 10)

door_w = st.sidebar.number_input("Largura da porta (mm)", 0, 3000, 2400, 10)
door_h = st.sidebar.number_input("Altura da porta (mm)", 0, 4000, 2400, 10)
door_x_mode = st.sidebar.selectbox("Posição da porta", ["Centralizada", "Custom (slider)", "Alinhar à junta/grade"])
door_x_custom = st.sidebar.slider("Deslocamento da porta a partir da esquerda (mm)", 0, int(wall_w), int(wall_w//2), 10)

st.sidebar.header("🪵 Sheets")
sheet_w = st.sidebar.number_input("Largura do sheet (mm)", 300, 3000, 1200, 10)
sheet_h = st.sidebar.number_input("Altura do sheet (mm)", 300, 4000, 2400, 10)
gap     = st.sidebar.number_input("Junta entre sheets (mm)", 0, 50, 10, 1)

st.sidebar.header("⚙️ Opções")
layout_type = st.sidebar.selectbox("Tipo de layout", ["Vertical", "Horizontal", "Híbrido", "Otimizar automaticamente"])
grid_step   = st.sidebar.number_input("Grade de múltiplos (mm)", 50, 600, 300, 50)  # ex.: 300
auto_mod    = st.sidebar.checkbox("Ajustar parede para fechar módulos", True)
merge_sill  = st.sidebar.checkbox("Fundir testas pequenas acima da porta (≤ grade)", True)
cut_in_place = st.sidebar.checkbox("Cortar no local (mostrar chapas atrás da porta)", False)
show_sizes   = st.sidebar.checkbox("Mostrar medidas nas peças", True)
show_numbers = st.sidebar.checkbox("Numerar peças", True)

# ========== HELPERS ==========
def snap_dimension(total, module, g):
    """fecha no maior múltiplo <= total (n*module + (n-1)*gap)"""
    if module + g <= 0: return total
    n = max(1, math.floor((total + g) / (module + g)))
    return n*module + (n-1)*g

def snap_to_grid(v, step):
    """alinha para múltiplo mais próximo (para baixo)"""
    return (int(v) // int(step)) * int(step)

def rect_subtract(rect, hole):
    """Subtrai 'hole' de 'rect'. Ambos (x, y, w, h). Retorna lista de retângulos restantes."""
    rx, ry, rw, rh = rect
    hx, hy, hw, hh = hole
    ix = max(rx, hx);  ax = min(rx+rw, hx+hw)
    iy = max(ry, hy);  ay = min(ry+rh, hy+hh)
    if ix >= ax or iy >= ay:
        return [rect]  # sem sobreposição
    out = []
    if ix > rx: out.append((rx, ry, ix - rx, rh))                        # esquerda
    if ax < rx+rw: out.append((ax, ry, (rx + rw) - ax, rh))              # direita
    if iy > ry: out.append((ix, ry, ax - ix, iy - ry))                   # baixo
    if ay < ry+rh: out.append((ix, ay, ax - ix, (ry + rh) - ay))         # topo
    return out

def build_grid(mode, W, H, sw, sh, g):
    """Gera peças-base (sem recorte da porta)."""
    pcs = []
    if mode == "Vertical":
        cols = max(0, math.floor((W + g) / (sw + g)))
        rows = max(0, math.floor((H + g) / (sh + g)))
        rem_h = H - (rows*sh + max(0, rows-1)*g)
        x0 = 0
        for _ in range(cols):
            y0 = 0
            for _ in range(rows):
                pcs.append((x0, y0, sw, sh)); y0 += sh + g
            if rem_h >= 1: pcs.append((x0, H - rem_h, sw, rem_h))
            x0 += sw + g
    elif mode == "Horizontal":
        cols = max(0, math.floor((W + g) / (sw + g)))
        rows = max(0, math.floor((H + g) / (sh + g)))
        rem_h = H - (rows*sh + max(0, rows-1)*g)
        y0 = 0
        for _ in range(rows):
            x0 = 0
            for _ in range(cols):
                pcs.append((x0, y0, sw, sh)); x0 += sw + g
            y0 += sh + g
        if rem_h >= 1:
            x0 = 0
            for _ in range(cols):
                pcs.append((x0, H - rem_h, sw, rem_h)); x0 += sw + g
    else:  # Híbrido: base sh + topo resto
        cols = max(0, math.floor((W + g) / (sw + g)))
        rem_h = H - (sh + g)
        x0 = 0
        for _ in range(cols):
            pcs.append((x0, 0, sw, sh)); x0 += sw + g
        if rem_h >= 1:
            x0 = 0
            for _ in range(cols):
                pcs.append((x0, H - rem_h, sw, rem_h)); x0 += sw + g
    return pcs

def format_mm(v): return f"{int(round(v))}"

def merge_small_headers(pieces, door, threshold):
    """Funde 'testas' pequenas coladas ao topo da porta com a peça imediatamente acima."""
    dx, dy, dw, dh = door
    top_edge = dy + dh
    headers = []
    uppers  = []
    for (x, y, w, h) in pieces:
        if abs(y - top_edge) <= 1 and x <= dx and x + w >= dx + dw:
            headers.append((x, y, w, h))
        if y > top_edge and x <= dx and x + w >= dx + dw:
            uppers.append((x, y, w, h))
    for hdr in headers:
        hx, hy, hw, hh = hdr
        if hh <= threshold + 1:
            match = None
            for u in uppers:
                ux, uy, uw, uh = u
                if abs(uy - (hy + hh)) <= 1 and ux == hx and uw == hw:
                    match = u; break
            if match:
                pieces.remove(hdr); pieces.remove(match)
                ux, uy, uw, uh = match
                pieces.append((hx, hy, hw, hh + uh))
    return pieces

def add_door_side_panels(pieces, door, sw, g, step, W, H):
    """
    PREENCHE as FAIXAS LATERAIS da porta se a porta 'comeu' uma coluna no meio.
    Calcula a largura exata dentro da coluna de sheet onde a borda da porta cai.
    """
    dx, dy, dw, dh = door
    final = pieces[:]

    # esquerda da porta: se a borda esquerda está DENTRO de uma coluna, cria a faixa remanescente
    module = sw + g if sw + g > 0 else sw
    k_left = int(dx // module)
    start_left = k_left * module          # início da coluna onde a borda cai
    within_left = dx - start_left         # sobra dentro da coluna à esquerda
    if 0 < within_left < sw:
        w_left = snap_to_grid(within_left, step)
        if w_left >= step:
            final.append((dx - w_left, 0, w_left, min(dh, H)))

    # direita da porta: se a borda direita está DENTRO de uma coluna, cria a faixa remanescente
    right = dx + dw
    k_right = int(right // module)
    start_right = k_right * module
    within_right = right - start_right
    if 0 < within_right < sw:
        w_right = snap_to_grid(sw - within_right, step)
        if w_right >= step:
            final.append((right, 0, w_right, min(dh, H)))

    return final

def overlaps(r, hole):
    rx, ry, rw, rh = r
    hx, hy, hw, hh = hole
    return not (rx+rw <= hx or hx+hw <= rx or ry+rh <= hy or hy+hh <= ry)

# ========== AJUSTES ==========
if auto_mod:
    wall_w = snap_dimension(wall_w, sheet_w, gap)
    rows = max(1, math.floor((wall_h + gap) / (sheet_h + gap)))
    snap_down = rows*sheet_h + (rows-1)*gap
    remainder = wall_h - snap_down
    wall_h = snap_down if remainder < grid_step else int(wall_h)

# posição da porta
if door_w > 0 and door_h > 0:
    if door_x_mode == "Centralizada":
        door_x = wall_w/2 - door_w/2
    elif door_x_mode == "Custom (slider)":
        door_x = max(0, min(door_x_custom, wall_w - door_w))
    else:  # alinhar à grade
        raw = wall_w/2 - door_w/2
        door_x = max(0, min(snap_to_grid(raw, grid_step), wall_w - door_w))
else:
    door_x = 0

door_rect = (door_x, 0, door_w, door_h)

# ========== OTIMIZAÇÃO (resumo) ==========
def calc_efficiency(W, H, d_w, d_h, sw, sh, g, mode):
    total = W * H
    base = build_grid(mode, W, H, sw, sh, g)
    used = sum(w*h for (_, _, w, h) in base) - d_w*d_h
    used = max(0, used)
    eff = used/total if total > 0 else 0
    return eff, 1-eff, used

effs = {}
for lt in ["Vertical", "Horizontal", "Híbrido"]:
    e,w,u = calc_efficiency(wall_w, wall_h, door_w, door_h, sheet_w, sheet_h, gap, lt)
    effs[lt] = {"Aproveitamento (%)": round(e*100, 2), "Desperdício (%)": round(w*100, 2), "Área utilizada (m²)": round(u/1e6, 2)}
df_eff = pd.DataFrame(effs).T
best_layout = df_eff["Aproveitamento (%)"].idxmax() if not df_eff.empty else "Vertical"
mode_to_draw = best_layout if layout_type == "Otimizar automaticamente" else layout_type

# ========== PEÇAS + RECORTE ==========
base_pieces = build_grid(mode_to_draw, wall_w, wall_h, sheet_w, sheet_h, gap)

# chapas que cruzam a porta (para modo "cortar no local")
door_cross = [r for r in base_pieces if overlaps(r, door_rect)]

if cut_in_place:
    # mostra as chapas inteiras; lista retalho do vão como peça de descarte
    final_pieces = base_pieces[:]
    waste_from_door = [{"#": "corte_porta", "Largura (mm)": int(door_w), "Altura (mm)": int(door_h)}] if door_w and door_h else []
else:
    # subtrai o vão da porta das chapas
    cut_pieces = []
    for r in base_pieces:
        cut_pieces.extend(rect_subtract(r, door_rect))
    # filtra + grade
    filtered = []
    for (x,y,w,h) in cut_pieces:
        if w > 5 and h > 5:
            w2 = snap_to_grid(w, grid_step); h2 = snap_to_grid(h, grid_step)
            if w2 >= grid_step and h2 >= grid_step:
                filtered.append((x, y, w2, h2))
    # funde testas pequenas
    if merge_sill and door_w > 0 and door_h > 0:
        filtered = merge_small_headers(filtered, door_rect, threshold=grid_step)
    # >>> NOVO: adiciona FAIXAS LATERAIS da porta quando necessárias
    final_pieces = add_door_side_panels(filtered, door_rect, sheet_w, gap, grid_step, wall_w, wall_h)
    waste_from_door = []

# ========== DESENHO ==========
fig, ax = plt.subplots(figsize=(10, wall_h / wall_w * 10))
ax.set_xlim(0, wall_w); ax.set_ylim(0, wall_h); ax.set_aspect("equal"); ax.axis("off")
ax.add_patch(Rectangle((0, 0), wall_w, wall_h, fill=False, lw=2, edgecolor="black"))

# Fantasma das chapas que cruzam a porta (útil no modo cortar no local)
if cut_in_place:
    for (x,y,w,h) in door_cross:
        ax.add_patch(Rectangle((x, y), w, h, facecolor='none', edgecolor='black', linestyle='--', linewidth=1.1))
        if show_sizes: ax.text(x+w/2, y+h-14, f"{int(w)}×{int(h)}", ha="center", va="top", fontsize=8, alpha=0.85)

rows_out = []
for idx, (x,y,w,h) in enumerate(final_pieces, start=1):
    ax.add_patch(Rectangle((x, y), w, h, facecolor="#f3d8b6", edgecolor="black"))
    if show_numbers: ax.text(x+w/2, y+h/2, f"{idx}", ha="center", va="center", fontsize=10, weight="bold")
    if show_sizes:   ax.text(x+w/2, y+h-16, f"{format_mm(w)}×{format_mm(h)}", ha="center", va="top", fontsize=8)
    rows_out.append({"#": idx, "Largura (mm)": int(round(w)), "Altura (mm)": int(round(h))})

# Porta por cima
if door_w > 0 and door_h > 0:
    if cut_in_place:
        ax.add_patch(Rectangle((door_x, 0), door_w, door_h, fill=False, edgecolor="red", linewidth=1.8))
    else:
        ax.add_patch(Rectangle((door_x, 0), door_w, door_h, facecolor="white", edgecolor="black", lw=1.8))
    ax.text(door_x + door_w/2, door_h/2, f"Porta\n{int(door_w)}×{int(door_h)}", ha="center", va="center", fontsize=11, weight="bold")

st.pyplot(fig)

# ========== TABELAS / EXPORT ==========
st.markdown("---")
st.subheader("📋 Lista de peças (após recorte/preenchimento)")
df_pieces = pd.DataFrame(rows_out)
if df_pieces.empty:
    st.info("Nenhuma peça após o recorte — ajuste as dimensões ou a grade.")
else:
    st.dataframe(df_pieces)
    csv = df_pieces.to_csv(index=False).encode("utf-8")
    st.download_button("📥 Baixar lista de peças (CSV)", data=csv, file_name="atlas_wall_cortes.csv", mime="text/csv")

if cut_in_place and door_w and door_h:
    st.info("Corte de vão incluído (cortar no local).")
    df_waste = pd.DataFrame(waste_from_door)
    st.dataframe(df_waste)
    st.download_button("📥 Baixar retalho do vão (CSV)", data=df_waste.to_csv(index=False).encode("utf-8"),
                       file_name="retalho_porta.csv", mime="text/csv")

st.subheader("📊 Comparativo de Eficiência (pré-recorte)")
st.dataframe(df_eff.style.highlight_max(subset=["Aproveitamento (%)"], color="#c4f0c2"))

# Alerta de modularidade
mod_fit = (wall_w + gap) % (sheet_w + gap) if (sheet_w + gap) > 0 else 0
if mod_fit != 0:
    st.warning(
        f"⚠️ A largura da parede ({int(wall_w)} mm) não fecha com módulos de {int(sheet_w)}+{int(gap)} mm. "
        f"Considere ajustar para múltiplos de {int(sheet_w + gap)} mm."
    )

st.caption("© Atlas Frames — v1.2.2. Laterais da porta são geradas conforme a coluna de sheet; grade padrão 300 mm.")
