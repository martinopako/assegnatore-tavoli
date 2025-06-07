# --- Assegnatore Tavoli Bilanciati con Streamlit (Bilanciamento sesso ±1 o ±2 con fallback ±3 e forzatura finale) ---
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

st.image("logo_netleg.png", width=150)
st.title("🎯 Assegnatore Tavoli Bilanciati – Netleg")

soglia_flessibile = st.checkbox("Consenti bilanciamento sesso ±2 per ridurre il numero di tavoli", value=False)
soglia_max = 2 if soglia_flessibile else 1
soglia_riserva = 3
soglia_fine = 100  # forza estrema finale
soglia_effettiva = soglia_max

uploaded_file = st.file_uploader("📁 Carica il file partecipanti.xlsx", type=["xlsx"])

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

    def tavoli_bilanciati(n, max_size=8):
        configs = []
        for num_tavoli in range(1, n + 1):
            for combo in combinations_with_replacement(range(1, max_size + 1), num_tavoli):
                if sum(combo) == n and all(1 <= x <= max_size for x in combo):
                    configs.append(sorted(list(combo)))
        return sorted(configs, key=lambda x: (len(x), max(x) - min(x)))

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

    configs = tavoli_bilanciati(len(partecipanti))
    for soglia_corrente in [soglia_max, soglia_riserva, soglia_fine]:
        for config in configs:
            ok, tavoli = prova_configurazione(config, soglia_corrente)
            if ok:
                best_config = config
                best_tavoli = tavoli
                soglia_effettiva = soglia_corrente
                break
        if best_tavoli:
            break

    if not best_tavoli:
        st.error("❌ Impossibile distribuire i partecipanti in nessuna configurazione.")
        st.stop()

    if soglia_effettiva > soglia_max:
        st.warning(f"⚠️ È stata applicata una soglia forzata di ±{soglia_effettiva} per completare l'assegnazione.")

    # Costruisci risultato finale
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
    st.success("✅ Tavoli assegnati con successo!")
    st.dataframe(st.session_state["df_result"])

    output = io.BytesIO()
    st.session_state["df_result"].to_excel(output, index=False, engine="openpyxl")
    output.seek(0)

    if st.download_button(
        "📅 Scarica risultato in Excel",
        data=output,
        file_name="tavoli_assegnati_finale.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    ):
        st.success("🎉 File scaricato. Per ricalcolare, ricarica un nuovo file.")
        st.session_state["assegnamento_confermato"] = False

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
