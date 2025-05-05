import streamlit as st
from supabase import create_client
import pandas as pd

# ------------------------------------------------------
# Modo wide y conexión explícita a Supabase
# ------------------------------------------------------
st.set_page_config(page_title="Registro de Gastos", layout="wide")
URL = "https://juezcuepljxpsiqgatyb.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp1ZXpjdWVwbGp4cHNpcWdhdHliIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY0MTcyNTIsImV4cCI6MjA2MTk5MzI1Mn0.N1uSwnN0DydpLtMVp_XSD3JHWjaJbEbUyUTrfTVmn54"
supabase = create_client(URL, KEY)

# ------------------------------------------------------
# 1. Cargo categorías y métodos de pago
# ------------------------------------------------------
cats_data = supabase.from_("categories").select("*").execute().data or []
pms_data  = supabase.from_("payment_methods").select("*").execute().data or []
df_cats = pd.DataFrame(cats_data)
df_pms  = pd.DataFrame(pms_data)

# ------------------------------------------------------
# Interfaz
# ------------------------------------------------------
st.title("Registro de Gastos")

# ------------------------------------------------------
# 2. Formulario para nuevo gasto
# ------------------------------------------------------
with st.form("gasto"):
    fecha = st.date_input("Fecha")
    cat   = st.selectbox("Categoría", df_cats["name"])
    pm    = st.selectbox("Método de pago", df_pms["name"])
    desc  = st.text_input("Descripción")
    monto = st.number_input("Monto (MXN)", min_value=0.0, format="%.2f")
    enviar = st.form_submit_button("Registrar gasto")

if enviar:
    cat_id = int(df_cats.loc[df_cats["name"] == cat, "id"].iloc[0])
    pm_id  = int(df_pms.loc[df_pms["name"] == pm, "id"].iloc[0])
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
# 3. Resumen mensual por categoría + tabla adaptativa + gráfica
# ------------------------------------------------------
if st.checkbox("Ver resumen mensual por categoría"):
    data = supabase.from_("expenses")\
                   .select("date,amount,category_id")\
                   .order("date", desc=True).execute().data or []
    df = pd.DataFrame(data)
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        resumen_cat = (
            df
            .assign(month=df["date"].dt.to_period("M"))
            .groupby(["month", "category_id"])["amount"]
            .sum()
            .reset_index()
            .assign(
                mes=lambda d: d["month"].dt.strftime("%B %Y"),
                categoria=lambda d: d["category_id"].map(
                    df_cats.set_index("id")["name"]
                )
            )
            .pivot(index="mes", columns="categoria", values="amount")
            .fillna(0)
        )
        st.table(resumen_cat)  # ajusta ancho según contenido
        st.bar_chart(resumen_cat, use_container_width=True)
    else:
        st.info("No hay datos de gastos para mostrar.")

# ------------------------------------------------------
# 4. Resumen mensual por método de pago + tabla + gráfica
# ------------------------------------------------------
if st.checkbox("Ver resumen mensual por método de pago"):
    data = supabase.from_("expenses")\
                   .select("date,amount,payment_method_id")\
                   .order("date", desc=True).execute().data or []
    df = pd.DataFrame(data)
    if not df.empty and "date" in df.columns:
        df["date"] = pd.to_datetime(df["date"])
        resumen_pm = (
            df
            .assign(month=df["date"].dt.to_period("M"))
            .groupby(["month", "payment_method_id"])["amount"]
            .sum()
            .reset_index()
            .assign(
                mes=lambda d: d["month"].dt.strftime("%B %Y"),
                metodo=lambda d: d["payment_method_id"].map(
                    df_pms.set_index("id")["name"]
                )
            )
            .pivot(index="mes", columns="metodo", values="amount")
            .fillna(0)
        )
        st.table(resumen_pm)
        st.bar_chart(resumen_pm, use_container_width=True)
    else:
        st.info("No hay datos de gastos para mostrar.")

# ------------------------------------------------------
# 5. Editar / Eliminar gastos (solo el seleccionado)
# ------------------------------------------------------
st.markdown("### Editar / Eliminar gastos")
all_exp = supabase.from_("expenses")\
                  .select("id,date,amount,category_id,payment_method_id,description")\
                  .order("date", desc=True).execute().data or []
exp_df = pd.DataFrame(all_exp)

if exp_df.empty:
    st.info("Aún no hay gastos registrados.")
elif "date" not in exp_df.columns:
    st.error(f"No encontré la columna 'date'. Columnas disponibles: {exp_df.columns.tolist()}")
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
            st.experimental_rerun()
