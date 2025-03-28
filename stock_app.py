# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import smtplib
from email.message import EmailMessage
import os

# CONFIGURATION GÉNÉRALE
st.set_page_config(page_title="📦 Suivi de Stock", layout="centered")
EMAIL = "moulaihcenewalidro@gmail.com"
APP_PASSWORD = "osva szaz sngc ljxa"

stock_file = "stock_initial_complet_avec_categorie.xlsx"
historique_file = "historique_journalier.xlsx"

# CHARGEMENT DES FICHIERS
if os.path.exists(stock_file):
    df_stock = pd.read_excel(stock_file)
else:
    df_stock = pd.DataFrame(columns=["Produit", "Code de Produit", "Lot", "Stock Initial (Kilos)",
                                     "Stock Initial Référence (Kilos)", "Densité", "Catégorie"])

if os.path.exists(historique_file):
    df_historique = pd.read_excel(historique_file)
else:
    df_historique = pd.DataFrame(columns=["Date", "Employé", "Client", "Fournisseur", "BL", "Produit", "Code de Produit",
                                          "Lot", "Unité", "Quantité Saisie", "Densité", "Quantité (Kilos)"])

# TRAITEMENTS PRÉLIMINAIRES
df_stock["Densité"] = pd.to_numeric(df_stock["Densité"], errors="coerce").fillna(1)
df_stock["Stock Initial (Kilos)"] = pd.to_numeric(df_stock["Stock Initial (Kilos)"], errors="coerce").fillna(0)
df_stock["Stock Initial Référence (Kilos)"] = pd.to_numeric(df_stock["Stock Initial Référence (Kilos)"], errors="coerce").fillna(0)
df_stock["Catégorie"] = df_stock["Catégorie"].astype(str)

# LISTES DYNAMIQUES
categories = sorted(df_stock["Catégorie"].dropna().unique())
clients_default = [
    "Zentral", "Répértoir culinaire UK", "FN", "Feuillette", "food choice", "TGT", "Kylian Blot", "RCL DUBAI",
    "Maison Landemaine", "OBERWEIS", "Maison Bécam", "Back Europ", "Chef Robuchon", "EPGB", "Les secrets d'Honoré",
    "Réserve", "Landemaine", "Joel Robuchon", "mon pari gourmand", "Mazet", "Chocolaterie Pecq", "Farinier",
    "Dasita", "Becam", "Pole sud"
]
employes = ["Alexendre", "Asmaa", "Zahir", "Massinissa"]
fournisseurs = sorted(set(df_historique.get("Fournisseur", pd.Series()).dropna().tolist()) + ["Premium Good", "Ilanga"])

# INTERFACE
st.title("📦 Suivi de Stock – Application Complète")

cat = st.selectbox("📂 Catégorie", categories)
df_filtered = df_stock[df_stock["Catégorie"] == cat]
produits = sorted(df_filtered["Produit"].unique())
produit = st.selectbox("Produit *", produits)

lot = st.text_input("Numéro de Lot *")
unite = st.selectbox("Unité *", ["Kilo", "Litre"])
quantite = st.number_input("Quantité *", min_value=0.0, step=0.1)
bl = st.text_input("Code BL *")
expediteur = st.text_input("Nom de l'expéditeur", "Système de Stock")

employe = st.selectbox("Employé", employes + ["🔹 Nouveau..."])
if employe == "🔹 Nouveau...":
    employe = st.text_input("➡️ Saisir nouveau employé")

client = st.selectbox("Client", clients_default + ["🔹 Nouveau..."])
if client == "🔹 Nouveau...":
    client = st.text_input("➡️ Saisir nouveau client")

fournisseur = st.selectbox("Fournisseur", fournisseurs + ["🔹 Nouveau..."])
if fournisseur == "🔹 Nouveau...":
    fournisseur = st.text_input("➡️ Saisir nouveau fournisseur")

# Auto-remplissage code/densité
row_info = df_stock[df_stock["Produit"] == produit]
code = row_info["Code de Produit"].values[0] if not row_info.empty else ""
densite = row_info["Densité"].values[0] if not row_info.empty else 1
quantite_kilo = quantite * densite if unite == "Litre" else quantite

st.markdown(f"🔖 Code Produit : `{code}`")
st.markdown(f"💧 Densité : `{densite}`")

# EMAIL
def envoyer_email(sujet, contenu):
    msg = EmailMessage()
    msg["Subject"] = sujet
    msg["From"] = EMAIL
    msg["To"] = EMAIL
    msg.set_content(contenu)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL, APP_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        st.error(f"Erreur email : {e}")

# ENREGISTREMENT
def enregistrer_mouvement(type_mvt):
    global df_stock, df_historique

    if not all([produit, lot, bl, quantite > 0]):
        st.warning("⚠️ Remplir tous les champs obligatoires (*)")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    idx = df_stock[(df_stock["Produit"] == produit) & (df_stock["Lot"] == lot)].index

    if type_mvt == "Entrée":
        if not idx.empty:
            df_stock.at[idx[0], "Stock Initial (Kilos)"] += quantite_kilo
        else:
            ref = quantite_kilo
            cat_value = cat
            df_stock.loc[len(df_stock)] = [produit, code, lot, quantite_kilo, ref, densite, cat_value]
    else:
        if not idx.empty:
            stock = df_stock.at[idx[0], "Stock Initial (Kilos)"]
            if quantite_kilo > stock:
                st.error(f"❌ Stock insuffisant : {stock:.2f} kg disponible")
                return
            df_stock.at[idx[0], "Stock Initial (Kilos)"] -= quantite_kilo
            ref = df_stock.at[idx[0], "Stock Initial Référence (Kilos)"]
            reste = stock - quantite_kilo
            pourcent = max(0, min((reste / ref) * 100, 100)) if ref > 0 else 0
            if pourcent <= 25:
                envoyer_email(f"⚠️ Stock bas - {produit} - Lot {lot}", f"Reste : {reste:.2f} kg ({pourcent:.1f}%)")
            if reste <= 0:
                envoyer_email(f"❌ Stock épuisé - {produit} - Lot {lot}", "Le stock est à 0 kg.")
        else:
            st.error("❌ Produit ou lot introuvable.")
            return

    row = {
        "Date": now, "Employé": employe, "Client": client, "Fournisseur": fournisseur, "BL": bl,
        "Produit": produit, "Code de Produit": code, "Lot": lot,
        "Unité": unite, "Quantité Saisie": quantite, "Densité": densite, "Quantité (Kilos)": quantite_kilo
    }
    df_historique = pd.concat([df_historique, pd.DataFrame([row])], ignore_index=True)
    df_stock.to_excel(stock_file, index=False)
    df_historique.to_excel(historique_file, index=False)
    st.success(f"{type_mvt} enregistrée ✅")

# RAPPORT
def envoyer_rapport_journalier_excel():
    date_now = datetime.now().strftime("%Y-%m-%d")
    df_jour = df_historique[df_historique["Date"].astype(str).str.startswith(date_now)]
    if df_jour.empty:
        st.warning("Aucune donnée aujourd’hui.")
        return
    file_name = f"rapport_{date_now}.xlsx"
    df_jour.to_excel(file_name, index=False)
    msg = EmailMessage()
    msg["Subject"] = f"📊 Rapport du {date_now}"
    msg["From"] = EMAIL
    msg["To"] = EMAIL
    msg.set_content(f"Rapport du jour en pièce jointe – {expediteur}")
    with open(file_name, "rb") as f:
        msg.add_attachment(f.read(), maintype="application", subtype="octet-stream", filename=file_name)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL, APP_PASSWORD)
            smtp.send_message(msg)
        st.success("📩 Rapport Excel envoyé")
    except Exception as e:
        st.error(f"Erreur email : {e}")

# BOUTONS PRINCIPAUX
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("✅ Approvisionnement"):
        enregistrer_mouvement("Entrée")
with col2:
    if st.button("📦 Sortie"):
        enregistrer_mouvement("Sortie")
with col3:
    if st.button("📤 Envoyer Rapport Excel"):
        envoyer_rapport_journalier_excel()

# GRAPHIQUE PAR LOT
st.markdown("---")
st.subheader("📉 Suivi par Lot")
cat2 = st.selectbox("🔎 Catégorie", categories, key="lot_cat")
produits2 = df_stock[df_stock["Catégorie"] == cat2]["Produit"].unique()
produit_sel = st.selectbox("Produit 🎯", produits2, key="lot_prod")
lots = df_stock[df_stock["Produit"] == produit_sel]["Lot"].unique()
lot_sel = st.selectbox("Lot 🎯", lots, key="lot_lot")

row = df_stock[(df_stock["Produit"] == produit_sel) & (df_stock["Lot"] == lot_sel)]
if not row.empty:
    stock = float(row["Stock Initial (Kilos)"].values[0])
    ref = float(row["Stock Initial Référence (Kilos)"].values[0])
    pourcent = max(0, min((stock / ref) * 100, 100)) if ref > 0 else 0
    couleur = "green" if pourcent > 60 else "orange" if pourcent > 25 else "red"
    fig, ax = plt.subplots(figsize=(6, 2.5))
    bar = ax.barh([f"{produit_sel} - Lot {lot_sel}"], [pourcent], color=couleur)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Stock (%)")
    ax.bar_label(bar, labels=[f"{pourcent:.1f}%\n{stock:.1f} kg / {ref:.1f} kg"], fontsize=10)
    st.pyplot(fig)

    if st.button("🗑️ Supprimer ce lot"):
        df_stock = df_stock[~((df_stock["Produit"] == produit_sel) & (df_stock["Lot"] == lot_sel))]
        df_stock.to_excel(stock_file, index=False)
        st.success("✅ Lot supprimé – actualisez la page pour voir les changements.")

# RÉSUMÉ FINAL
st.markdown("---")
st.subheader("📋 Résumé Global des Stocks")
df_resume = df_stock.copy()
df_resume["% Stock"] = (df_resume["Stock Initial (Kilos)"] / df_resume["Stock Initial Référence (Kilos)"]).replace([float("inf"), -float("inf")], 0) * 100
df_resume["% Stock"] = df_resume["% Stock"].fillna(0).round(1).clip(lower=0, upper=100)
df_resume["Stock Initial (Kilos)"] = df_resume["Stock Initial (Kilos)"].apply(lambda x: max(0, x))
st.dataframe(df_resume[["Produit", "Lot", "Stock Initial (Kilos)", "Stock Initial Référence (Kilos)", "% Stock"]])
