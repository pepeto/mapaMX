# app.py
# Streamlit app to load 'direcciones_X.csv', select a record by number,
# and show a Folium map with two points:
# (PP_latitud, PP_longitud) and (lat, lng),
# using custom markers with numbers and colors based on conditions.

import pandas as pd
import streamlit as st
from pathlib import Path
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Mapa de direcciones", layout="wide")

# ---------- Helpers ----------

def load_dataframe(csv_path: Path) -> pd.DataFrame:
    df = pd.read_csv(csv_path)
    df = df.copy().reset_index(drop=True)
    df["record_id"] = df.index + 1
    df = df.set_index("record_id")
    return df

def to_float_series(series: pd.Series) -> pd.Series:
    text = (
        series.astype(str)
        .str.strip()
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    return pd.to_numeric(text, errors="coerce")

def validate_required_columns(df: pd.DataFrame, required_cols: list[str]) -> list[str]:
    return [c for c in required_cols if c not in df.columns]

def make_numbered_icon(number: int, color: str) -> folium.DivIcon:
    """Create a circular marker with a number and background color."""
    html = f"""
    <div style="
        background-color:{color};
        border-radius:50%;
        width:28px;
        height:28px;
        display:flex;
        align-items:center;
        justify-content:center;
        color:white;
        font-weight:bold;
        border:2px solid black;">
        {number}
    </div>
    """
    return folium.DivIcon(html=html)

# ---------- UI: Sidebar ----------

st.sidebar.title("Configuración")

default_path = Path("direcciones_X.csv")
file_exists = default_path.exists()

uploaded_file = st.sidebar.file_uploader(
    "Opcional: subí un CSV (si no, se usará 'direcciones_X.csv' de la carpeta actual)",
    type=["csv"]
)

data_source_label = "Archivo subido" if uploaded_file is not None else "direcciones_X.csv local"
st.sidebar.markdown(f"**Fuente de datos:** {data_source_label}")

# ---------- Load data ----------

if uploaded_file is not None:
    df = pd.read_csv(uploaded_file)
    df = df.copy().reset_index(drop=True)
    df["record_id"] = df.index + 1
    df = df.set_index("record_id")
elif file_exists:
    df = load_dataframe(default_path)
else:
    st.error("No se encontró 'direcciones_X.csv' y no se subió ningún archivo.")
    st.stop()

required_columns = ["PP_latitud", "PP_longitud", "lat", "lng", "PP_method", "score", "PP_diferencia"]
missing_columns = validate_required_columns(df, required_columns)
if len(missing_columns) > 0:
    st.error(f"Faltan columnas requeridas en el CSV: {', '.join(missing_columns)}")
    st.stop()

df = df.copy()
df["PP_latitud"] = to_float_series(df["PP_latitud"])
df["PP_longitud"] = to_float_series(df["PP_longitud"])
df["lat"] = to_float_series(df["lat"])
df["lng"] = to_float_series(df["lng"])
df["PP_diferencia"] = to_float_series(df["PP_diferencia"])
df["score"] = to_float_series(df["score"])

# ---------- UI: Main ----------

st.title("Evaluación de Georeferenciación")

total_records = int(df.index.max())
st.caption(f"Registros disponibles: {total_records+1}")

selected_record_id = st.number_input(
    f"Seleccionar Número de Registro (1-{total_records+1}):",
    min_value=1,
    max_value=total_records,
    value=1,
    step=1,
)

row = df.loc[int(selected_record_id)]

pp_latitude = row["PP_latitud"]
pp_longitude = row["PP_longitud"]
geo_latitude = row["lat"]
geo_longitude = row["lng"]

# Only require geocoded coordinates; ignore PP if invalid/missing
if pd.isna(geo_latitude) or pd.isna(geo_longitude):
    st.warning("El registro seleccionado no tiene lat/lng válidos.")
    st.dataframe(row.to_frame().T, use_container_width=True)
    st.stop()

# ---------- Build Folium map ----------

# PP validity flag: both coords must be present and numeric
pp_valid = pd.notna(pp_latitude) and pd.notna(pp_longitude)

# Map center: if PP invalid, center on geocoded; else, midpoint
if pp_valid:
    center_latitude = (pp_latitude + geo_latitude) / 2.0
    center_longitude = (pp_longitude + geo_longitude) / 2.0
else:
    center_latitude = float(geo_latitude)
    center_longitude = float(geo_longitude)

folium_map = folium.Map(location=[center_latitude, center_longitude], zoom_start=15, control_scale=True)

# Decide colors / condition (as requested)
pp_condition = (str(row["PP_method"]).upper() == "EXACT") and (float(row["PP_diferencia"]) < 100)
geo_color = "green" if float(row["score"]) > 0.5 else "gray"

# Add PP marker (number 2) only if PP exists AND condition is true (green)
if pp_valid and pp_condition:
    folium.Marker(
        location=[pp_latitude, pp_longitude],
        tooltip="PP point",
        popup=f"PP: ({pp_latitude:.6f}, {pp_longitude:.6f}) | PP_method={row['PP_method']} | PP_diferencia={row['PP_diferencia']}",
        icon=make_numbered_icon(2, "green")
    ).add_to(folium_map)

# Add Geocoded marker (number 1)
folium.Marker(
    location=[geo_latitude, geo_longitude],
    tooltip="Geocoded point",
    popup=f"Geocoded: ({geo_latitude:.6f}, {geo_longitude:.6f}) | score={row['score']}",
    icon=make_numbered_icon(1, geo_color)
).add_to(folium_map)

# Draw line only if marker 2 is visible (and PP is valid)
if pp_valid and pp_condition:
    folium.PolyLine(
        locations=[[pp_latitude, pp_longitude], [geo_latitude, geo_longitude]],
        weight=3,
        opacity=0.8
    ).add_to(folium_map)

# Fit bounds only if both points are present; else remain centered on geocoded
if pp_valid and pp_condition:
    folium_map.fit_bounds([[pp_latitude, pp_longitude], [geo_latitude, geo_longitude]])

st_folium(folium_map, use_container_width=True, height=520)

st.subheader("Registro seleccionado")
st.dataframe(row.to_frame().T, use_container_width=True)
