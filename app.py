import streamlit as st
import pandas as pd
import random
from collections import defaultdict, Counter
from itertools import combinations_with_replacement
import io

# --- LOGIN con password semplice ---
def check_password():
    def password_entered():
        if st.session_state["password"] == "Netleg123":
            st.session_state["password_correct"] = True
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        st.text_input("🔒 Inserisci la password per accedere:", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        st.text_input("🔒 Inserisci la password per accedere:", type="password", on_change=password_entered, key="password")
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

if uploaded_file:
    df = pd.read_excel(uploaded_file)
    df["NomeCompleto"] = df["Nome"].str.strip() + " " + df["Cognome"].str.strip()
    df["Preferenze"] = df["Preferenze"].fillna("").str.strip()
    df["Fascia"] = df["Fascia"].fillna("").str.strip()
    df["Sesso"] = df["Sesso"].fillna("").str.upper()

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
        t = primo_tavolo_con_spazio(len(gruppo))
        if t:
            t["persone"].extend(gruppo)
            assegnati.update(gruppo)
        else:
            for p in gruppo:
                t_individuale = primo_tavolo_con_spazio(1)
                if t_individuale:
                    t_individuale["persone"].append(p)
                    assegnati.add(p)

    rimanenti = [p for p in partecipanti if p not in assegnati]

    for p in rimanenti:
        info_p = df.loc[df["NomeCompleto"] == p].iloc[0]
        fascia_p, sesso_p = info_p["Fascia"], info_p["Sesso"]

        def score(t):
            persone = t["persone"]
            sessi = df[df["NomeCompleto"].isin(persone)]["Sesso"].tolist()
            maschi = sessi.count("M")
            femmine = sessi.count("F")
            if sesso_p == "M":
                sbilanciamento = maschi
            else:
                sbilanciamento = femmine
            return (
                sbilanciamento,
                abs(maschi - femmine)
            )

        candidate = sorted(
            [t for t in tavoli if len(t["persone"]) < t["lim"]],
            key=score
        )

        if candidate:
            candidate[0]["persone"].append(p)

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
    st.success("✅ Tavoli assegnati!")

    st.dataframe(df_result)

    output = io.BytesIO()
    df_result.to_excel(output, index=False, engine="openpyxl")
    output.seek(0)

    st.download_button(
        "📥 Scarica risultato in Excel",
        data=output,
        file_name="tavoli_assegnati_finale.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

    if preferenze_errate:
        st.warning("⚠️ Nomi nelle preferenze non trovati:")
        st.dataframe(pd.DataFrame(preferenze_errate, columns=["Chi ha scritto", "Nome non valido"]))
