import streamlit as st
import pandas as pd
import random
from collections import defaultdict, Counter
from itertools import combinations_with_replacement
import io

# --- LOGIN ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "Netleg123":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔐 Inserisci la password:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔐 Inserisci la password:", type="password", on_change=password_entered, key="password")
        st.error("❌ Password errata")
        return False
    else:
        return True

if not check_password():
    st.stop()

# Logo e titolo
st.image("logo_netleg.png", width=150)
st.title("🎯 Assegnatore Tavoli Bilanciati – Netleg")

uploaded_file = st.file_uploader("📁 Carica il file partecipanti.xlsx", type=["xlsx"])

# Pulsante per ricalcolare
if "ricalcola" not in st.session_state:
    st.session_state["ricalcola"] = False

if uploaded_file:
    if st.button("🔁 Ricalcola Tavoli"):
        st.session_state["ricalcola"] = True

    # Se i tavoli non sono stati ancora calcolati o se premi "Ricalcola"
    if "df_result" not in st.session_state or st.session_state["ricalcola"]:
        df = pd.read_excel(uploaded_file)
        df["NomeCompleto"] = df["Nome"].str.strip() + " " + df["Cognome"].str.strip()
        df["Preferenze"] = df["Preferenze"].fillna("").str.strip()
        df["Fascia"] = df["Fascia"].fillna("").str.strip()
        df["Sesso"] = df["Sesso"].fillna("").str.capitalize()

        partecipanti = df["NomeCompleto"].tolist()
        random.shuffle(partecipanti)
        nomi_validi = set(df["NomeCompleto"])

        preferenze_dict = defaultdict(list)
        preferenze_errate = []

        for _, r in df.iterrows():
            nome = r["NomeCompleto"]
            preferenze = [p.strip() for p in r["Preferenze"].split(",") if p.strip()]
            for pref in preferenze:
                if pref not in nomi_validi:
                    preferenze_errate.append((nome, pref))
                else:
                    preferenze_dict[nome].append(pref)

        def tavoli_bilanciati(n, min_size=6, max_size=8):
            migliori = []
            for num_tavoli in range(1, n // min_size + 2):
                for combo in combinations_with_replacement(range(min_size, max_size + 1), num_tavoli):
                    if sum(combo) == n:
                        diff = max(combo) - min(combo)
                        if not migliori or (
                            len(combo) < len(migliori[0]) or
                            (len(combo) == len(migliori[0]) and diff < (max(migliori[0]) - min(migliori[0])))
                        ):
                            migliori = [list(combo)]
                        elif (
                            len(combo) == len(migliori[0]) and
                            diff == (max(migliori[0]) - min(migliori[0]))
                        ):
                            migliori.append(list(combo))
            return sorted(migliori[0]) if migliori else [n]

        capienze = tavoli_bilanciati(len(partecipanti))
        tavoli = [{"lim": cap, "persone": []} for cap in capienze]
        assegnati = set()

        def primo_tavolo_con_spazio(k):
            return next((t for t in tavoli if len(t["persone"]) + k <= t["lim"]), None)

        gruppi_preferenze = []
        for p in partecipanti:
            if p in assegnati:
                continue
            gruppo = {p}
            for pref in preferenze_dict.get(p, []):
                if pref in partecipanti:
                    gruppo.add(pref)
            unito = False
            for g in gruppi_preferenze:
                if not gruppo.isdisjoint(g):
                    g.update(gruppo)
                    unito = True
                    break
            if not unito:
                gruppi_preferenze.append(gruppo)

        gruppi_preferenze.sort(key=lambda g: -len(g))

        for gruppo in gruppi_preferenze:
            gruppo = list(gruppo)
            if all(p in assegnati for p in gruppo):
                continue
            t_candidato = sorted(
                [t for t in tavoli if len(t["persone"]) + len(gruppo) <= t["lim"]],
                key=lambda t: (
                    abs(Counter(df[df["NomeCompleto"].isin(t["persone"])]["Sesso"])["Maschio"] -
                        Counter(df[df["NomeCompleto"].isin(t["persone"])]["Femmina"]),
                    len(t["persone"])
                )
            )
            if t_candidato:
                t_candidato[0]["persone"].extend(gruppo)
                assegnati.update(gruppo)

        rimanenti = [p for p in partecipanti if p not in assegnati]

        def eta_media(fascia):
            return {"25-34": 29.5, "35-44": 39.5, "45-54": 49.5}.get(fascia, 39.5)

        for p in rimanenti:
            info_p = df.loc[df["NomeCompleto"] == p].iloc[0]
            sesso_p = info_p["Sesso"]
            eta_p = eta_media(info_p["Fascia"])

            candidate = sorted(
                tavoli,
                key=lambda t: (
                    abs(Counter(df[df["NomeCompleto"].isin(t["persone"])]["Sesso"])["Maschio"] -
                        Counter(df[df["NomeCompleto"].isin(t["persone"])]["Femmina"]),
                    abs(
                        eta_p - df[df["NomeCompleto"].isin(t["persone"])]["Fascia"].map(eta_media).mean()
                        if t["persone"] else 0
                    ),
                    len(t["persone"])
                )
            )
            for t in candidate:
                if len(t["persone"]) < t["lim"]:
                    t["persone"].append(p)
                    assegnati.add(p)
                    break

        rows = []
        for i, t in enumerate(tavoli, start=1):
            for persona in t["persone"]:
                info = df.loc[df["NomeCompleto"] == persona].iloc[0]
                rows.append({
                    "Tavolo":      i,
                    "Nome":        info["Nome"],
                    "Cognome":     info["Cognome"],
                    "Fascia":      info["Fascia"],
                    "Sesso":       info["Sesso"],
                    "Preferenze":  info["Preferenze"]
                })

        df_result = pd.DataFrame(rows)
        st.session_state["df_result"] = df_result
        st.session_state["preferenze_errate"] = preferenze_errate
        st.session_state["ricalcola"] = False  # Reset dopo esecuzione

    # Mostra risultati salvati in sessione
    st.success("✅ Tavoli assegnati con successo!")
    st.dataframe(st.session_state["df_result"])

    # Download
    output = io.BytesIO()
    st.session_state["df_result"].to_excel(output, index=False, engine="openpyxl")
    output.seek(0)

    st.download_button(
        "📥 Scarica risultato in Excel",
        data=output,
        file_name="tavoli_assegnati_finale.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    # Riepilogo
    st.subheader("📊 Riepilogo per Tavolo (Sesso & Età Media)")
    df_r = st.session_state["df_result"].copy()
    df_r["EtàMediaStimata"] = df_r["Fascia"].map(lambda f: {"25-34": 29.5, "35-44": 39.5, "45-54": 49.5}.get(f, 39.5))
    riepilogo = df_r.groupby("Tavolo").agg(
        Maschi=("Sesso", lambda x: sum(x == "Maschio")),
        Femmine=("Sesso", lambda x: sum(x == "Femmina")),
        EtaMedia=("EtàMediaStimata", "mean"),
        Totale=("Sesso", "count")
    ).reset_index()
    st.dataframe(riepilogo)

    if st.session_state["preferenze_errate"]:
        st.warning("⚠️ Nomi nelle preferenze non trovati:")
        st.dataframe(pd.DataFrame(st.session_state["preferenze_errate"], columns=["Chi ha scritto", "Nome non valido"]))
