for p in rimanenti:
    info_p = df.loc[df["NomeCompleto"] == p].iloc[0]
    fascia_p, sesso_p = info_p["Fascia"], info_p["Sesso"]

    # Bilanciamento uomo/donna più forte
    def score(t):
        persone = t["persone"]
        sessi = df[df["NomeCompleto"].isin(persone)]["Sesso"].tolist()
        maschi = sessi.count("M")
        femmine = sessi.count("F")
        sbilanciamento = abs(maschi - femmine)
        stessa_fascia = sum(df[df["NomeCompleto"].isin(persone)]["Fascia"] == fascia_p)
        return (
            stessa_fascia,     # preferiamo tavoli con meno persone della stessa fascia
            sbilanciamento     # e tavoli con sbilanciamento minore
        )

    candidate = sorted(
        [t for t in tavoli if len(t["persone"]) < t["lim"]],
        key=score
    )

    if candidate:
        candidate[0]["persone"].append(p)
