# --- Assegnatore Tavoli Bilanciati con Streamlit (Bilanciamento sesso ±1 o ±2 con fallback ±3) ---
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

st.image("logo_netleg.png", width=150)
st.title("\U0001f3af Assegnatore Tavoli Bilanciati – Netleg")

soglia_flessibile = st.checkbox("Consenti bilanciamento sesso ±2 per ridurre il numero di tavoli", value=False)
soglia_max = 2 if soglia_flessibile else 1
soglia_riserva = 3
soglia_effettiva = soglia_max

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

    def eta_media(fascia):
        return {"25-34": 29.5, "35-44": 39.5, "45-54": 49.5}.get(fascia, 39.5)

    def sesso_gruppo(gruppo):
        sessi = df[df["NomeCompleto"].isin(gruppo)]["Sesso"].value_counts()
        return sessi.get("Maschio", 0), sessi.get("Femmina", 0)

    def inseribile(tavolo, gruppo, soglia):
        maschi_g, femmine_g = sesso_gruppo(gruppo)
        persone_tavolo = df[df["NomeCompleto"].isin(tavolo["persone"])]
        maschi_t = sum(persone_tavolo["Sesso"] == "Maschio")
        femmine_t = sum(persone_tavolo["Sesso"] == "Femmina")
        return abs((maschi_t + maschi_g) - (femmine_t + femmine_g)) <= soglia and len(tavolo["persone"]) + len(gruppo) <= tavolo["lim"]

    def tavoli_bilanciati(n, min_size=6, max_size=8):
        configs = []
        for num_tavoli in range(1, n // min_size + 2):
            for combo in combinations_with_replacement(range(min_size, max_size + 1), num_tavoli):
                if sum(combo) == n:
                    configs.append(sorted(list(combo)))
        return sorted(configs, key=lambda x: (len(x), max(x)-min(x)))

    def prova_configurazione(config, soglia):
        tavoli = [{"lim": cap, "persone": []} for cap in config]
        assegnati = set()
        for gruppo in sorted(gruppi, key=lambda g: -len(g)):
            for p in gruppo:
                if p in assegnati:
                    continue
                for t in sorted(tavoli, key=lambda x: len(x["persone"])):
                    if inseribile(t, [p], soglia):
                        t["persone"].append(p)
                        assegnati.add(p)
                        break
        return len(assegnati) == len(partecipanti), tavoli

    best_config = None
    best_tavoli = None
    for config in tavoli_bilanciati(len(partecipanti)):
        ok, tavoli = prova_configurazione(config, soglia_max)
        if ok:
            best_config = config
            best_tavoli = tavoli
            soglia_effettiva = soglia_max
            break
        elif soglia_max < soglia_riserva:
            ok_relaxed, tavoli_relaxed = prova_configurazione(config, soglia_riserva)
            if ok_relaxed:
                best_config = config
                best_tavoli = tavoli_relaxed
                soglia_effettiva = soglia_riserva
                break

    if not best_tavoli:
        st.error("❌ Impossibile distribuire i partecipanti rispettando i vincoli. Prova a rilassare la soglia.")
        st.stop()

    if soglia_effettiva > soglia_max:
        st.warning(f"⚠️ È stata applicata una soglia temporanea di ±{soglia_effettiva} per completare l'assegnazione.")

    rows = []
    for i, t in enumerate(best_tavoli, start=1):
        for persona in t["persone"]:
            info = df[df["NomeCompleto"] == persona].iloc[0]
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
