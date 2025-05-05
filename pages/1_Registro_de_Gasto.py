# pages/1_Registro_de_Gasto.py

import streamlit as st
from supabase import create_client
import pandas as pd

# ------------------------------------------------------
# Configuración de página y conexión a Supabase
# ------------------------------------------------------
st.set_page_config(page_title="Registro de Gastos", layout="wide")
URL = "https://juezcuepljxpsiqgatyb.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp1ZXpjdWVwbGp4cHNpcWdhdHliIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY0MTcyNTIsImV4cCI6MjA2MTk5MzI1Mn0.N1uSwnN0DydpLtMVp_XSD3JHWjaJbEbUyUTrfTVmn54"
supabase = create_client(URL, KEY)

# ------------------------------------------------------
# Cargo categorías y métodos
# ------------------------------------------------------
cats_data = supabase.from_("categories").select("*").execute().data or []
pms_data  = supabase.from_("payment_methods").select("*").execute().data or []
df_cats = pd.DataFrame(cats_data)
df_pms  = pd.DataFrame(pms_data)

st.title("Registro de Gastos")

# ------------------------------------------------------
# Formulario para nuevo gasto
# ------------------------------------------------------
with st.form("gasto"):
    col1, col2, col3, col4, col5 = st.columns([2,2,3,2,1])
    with col1:
        fecha = st.date_input("Fecha")
    with col2:
        cat = st.selectbox("Categoría", df_cats["name"])
    with col3:
        pm = st.selectbox("Método de pago", df_pms["name"])
    with col4:
        desc = st.text_input("Descripción")
    with col5:
        monto = st.number_input("Monto (MXN)", min_value=0.0, format="%.2f")
    enviar = st.form_submit_button("Registrar gasto")

if enviar:
    cat_id = int(df_cats.loc[df_cats["name"] == cat, "id"].iloc[0])
    pm_id  = int(df_pms.loc[df_pms["name"] == pm,   "id"].iloc[0])
    nuevo = {
        "date": fecha.isoformat(),
        "amount": monto,
        "category_id": cat_id,
        "payment_method_id": pm_id,
        "description": desc
    }
    res = supabase.from_("expenses").insert(nuevo).execute()
    status = getattr(res, "status_code", None)
    if status and status >= 400:
        st.error(f"Error {status}: {res.data}")
    else:
        st.success("Gasto registrado ✔️")

# ------------------------------------------------------
# Listado de gastos y botón de eliminar
# ------------------------------------------------------
st.markdown("### Editar / Eliminar gastos")
all_exp = supabase.from_("expenses")\
                  .select("id,date,amount,category_id,payment_method_id,description")\
                  .order("date", desc=False).execute().data or []
exp_df = pd.DataFrame(all_exp)

if exp_df.empty:
    st.info("Aún no hay gastos registrados.")
else:
    exp_df["date"] = pd.to_datetime(exp_df["date"]).dt.date
    exp_df["category"] = exp_df["category_id"].map(df_cats.set_index("id")["name"])
    exp_df["payment_method"] = exp_df["payment_method_id"].map(df_pms.set_index("id")["name"])
    exp_show = exp_df[["id","date","amount","category","payment_method","description"]]

    for _, row in exp_show.iterrows():
        cols = st.columns([1,1,1,1,1,2,1], gap="small")
        cols[0].write(row["id"])
        cols[1].write(row["date"])
        cols[2].write(f"${row['amount']:.2f}")
        cols[3].write(row["category"])
        cols[4].write(row["payment_method"])
        cols[5].write(row["description"])
        if cols[6].button("Eliminar", key=f"del_{row['id']}"):
            supabase.from_("expenses").delete().eq("id", row["id"]).execute()
            st.success("Gasto eliminado ✔️")
            # Para ver el cambio, recarga la página manualmente
