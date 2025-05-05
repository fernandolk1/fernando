# pages/03_ingresos.py

import streamlit as st
from supabase import create_client
import pandas as pd
import altair as alt

# ------------------------------------------------------
# Configuración y conexión (modo wide)
# ------------------------------------------------------
st.set_page_config(page_title="Registro de Ingresos", layout="wide")
URL = "https://juezcuepljxpsiqgatyb.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp1ZXpjdWVwbGp4cHNpcWdhdHliIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY0MTcyNTIsImV4cCI6MjA2MTk5MzI1Mn0.N1uSwnN0DydpLtMVp_XSD3JHWjaJbEbUyUTrfTVmn54"
supabase = create_client(URL, KEY)

# ------------------------------------------------------
# Cargo fuentes y datos de ingresos
# ------------------------------------------------------
src_data = supabase.from_("income_sources").select("*").execute().data or []
df_src = pd.DataFrame(src_data).set_index("id")

inc_data = supabase.from_("incomes")\
    .select("id,date,amount,source_id,description")\
    .order("date", desc=False).execute().data or []
df_inc = pd.DataFrame(inc_data)

st.title("Registro de Ingresos")

# ------------------------------------------------------
# Formulario para nuevo ingreso
# ------------------------------------------------------
with st.form("ingreso"):
    c1, c2, c3, c4 = st.columns([2,2,2,3])
    with c1:
        fecha = st.date_input("Fecha")
    with c2:
        fuente = st.selectbox("Fuente", df_src["name"])
    with c3:
        monto  = st.number_input("Monto (MXN)", min_value=0.0, format="%.2f")
    with c4:
        desc   = st.text_input("Descripción")
    enviar = st.form_submit_button("Registrar ingreso")

if enviar:
    nuevo = {
        "date": fecha.isoformat(),
        "amount": monto,
        "source_id": int(df_src[df_src["name"] == fuente].index[0]),
        "description": desc
    }
    res = supabase.from_("incomes").insert(nuevo).execute()
    if getattr(res, "status_code", 0) >= 400:
        st.error("Error al registrar ingreso")
    else:
        st.success("Ingreso registrado ✔️")

# ------------------------------------------------------
# Si no hay datos, detenemos
# ------------------------------------------------------
if df_inc.empty:
    st.info("Aún no hay ingresos registrados.")
    st.stop()

# ------------------------------------------------------
# Formateo de DataFrame
# ------------------------------------------------------
df_inc["date"]   = pd.to_datetime(df_inc["date"]).dt.date
df_inc["fuente"] = df_inc["source_id"].map(df_src["name"])

# ------------------------------------------------------
# Métricas generales + por fuente
# ------------------------------------------------------
total_ingresos = df_inc["amount"].sum()
by_fuente      = df_inc.groupby("fuente")["amount"].sum()

cols = st.columns(1 + len(by_fuente))
cols[0].metric("Total ingresos", f"${total_ingresos:,.2f}")
for i, (f, val) in enumerate(by_fuente.items(), start=1):
    cols[i].metric(f, f"${val:,.2f}")

st.markdown("---")

# ------------------------------------------------------
# Barras horizontales: ingreso por fuente x mes
# ------------------------------------------------------
df_inc["mes"] = pd.to_datetime(df_inc["date"]).dt.to_period("M").dt.strftime("%B %Y")
src_month = df_inc.groupby(["mes","fuente"])["amount"].sum().reset_index()

bar = (
    alt.Chart(src_month)
       .mark_bar()
       .encode(
           y=alt.Y("fuente:N", sort='-x', title="Fuente"),
           x=alt.X("amount:Q", title="Total por fuente (MXN)"),
           color="fuente:N"
       )
       .properties(width=500, height=300)
)
st.altair_chart(bar, use_container_width=False)

st.markdown("---")

# ------------------------------------------------------
# Editar / Eliminar ingresos
# ------------------------------------------------------
st.markdown("### Editar / Eliminar registros de Ingresos")
for _, row in df_inc.iterrows():
    cols = st.columns([1,1,1,2,1], gap="small")
    cols[0].write(row["id"])
    cols[1].write(row["date"])
    cols[2].write(f"${row['amount']:.2f}")
    cols[3].write(row["fuente"])
    cols[4].write(row["description"])
    if cols[4].button("Eliminar", key=f"del_inc_{row['id']}"):
        supabase.from_("incomes").delete().eq("id", row["id"]).execute()
        st.success("Ingreso eliminado ✔️")
