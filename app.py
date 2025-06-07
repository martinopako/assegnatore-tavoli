# --- Assegnatore Tavoli Bilanciati con Streamlit ---
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
        st.text_input("\U0001f512 Inserisci la password:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("\U0001f512 Inserisci la password:", type="password", on_change=password_entered, key="password")
        st.error("\u274c Password errata")
        return False
    else:
        return True

if not check_password():
    st.stop()

# Logo e titolo
st.image("logo_netleg.png", width=150)
st.title("\U0001f3af Assegnatore Tavoli Bilanciati – Netleg")

uploaded_file = st.file_uploader("\U0001f4c1 Carica il file partecipanti.xlsx", type=["xlsx"])

if "assegnamento_confermato" not in st.session_state:
    st.session_state["assegnamento_confermato"] = False

if uploaded_file and not st.session_state["assegnamento_confermato"]:
    df = pd.read_excel(uploaded_file)
    df["NomeCompleto"] = df["Nome"].str.strip() + " " + df["Cognome"].str.strip()
    df["Preferenze"] = df["Preferenze"].fillna("").str.strip()
    df["Fascia"] = df["Fascia"].fillna("").str.strip()
    df["Sesso"] = df["Sesso"].fillna("").str.capitalize()

    partecipanti = df["NomeCompleto"].tolist()
    random.seed(42)  # fissato per evitare risultati diversi
    random.shuffle(partecipanti)
    nomi_validi = set(df["NomeCompleto"])

    preferenze_dict = defaultdict(set)
    preferenze_errate = []

    for _, r in df.iterrows():
        nome = r["NomeCompleto"]
        preferenze = [p.strip() for p in r["Preferenze"].split(",") if p.strip()]
        for pref in preferenze:
            if pref not in nomi_validi:
                preferenze_errate.append((nome, pref))
            else:
                preferenze_dict[nome].add(pref)

    # Unione transitiva delle preferenze unidirezionali
    gruppi = []
    visitati = set()

    def dfs(p, gruppo):
        if p in visitati:
            return
        visitati.add(p)
        gruppo.add(p)
        for pref in preferenze_dict[p]:
            dfs(pref, gruppo)

    for p in partecipanti:
        if p not in visitati:
            gruppo = set()
            dfs(p, gruppo)
            gruppi.append(gruppo)

    # Calcolo tavoli bilanciati
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

    def eta_media(fascia):
        return {"25-34": 29.5, "35-44": 39.5, "45-54": 49.5}.get(fascia, 39.5)

    gruppi.sort(key=lambda g: -len(g))
    for gruppo in gruppi:
        gruppo = list(gruppo)
        if all(p in assegnati for p in gruppo):
            continue
        candidati = sorted(
            [t for t in tavoli if len(t["persone"]) + len(gruppo) <= t["lim"]],
            key=lambda t: (
                abs(Counter(df[df["NomeCompleto"].isin(t["persone"])]["Sesso"])['Maschio'] -
                    Counter(df[df["NomeCompleto"].isin(t["persone"])]["Sesso"])['Femmina']),
                len(t["persone"])
            )
        )
        if candidati:
            candidati[0]["persone"].extend(gruppo)
            assegnati.update(gruppo)

    # Rimanenti partecipanti
    rimanenti = [p for p in partecipanti if p not in assegnati]

    for p in rimanenti:
        info_p = df.loc[df["NomeCompleto"] == p].iloc[0]
        sesso_p = info_p["Sesso"]
        eta_p = eta_media(info_p["Fascia"])

        candidate = sorted(
            tavoli,
            key=lambda t: (
                abs(Counter(df[df["NomeCompleto"].isin(t["persone"])]["Sesso"])['Maschio'] -
                    Counter(df[df["NomeCompleto"].isin(t["persone"])]["Sesso"])['Femmina']),
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
    st.session_state["assegnamento_confermato"] = True

# Visualizza risultati solo se disponibili
if "df_result" in st.session_state:
    st.success("\u2705 Tavoli assegnati con successo!")
    st.dataframe(st.session_state["df_result"])

    output = io.BytesIO()
    st.session_state["df_result"].to_excel(output, index=False, engine="openpyxl")
    output.seek(0)

    if st.download_button(
        "\U0001f4e5 Scarica risultato in Excel",
        data=output,
        file_name="tavoli_assegnati_finale.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ):
        st.success("\U0001f389 File scaricato. Per ricalcolare, ricarica un nuovo file.")
        st.session_state["assegnamento_confermato"] = False

    st.subheader("\U0001f4ca Riepilogo per Tavolo (Sesso & Et\u00e0 Media)")
    df_r = st.session_state["df_result"].copy()
    df_r["Et\u00e0MediaStimata"] = df_r["Fascia"].map(lambda f: {"25-34": 29.5, "35-44": 39.5, "45-54": 49.5}.get(f, 39.5))
    riepilogo = df_r.groupby("Tavolo").agg(
        Maschi=("Sesso", lambda x: sum(x == "Maschio")),
        Femmine=("Sesso", lambda x: sum(x == "Femmina")),
        EtaMedia=("Et\u00e0MediaStimata", "mean"),
        Totale=("Sesso", "count")
    ).reset_index()
    st.dataframe(riepilogo)

    if st.session_state["preferenze_errate"]:
        st.warning("\u26a0\ufe0f Nomi nelle preferenze non trovati:")
        st.dataframe(pd.DataFrame(st.session_state["preferenze_errate"], columns=["Chi ha scritto", "Nome non valido"]))
