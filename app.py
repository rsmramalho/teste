import io
import math
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle

# ========== CONFIG ==========
st.set_page_config(page_title="Atlas Wall Builder", page_icon="🧱", layout="wide")
st.title("🧱 Atlas Wall Builder v1.2.1")
st.caption("Recorte automático da porta, cortes em múltiplos, eliminação de retalhos e lista de peças.")

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
grid_step   = st.sidebar.number_input("Grade de múltiplos (mm)", 50, 600, 300, 50)  # ex.: 300
auto_mod    = st.sidebar.checkbox("Ajustar parede para fechar módulos", True)
merge_sill  = st.sidebar.checkbox("Fundir retalho acima da porta com a peça de cima (≤ grade)", True)
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
    # sem sobreposição
    if ix >= ax or iy >= ay:
        return [rect]

    out = []
    # esquerda
    if ix > rx: out.append((rx, ry, ix - rx, rh))
    # direita
    if ax < rx+rw: out.append((ax, ry, (rx + rw) - ax, rh))
    # baixo
    if iy > ry: out.append((ix, ry, ax - ix, iy - ry))
    # topo
    if ay < ry+rh: out.append((ix, ay, ax - ix, (ry + rh) - ay))
    return out

def build_grid(mode, W, H, sw, sh, g):
    """
    Cria peças-base (sem recorte da porta).
    Vertical: colunas sw; linhas sh; topo = resto
    Horizontal: linhas sh; colunas sw; topo = resto
    Híbrido: 1 faixa base sh + topo resto
    """
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

    else:  # Híbrido
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
    """
    Se existir uma peça "testa" colada ao topo da porta com altura <= threshold,
    funde-a com a peça imediatamente acima (se alinhadas em X e contíguas em Y).
    """
    dx, dy, dw, dh = door
    top_edge = dy + dh  # y do topo da porta

    # separa peças acima da porta que cobrem totalmente o vão em X
    headers = []
    uppers  = []
    for (x, y, w, h) in pieces:
        # header := faixa cujo pé está exatamente no topo da porta (ou muito perto)
        if abs(y - top_edge) <=_
