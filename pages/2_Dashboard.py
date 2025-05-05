# pages/02_dashboard.py

import streamlit as st
from supabase import create_client
import pandas as pd
import altair as alt
from datetime import date

# ------------------------------------------------------
# Configuración de página y conexión a Supabase
# ------------------------------------------------------
st.set_page_config(page_title="Dashboard de Gastos", layout="wide")
URL = "https://juezcuepljxpsiqgatyb.supabase.co"
KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6Imp1ZXpjdWVwbGp4cHNpcWdhdHliIiwicm9sZSI6ImFub24iLCJpYXQiOjE3NDY0MTcyNTIsImV4cCI6MjA2MTk5MzI1Mn0.N1uSwnN0DydpLtMVp_XSD3JHWjaJbEbUyUTrfTVmn54"
supabase = create_client(URL, KEY)

# ------------------------------------------------------
# Cargo y preparo datos de gastos
# ------------------------------------------------------
exp = (
    supabase.from_("expenses")
    .select("date,amount,category_id,payment_method_id")
    .order("date", desc=False)
    .execute()
    .data
) or []
df_master = pd.DataFrame(exp)
if df_master.empty:
    st.info("No hay datos para mostrar en el dashboard.")
    st.stop()

df_master["date"] = pd.to_datetime(df_master["date"])
cats = (
    pd.DataFrame(supabase.from_("categories").select("*").execute().data or [])
    .set_index("id")
)
pms = (
    pd.DataFrame(supabase.from_("payment_methods").select("*").execute().data or [])
    .set_index("id")
)
df_master["payment_method"] = df_master["payment_method_id"].map(pms["name"])
df_master["category"] = df_master["category_id"].map(cats["name"])
df_master["period"] = df_master["date"].dt.to_period("M")

# ------------------------------------------------------
# Cargo datos de ingresos
# ------------------------------------------------------
inc = supabase.from_("incomes").select("amount").execute().data or []
df_inc = pd.DataFrame(inc)
total_ingresos = df_inc["amount"].sum() if not df_inc.empty else 0.0

# ------------------------------------------------------
# Filtro por mes en la barra lateral
# ------------------------------------------------------
periods = sorted(df_master["period"].unique())
labels = [p.strftime("%B %Y") for p in periods]
period_map = dict(zip(labels, periods))
sel = st.sidebar.selectbox("Filtrar mes", ["Todos"] + labels)
if sel != "Todos":
    per = period_map[sel]
    df = df_master[df_master["period"] == per]
else:
    df = df_master.copy()

# ------------------------------------------------------
# Cálculo de pago BBVA TC (corte día 9)
# ------------------------------------------------------
cut_day = 9
if sel != "Todos":
    year, month = per.year, per.month
else:
    today = date.today()
    year, month = today.year, today.month

# rango facturación: del 10 del mes anterior al 9 del mes actual
if month == 1:
    start = date(year - 1, 12, cut_day + 1)
else:
    start = date(year, month - 1, cut_day + 1)
end = date(year, month, cut_day)

mask_bbva = (
    (df_master["payment_method"] == "BBVA TC")
    & (df_master["date"].dt.date >= start)
    & (df_master["date"].dt.date <= end)
)
pago_bbva = df_master.loc[mask_bbva, "amount"].sum()

# ------------------------------------------------------
# 1. Métricas generales: ingresos, gasto, neto, pago BBVA, por método
# ------------------------------------------------------
st.header("📊 Dashboard de Gastos")

total_gastado = df["amount"].sum()
ingresos_neto = total_ingresos - total_gastado
by_pm = df.groupby("payment_method")["amount"].sum()

cols = st.columns(4 + len(by_pm))
cols[0].metric("Total ingresos", f"${total_ingresos:,.2f}")
cols[1].metric("Total gastado", f"${total_gastado:,.2f}")
cols[2].metric("Ingresos netos", f"${ingresos_neto:,.2f}")
cols[3].metric(
    f"Pago BBVA TC ({start.day}/{start.month} – {end.day}/{end.month})",
    f"${pago_bbva:,.2f}"
)
for i, (m, val) in enumerate(by_pm.items(), start=4):
    cols[i].metric(f"Total {m}", f"${val:,.2f}")

st.markdown("---")

# ------------------------------------------------------
# Helper: nombres en español
# ------------------------------------------------------
weekday_map = {
    0: "Lunes", 1: "Martes", 2: "Miércoles", 3: "Jueves",
    4: "Viernes", 5: "Sábado", 6: "Domingo"
}
month_map = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril",
    5: "Mayo", 6: "Junio", 7: "Julio", 8: "Agosto",
    9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"
}

# ------------------------------------------------------
# 2. Gasto diario (línea con etiquetas "Lunes - 5 de Mayo")
# ------------------------------------------------------
daily = (
    df.groupby(df["date"].dt.date)["amount"]
    .sum()
    .reset_index()
    .rename(columns={"date": "fecha"})
)
daily["fecha"] = pd.to_datetime(daily["fecha"])
daily["label"] = daily["fecha"].apply(
    lambda d: f"{weekday_map[d.weekday()]} - {d.day} de {month_map[d.month]}"
)
line = (
    alt.Chart(daily)
    .mark_line(point=True)
    .encode(
        x=alt.X("label:N", title="Día"),
        y=alt.Y("amount:Q", title="Gasto diario (MXN)")
    )
    .properties(width=600, height=300)
)
st.altair_chart(line, use_container_width=False)

st.markdown("---")

# ------------------------------------------------------
# 3. Gasto por categoría x mes (barras horizontales)
# ------------------------------------------------------
catm = (
    df.assign(mes=df["period"].dt.strftime("%B %Y"))
    .groupby(["mes", "category"])["amount"]
    .sum()
    .reset_index()
)
bar_cat = (
    alt.Chart(catm)
    .mark_bar()
    .encode(
        y=alt.Y("category:N", sort="-x"),
        x=alt.X("amount:Q", title="Total gastado (MXN)"),
        color="category:N"
    )
    .properties(width=500, height=250)
)
st.altair_chart(bar_cat, use_container_width=False)

st.markdown("---")

# ------------------------------------------------------
# 4. Gasto por método de pago x mes (barras horizontales)
# ------------------------------------------------------
pmm = (
    df.assign(mes=df["period"].dt.strftime("%B %Y"))
    .groupby(["mes", "payment_method"])["amount"]
    .sum()
    .reset_index()
)
bar_pm = (
    alt.Chart(pmm)
    .mark_bar()
    .encode(
        y=alt.Y("payment_method:N", sort="-x"),
        x=alt.X("amount:Q", title="Total gastado (MXN)"),
        color="payment_method:N"
    )
    .properties(width=500, height=250)
)
st.altair_chart(bar_pm, use_container_width=False)
