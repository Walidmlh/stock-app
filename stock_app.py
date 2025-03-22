# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import smtplib
from email.message import EmailMessage
import os

EMAIL = "moulaihcenewalidro@gmail.com"
APP_PASSWORD = "osva szaz sngc ljxa"

stock_file = "stock_initial_test.xlsx"
historique_file = "historique_journalier.xlsx"

# === CHARGEMENT DES DONNÉES ===
if os.path.exists(stock_file):
    df_stock = pd.read_excel(stock_file)
else:
    df_stock = pd.DataFrame(columns=["Produit", "Code de Produit", "Lot", "Stock Initial (Kilos)", "Stock Initial Référence (Kilos)", "Densité"])

if os.path.exists(historique_file):
    df_historique = pd.read_excel(historique_file)
else:
    df_historique = pd.DataFrame(columns=["Date", "Employé", "Client", "Fournisseur", "BL", "Produit", "Code de Produit", "Lot", "Unité", "Quantité Saisie", "Densité", "Quantité (Kilos)"])

if "Fournisseur" not in df_historique.columns:
    df_historique["Fournisseur"] = ""

# === LISTES DYNAMIQUES ===
produits = sorted(df_stock["Produit"].dropna().unique())
clients = sorted([c for c in df_historique["Client"].dropna().unique() if c != "HHHHH"])
employes = sorted(df_historique["Employé"].dropna().unique())
fournisseurs = sorted(set(df_historique["Fournisseur"].dropna().unique().tolist() + ["Premium Good", "Ilanga"]))

# === INTERFACE ===
st.set_page_config(page_title="📦 Suivi de Stock", layout="centered")
st.title("📦 Suivi de Stock – Application Complète")

col1, col2 = st.columns(2)
with col1:
    produit = st.selectbox("Produit *", produits)
    lot = st.text_input("Numéro de Lot *")
    unite = st.selectbox("Unité *", ["Kilo", "Litre"])
    quantite = st.number_input("Quantité *", min_value=0.0, step=0.1)
    bl = st.text_input("Code BL *")
    expediteur = st.text_input("Nom de l'expéditeur des emails", "Système de Stock")

with col2:
    employe = st.selectbox("Employé", employes + ["🔹 Nouveau..."])
    if employe == "🔹 Nouveau...":
        employe = st.text_input("➡️ Saisir nouveau employé")

    client = st.selectbox("Client *", clients + ["🔹 Nouveau..."])
    if client == "🔹 Nouveau...":
        client = st.text_input("➡️ Saisir nouveau client")

    fournisseur = st.selectbox("Fournisseur *", fournisseurs + ["🔹 Nouveau..."])
    if fournisseur == "🔹 Nouveau...":
        fournisseur = st.text_input("➡️ Saisir nouveau fournisseur")

# === DÉTERMINATION CODE & DENSITÉ ===
code = df_stock[df_stock["Produit"] == produit]["Code de Produit"].values[0] if produit in df_stock["Produit"].values else ""
densite = df_stock[df_stock["Produit"] == produit]["Densité"].values[0] if produit in df_stock["Produit"].values else 1
quantite_kilo = quantite * densite if unite == "Litre" else quantite

st.markdown(f"🔖 Code Produit : `{code}`")
st.markdown(f"💧 Densité : `{densite}`")

# === EMAIL ===
def envoyer_email(subject, contenu):
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = EMAIL
    msg["To"] = EMAIL
    msg.set_content(contenu)
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL, APP_PASSWORD)
            smtp.send_message(msg)
    except Exception as e:
        st.error(f"Erreur envoi email : {e}")

# === ENREGISTREMENT ===
def enregistrer_mouvement(type_mouvement):
    global df_stock, df_historique
    if not all([produit, lot, client, bl, quantite > 0]):
        st.warning("⚠️ Veuillez remplir tous les champs obligatoires (*)")
        return

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    idx = df_stock[(df_stock["Produit"] == produit) & (df_stock["Lot"] == lot)].index

    if type_mouvement == "Entrée":
        if not idx.empty:
            df_stock.at[idx[0], "Stock Initial (Kilos)"] += quantite_kilo
        else:
            df_stock.loc[len(df_stock)] = [produit, code, lot, quantite_kilo, quantite_kilo, densite]
    else:
        if not idx.empty:
            stock_actuel = df_stock.at[idx[0], "Stock Initial (Kilos)"]
            if quantite_kilo > stock_actuel:
                st.error("❌ Le stock ne permet pas de conditionner cette quantité.")
                return
            df_stock.at[idx[0], "Stock Initial (Kilos)"] -= quantite_kilo
            stock_ref = df_stock.at[idx[0], "Stock Initial Référence (Kilos)"]
            pourcentage = max(0, (stock_actuel - quantite_kilo) / stock_ref * 100) if stock_ref > 0 else 0
            if pourcentage <= 25:
                envoyer_email(f"⚠️ Stock Faible – {produit} (Lot {lot})",
                              f"Bonjour,\n\nLe stock du lot '{lot}' pour le produit '{produit}' est passé sous 25%.\n"
                              f"Stock restant : {stock_actuel - quantite_kilo:.2f} kg ({pourcentage:.1f}%)\n\nCordialement,\n{expediteur}")
            if stock_actuel - quantite_kilo <= 0:
                envoyer_email(f"❌ Stock Épuisé – {produit} (Lot {lot})",
                              f"Bonjour,\n\nLe lot '{lot}' du produit '{produit}' est à 0 kg.\nMerci d’en tenir compte.\n\nCordialement,\n{expediteur}")
        else:
            st.error("❌ Lot ou produit introuvable")
            return

    new_row = {
        "Date": now, "Employé": employe, "Client": client, "Fournisseur": fournisseur, "BL": bl,
        "Produit": produit, "Code de Produit": code, "Lot": lot,
        "Unité": unite, "Quantité Saisie": quantite, "Densité": densite,
        "Quantité (Kilos)": quantite_kilo
    }

    df_historique = pd.concat([df_historique, pd.DataFrame([new_row])], ignore_index=True)
    df_stock.to_excel(stock_file, index=False)
    df_historique.to_excel(historique_file, index=False)
    st.success(f"{type_mouvement} enregistrée ✅")

# === BOUTONS PRINCIPAUX ===
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("✅ Approvisionnement"):
        enregistrer_mouvement("Entrée")
with col2:
    if st.button("📦 Sortie / Conditionnement"):
        enregistrer_mouvement("Sortie")
with col3:
    if st.button("📤 Envoyer le rapport du jour"):
        aujourd_hui = datetime.now().strftime("%Y-%m-%d")
        df_jour = df_historique[df_historique["Date"].str.startswith(aujourd_hui)]
        if df_jour.empty:
            st.warning("Aucune donnée pour aujourd’hui.")
        else:
            tableau = df_jour[["Employé", "Client", "Produit", "Lot", "Quantité (Kilos)"]].to_string(index=False)
            envoyer_email(
                f"📊 Rapport Conditionnement du {aujourd_hui}",
                f"Bonjour,\n\nVoici le rapport de production du {aujourd_hui} :\n\n{tableau}\n\nCordialement,\n{expediteur}"
            )
            st.success("Rapport du jour envoyé par email.")

# === FILTRE PAR LOT ===
st.markdown("---")
st.subheader("📉 Suivi d'un Lot")

produit_sel = st.selectbox("Produit", produits)
lot_sel = st.selectbox("Lot", df_stock[df_stock["Produit"] == produit_sel]["Lot"].unique())
row = df_stock[(df_stock["Produit"] == produit_sel) & (df_stock["Lot"] == lot_sel)]

if not row.empty:
    stock = float(row["Stock Initial (Kilos)"].values[0])
    ref = float(row["Stock Initial Référence (Kilos)"].values[0])
    pourcentage = max(0, (stock / ref) * 100) if ref > 0 else 0
    couleur = "green" if pourcentage > 60 else "orange" if pourcentage > 25 else "red"
    fig, ax = plt.subplots(figsize=(6, 2.5))
    bar = ax.barh([f"{produit_sel} - Lot {lot_sel}"], [pourcentage], color=couleur)
    ax.set_xlim(0, 100)
    ax.set_xlabel("Stock (%)")
    ax.bar_label(bar, labels=[f"{pourcentage:.1f}%\n{stock:.1f} kg / {ref:.1f} kg"], fontsize=10)

    st.pyplot(fig)
if st.button("🗑️ Supprimer ce lot"):
        df_stock = df_stock[~((df_stock["Produit"] == produit_sel) & (df_stock["Lot"] == lot_sel))]
        df_stock.to_excel(stock_file, index=False)
        st.success("✅ Lot supprimé avec succès.")
        st.experimental_rerun()
   

# === RÉSUMÉ DES STOCKS ===
st.markdown("---")
st.subheader("📊 Résumé des Stocks")

df_resume = df_stock.groupby("Produit")[["Stock Initial (Kilos)"]].sum().reset_index()
df_resume["Stock Initial (Kilos)"] = df_resume["Stock Initial (Kilos)"].apply(lambda x: max(0, x))
st.dataframe(df_resume)
