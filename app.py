import streamlit as st
import pandas as pd
import random
from collections import defaultdict

st.title("🎯 Assegnatore Tavoli Bilanciati")

uploaded_file = st.file_uploader("📂 Carica il file Excel con le preferenze", type=["xlsx"])

if uploaded_file:
    df = pd.read_excel(uploaded_file)

    # Pulizia e preparazione
    df.columns = [col.strip() for col in df.columns]
    df = df[["Nome", "Cognome", "Sesso", "Fascia", "Preferenze"]].copy()
    df.dropna(subset=["Nome", "Cognome", "Sesso"], inplace=True)
    df["NomeCompleto"] = df["Nome"].str.strip() + " " + df["Cognome"].str.strip()
    df["Preferenze"] = df["Preferenze"].fillna("").astype(str).str.strip()
    df["Sesso"] = df["Sesso"].str.capitalize().str.strip()
    df["Fascia"] = df["Fascia"].fillna("").astype(str).str.strip()

    # Costruzione preferenze
    preferenze_dict = defaultdict(set)
    nomi_validi = set(df["NomeCompleto"])

    for _, r in df.iterrows():
        nome = r["NomeCompleto"]
        preferenze = [p.strip() for p in r["Preferenze"].split(",") if p.strip()]
        for pref in preferenze:
            if pref in nomi_validi:
                preferenze_dict[nome].add(pref)

    # Gruppi su preferenze
    visitati = set()
    gruppi = []

    def dfs(p, gruppo):
        if p in visitati:
            return
        visitati.add(p)
        gruppo.add(p)
        for pref in preferenze_dict[p]:
            dfs(pref, gruppo)

    for p in df["NomeCompleto"]:
        if p not in visitati:
            gruppo = set()
            dfs(p, gruppo)
            gruppi.append(gruppo)

    tutti_in_gruppi = set().union(*gruppi)
    singoli = [set([p]) for p in df["NomeCompleto"] if p not in tutti_in_gruppi]
    gruppi.extend(singoli)

    # Bilanciamento tavoli
    random.shuffle(gruppi)
    tavoli = []

    def conta_sessi(persone):
        sessi = df[df["NomeCompleto"].isin(persone)]["Sesso"].value_counts()
        return sessi.get("Maschio", 0), sessi.get("Femmina", 0)

    for gruppo in gruppi:
        added = False
        for tavolo in tavoli:
            if len(tavolo) + len(gruppo) <= 8:
                potenziale = tavolo + list(gruppo)
                m, f = conta_sessi(potenziale)
                if abs(m - f) <= 2:
                    tavolo.extend(gruppo)
                    added = True
                    break
        if not added:
            tavoli.append(list(gruppo))

    # Risultati
    output_rows = []
    for i, tavolo in enumerate(tavoli, start=1):
        for nome in tavolo:
            row = df[df["NomeCompleto"] == nome].iloc[0]
            output_rows.append({
                "Tavolo": i,
                "Nome": row["Nome"],
                "Cognome": row["Cognome"],
                "Sesso": row["Sesso"],
                "Fascia": row["Fascia"],
                "Preferenze": row["Preferenze"]
            })

    df_finale = pd.DataFrame(output_rows).sort_values(by="Tavolo")
    st.success("✅ Tavoli assegnati con successo!")
    st.dataframe(df_finale)

    # Download
    excel = df_finale.to_excel(index=False, engine="openpyxl")
    st.download_button(
        label="📥 Scarica Excel",
        data=excel,
        file_name="tavoli_bilanciati.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
