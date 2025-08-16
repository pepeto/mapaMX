# app.py
# Streamlit app to load 'direcciones_X.csv', select a record by number,
# and show a Folium map with two points: (PP_latitud, PP_longitud) and (lat, lng).
# Code in English, with explicit variable names and detailed comments.

import pandas as pd
import streamlit as st
from pathlib import Path
import folium
from streamlit_folium import st_folium

st.set_page_config(page_title="Mapa de direcciones", layout="wide")

# ---------- Helpers ----------

def load_dataframe(csv_path: Path) -> pd.DataFrame:
    """
    Load the CSV into a DataFrame and prepare an integer 1-based index called 'record_id'
    so we can select rows using .loc (user preference).
    """
    df = pd.read_csv(csv_path)
    df = df.copy().reset_index(drop=True)
    df["record_id"] = df.index + 1
    df = df.set_index("record_id")
    return df


def to_float_series(series: pd.Series) -> pd.Series:
    """
    Convert a pandas Series to float, handling commas as decimal separators and trimming spaces.
    Any non-convertible value becomes NaN (will be validated later).
    """
    text = series.astype(str).str.strip().str.replace(" ", "", regex=False).str.replace(",", ".", regex=False)
    return pd.to_numeric(text, errors="coerce")


def validate_required_columns(df: pd.DataFrame, required_cols: list[str]) -> list[str]:
    """
    Return the list of missing columns.
    """
    return [c for c in required_cols if c not in df.columns]


# ---------- UI: Sidebar ----------

st.sidebar.title("Configuración")

default_path = Path("direcciones_X.csv")
file_exists = default_path.exists()

uploaded_file = st.sidebar.file_uploader(
    "Opcional: subí un CSV (si no, se usará 'direcciones_X.csv' de la carpeta actual)",
    type=["csv"]
)

# Decide which source to load: uploaded file (if provided) or default local file.
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

# Validate that required columns exist
required_columns = ["PP_latitud", "PP_longitud", "lat", "lng"]
missing_columns = validate_required_columns(df, required_columns)
if len(missing_columns) > 0:
    st.error(f"Faltan columnas requeridas en el CSV: {', '.join(missing_columns)}")
    st.stop()

# Cast coordinate columns to numeric (robust to commas)
df = df.copy()
df["PP_latitud"] = to_float_series(df["PP_latitud"])
df["PP_longitud"] = to_float_series(df["PP_longitud"])
df["lat"] = to_float_series(df["lat"])
df["lng"] = to_float_series(df["lng"])

# ---------- UI: Main ----------

st.title("Mapa Folium de dos puntos por registro")

total_records = int(df.index.max())
st.caption(f"Registros disponibles: {total_records}")

selected_record_id = st.number_input(
    "Elegí el número de registro (1-based):",
    min_value=1,
    max_value=total_records,
    value=1,
    step=1,
    help="Usa el índice 1..N (no es 0-based)."
)

# Retrieve the selected row with .loc to respect user preference
row = df.loc[int(selected_record_id)]

pp_latitude = row["PP_latitud"]
pp_longitude = row["PP_longitud"]
geo_latitude = row["lat"]
geo_longitude = row["lng"]

# Validate presence of coordinates for the selected record
if pd.isna(pp_latitude) or pd.isna(pp_longitude) or pd.isna(geo_latitude) or pd.isna(geo_longitude):
    st.warning("El registro seleccionado tiene coordenadas faltantes o no numéricas. Elegí otro registro.")
    st.dataframe(row.to_frame().T, use_container_width=True)
    st.stop()

# ---------- Build Folium map ----------

# Compute a neutral center between both points
center_latitude = (pp_latitude + geo_latitude) / 2.0
center_longitude = (pp_longitude + geo_longitude) / 2.0

folium_map = folium.Map(location=[center_latitude, center_longitude], zoom_start=15, control_scale=True)

# Add both markers
folium.Marker(
    location=[pp_latitude, pp_longitude],
    tooltip="PP point (PP_latitud, PP_longitud)",
    popup=f"PP: ({pp_latitude:.6f}, {pp_longitude:.6f})",
    icon=folium.Icon(color="blue", icon="flag")
).add_to(folium_map)

folium.Marker(
    location=[geo_latitude, geo_longitude],
    tooltip="Geocoded point (lat, lng)",
    popup=f"Geocoded: ({geo_latitude:.6f}, {geo_longitude:.6f})",
    icon=folium.Icon(color="red", icon="map-marker")
).add_to(folium_map)

# Optional: draw a line between both points for visual clarity
folium.PolyLine(
    locations=[[pp_latitude, pp_longitude], [geo_latitude, geo_longitude]],
    weight=3,
    opacity=0.8
).add_to(folium_map)

# Fit the map to show both points nicely
folium_map.fit_bounds([[pp_latitude, pp_longitude], [geo_latitude, geo_longitude]])

# Render Folium map inside Streamlit
st_folium(folium_map, use_container_width=True, height=520)

# Show the full row for reference
st.subheader("Registro seleccionado")
st.dataframe(row.to_frame().T, use_container_width=True)
