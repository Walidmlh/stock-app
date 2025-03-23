# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import smtplib
from email.message import EmailMessage
import os

# === CONFIGURATION ===
st.set_page_config(page_title="📦 Suivi de Stock", layout="centered")

EMAIL = "moulaihcenewalidro@gmail.com"
APP_PASSWORD = "osva szaz sngc ljxa"

stock_file = "stock_initial_test.xlsx"
historique_file = "historique_journalier.xlsx"

# === CHARGEMENT ===
if os.path.exists(stock_file):
    df_stock = pd.read_excel(stock_file)
else:
    df_stock = pd.DataFrame(columns=["Produit", "Code de Produit", "Lot", "Stock Initial (Kilos)", "Stock Initial Référence (Kilos)", "Densité"])

if os.path.exists(historique_file):
    df_historique = pd.read_excel(historique_file)
else:
    df_historique = pd.DataFrame(columns=["Date", "Employé", "Client", "Fournisseur", "BL", "Produit", "Code de Produit", "Lot", "Unité", "Quantité Saisie", "Densité", "Quantité (Kilos)"])

# === LISTES DYNAMIQUES ===
produits = sorted(df_stock["Produit"].dropna().unique().tolist())
clients = sorted([c for c in df_historique["Client"].dropna().unique() if c != "HHHHH"])
employes = sorted(df_historique["Employé"].dropna().unique())
fournisseurs = sorted(set(df_historique["Fournisseur"].dropna().unique().tolist() + ["Premium Good", "Ilanga"]))

# === TITRE ===
st.title("📦 Suivi de Stock – Application Complète")

# === INTERFACE SAISIE ===
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
        if employe and employe not in employes:
            employes.append(employe)

    client = st.selectbox("Client", clients + ["🔹 Nouveau..."])
    if client == "🔹 Nouveau...":
        client = st.text_input("➡️ Nouveau client")
        if client and client not in clients:
            clients.append(client)

    fournisseur = st.selectbox("Fournisseur", fournisseurs + ["🔹 Nouveau..."])
    if fournisseur == "🔹 Nouveau...":
        fournisseur = st.text_input("➡️ Nouveau fournisseur")

# === CODE PRODUIT + DENSITÉ ===
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
        st.info("📩 Email envoyé.")
    except Exception as e:
        st.error(f"Erreur email : {e}")

# === ENREGISTRER ===
def enregistrer_mouvement(type_mouvement):
    global df_stock, df_historique
    if not all([produit, lot, bl, quantite > 0]):
        st.warning("⚠️ Remplissez tous les champs obligatoires (*)")
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
                st.error(f"❌ Stock insuffisant : disponible {stock_actuel:.2f} kg, demandé {quantite_kilo:.2f} kg.")
                return
            df_stock.at[idx[0], "Stock Initial (Kilos)"] -= quantite_kilo

            stock_ref = df_stock.at[idx[0], "Stock Initial Référence (Kilos)"]
            reste = stock_actuel - quantite_kilo
            pourcentage = max(0, (reste / stock_ref) * 100) if stock_ref > 0 else 0

            if pourcentage <= 25:
                envoyer_email(
                    f"⚠️ Stock Faible – {produit} (Lot {lot})",
                    f"Bonjour,\n\nLe stock du lot '{lot}' pour le produit '{produit}' est sous 25%.\nStock restant : {reste:.2f} kg ({pourcentage:.1f}%)\n\nCordialement,\n{expediteur}"
                )
            if reste <= 0:
                envoyer_email(
                    f"❌ Stock Épuisé – {produit} (Lot {lot})",
                    f"Bonjour,\n\nLe lot '{lot}' du produit '{produit}' est épuisé (0 kg).\n\nCordialement,\n{expediteur}"
                )
        else:
            st.error("❌ Produit ou lot introuvable.")
            return

    new_row = {
        "Date": now, "Employé": employe, "Client": client, "Fournisseur": fournisseur, "BL": bl,
        "Produit": produit, "Code de Produit": code, "Lot": lot,
        "Unité": unite, "Quantité Saisie": quantite, "Densité": densite, "Quantité (Kilos)": quantite_kilo
    }

    df_historique = pd.concat([df_historique, pd.DataFrame([new_row])], ignore_index=True)
    df_stock.to_excel(stock_file, index=False)
    df_historique.to_excel(historique_file, index=False)
    st.success(f"{type_mouvement} enregistrée ✅")

def envoyer_rapport_journalier_excel():
    aujourd_hui = datetime.now().strftime("%Y-%m-%d")
    df_jour = df_historique[df_historique["Date"].astype(str).str.startswith(aujourd_hui)]

    if df_jour.empty:
        st.warning("Aucune donnée pour aujourd’hui.")
        return

    # Générer un fichier Excel temporaire
    file_name = f"rapport_conditionnement_{aujourd_hui}.xlsx"
    df_jour.to_excel(file_name, index=False)

    # Préparer l’email avec pièce jointe
    msg = EmailMessage()
    msg["Subject"] = f"📊 Rapport Conditionnement du {aujourd_hui}"
    msg["From"] = EMAIL
    msg["To"] = EMAIL
    msg.set_content(
        f"Bonjour,\n\nVeuillez trouver en pièce jointe le rapport journalier du {aujourd_hui}.\n\nCordialement,\n{expediteur}"
    )

    try:
        with open(file_name, "rb") as f:
            msg.add_attachment(f.read(), maintype="application", subtype="octet-stream", filename=file_name)

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
            smtp.login(EMAIL, APP_PASSWORD)
            smtp.send_message(msg)

        st.success("📤 Rapport Excel envoyé par email avec succès.")
    except Exception as e:
        st.error(f"Erreur lors de l’envoi de l’email : {e}")

# === BOUTONS PRINCIPAUX ===
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("✅ Approvisionnement"):
        enregistrer_mouvement("Entrée")
with col2:
    if st.button("📦 Sortie / Conditionnement"):
        enregistrer_mouvement("Sortie")
with col3:
    if st.button("📤 Envoyer le rapport du jour (Excel)"):
        envoyer_rapport_journalier_excel()


# === FILTRE PAR LOT ===
st.markdown("---")
st.subheader("📉 Suivi d’un Lot")
produit_sel = st.selectbox("Produit 🎯", produits)
lots = df_stock[df_stock["Produit"] == produit_sel]["Lot"].unique()
lot_sel = st.selectbox("Lot 🎯", lots)

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
        st.success("✅ Lot supprimé.")
        st.experimental_rerun()

# === RÉSUMÉ DES STOCKS ===
st.markdown("---")
st.subheader("📊 Résumé détaillé des Stocks")

df_resume = df_stock.copy()
df_resume["% Stock"] = ((df_resume["Stock Initial (Kilos)"] / df_resume["Stock Initial Référence (Kilos)"]) * 100).round(1)
df_resume["% Stock"] = df_resume["% Stock"].apply(lambda x: max(0, min(x, 100)))
df_resume["Stock Initial (Kilos)"] = df_resume["Stock Initial (Kilos)"].apply(lambda x: max(0, x))
st.dataframe(df_resume[["Produit", "Code de Produit", "Lot", "Stock Initial (Kilos)", "Stock Initial Référence (Kilos)", "% Stock"]])
