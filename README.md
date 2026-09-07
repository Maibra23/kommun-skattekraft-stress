## Skattekraft i svenska kommuner: läge, förflyttning och vad som förklarar dem

Det här projektet mäter var Sveriges 290 kommuner står i skattekraft mot riksgenomsnittet, åt vilket håll de rör sig, och vilka strukturella faktorer som förklarar skillnaderna. Det är i första hand **beskrivande**: modellen förklarar skillnader mellan kommuner, den förutsäger dem inte.

**Vad ingår?**

- 290 kommuner över 17 år (2010–2026), 4 930 observationer
- **Relativ position och förflyttning** över 1, 3, 5 och 10 år — projektets mest tillförlitliga resultat, och det enda som inte kräver någon modell
- **Tvärsnittsmodell** som förklarar 69 % av skillnaderna mellan kommuner, med explicit redovisning av vilka variabler som går att särskilja och vilka som inte gör det
- **Panelmodell** (tvåvägs fixed effects) för samband inom kommuner över tid — en annan fråga, och inte en rangordning
- **Femårsprognos** för förflyttning, testad mot utfall innan den publiceras (Spearman +0,33), med intervall som kommer från prognosens egna träffar
- Interaktivt Streamlit-dashboard med tre vyer

**Varför?** Skattekraften varierar enormt: ~481 000 kr per invånare i Danderyd mot under 180 000 kr i delar av Norrland. Frågan projektet svarar på är *vad som förklarar den skillnaden* — och, i andra hand, hur mycket av den som går att förutsäga. Svaret på det andra är: mindre än man skulle vilja, och projektet redovisar det öppet.

> **Om projektets historia.** En tidigare version rangordnade kommuner efter en prognosticerad tillväxt för 2025 som aldrig hade testats mot utfall. När horisonten stängde och den testades blev korrelationen med faktisk tillväxt **+0,02**, och den förlorade mot att gissa riksgenomsnittet. Hela modellagret gjordes om under 2026-09; se `docs/REMEDIATION_PLAN.md` och `docs/DEVIATIONS.md` §6.4.

## Modell

Regressionsspecifikation (tvåvägs fixed effects):

```
DeltaSkattekraft_it = alpha_i + gamma_t + beta_1*Arbetsloshet_it + beta_2*Forsorjningskvot_it
                      + beta_3*Befolkningstillvaxt_it + beta_4*Utbildningsandel_it + epsilon_it
```

Där *i* indexerar kommun (290), *t* indexerar år. Standardfel klustrade på kommunnivå. Estimerad med `linearmodels.PanelOLS`. **Den primära specifikationen laggar högerledet ett år** — varje variabels samband med tillväxten är starkast vid t−1 eller senare, vilket följer av att skattekraften publiceras med två års eftersläpning.

Den här panelmodellen svarar på frågan *inom en kommun över tid*. Den kan inte rangordna kommuner: 98 % av variationen i relativ position ligger **mellan** kommuner, och det är precis den variation kommun-effekterna räknar bort.

**Rangordningen kommer i stället från en tvärsnittsmodell** på samma fyra variabler, utan kommun-effekter, skattad på det senaste året där alla variabler finns. R² = 0,69. Av de fyra variablerna går bara två att särskilja mellan kommuner — utbildningsandel (+10,0 indexenheter per standardavvikelse) och öppen arbetslöshet (−2,7). Försörjningskvot och befolkningstillväxt ingår som kontroller; deras konfidensintervall omsluter noll i varje år 2021–2024.

**Prognos:** femårig förflyttning i relativ position, inte ettårig tillväxt — den senare går inte att återskapa ur datan. Prognosen testas mot varje tillgängligt startår innan den publiceras och skrivs inte alls om den inte klarar sin egen gräns.

Se `[docs/METHODOLOGY.md](docs/METHODOLOGY.md)` för fullständig metodbeskrivning inklusive robusthetsanalyser och begränsningar.

## Datakällor


| Källa                  | Tabell-ID | Variabel                    | Period    |
| ---------------------- | --------- | --------------------------- | --------- |
| SCB Statistikdatabasen | OE0101    | Skattekraft per invånare    | 2009-2024 |
| SCB Statistikdatabasen | BE0101    | Folkmängd (ålder, kön)      | 2009-2024 |
| SCB Statistikdatabasen | AA0003    | Öppen arbetslöshet (STATIV) | 2010-2024 |
| SCB Statistikdatabasen | UF0506    | Utbildningsnivå             | 2010-2024 |
| okfse/sweden-geojson   | .         | Kommungränser (GeoJSON)     | 2024      |


Se `[docs/KRI_Dataset_Identification.md](docs/KRI_Dataset_Identification.md)` för detaljerad datarevision med API-endpoints, query-parametrar och validering.

## Köra lokalt

### Förutsättningar

Python 3.11 och Git.

### Installation

```bash
git clone https://github.com/mustafa-2024/kommun-skattekraft-stress.git
cd kommun-skattekraft-stress
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Kör datapipelinen

Pipelinen hämtar data från SCB:s API, rensar, estimerar modellen och genererar alla artefakter:

```bash
python pipeline.py
```

### Starta dashboarden

```bash
streamlit run app.py
```

Öppna `http://localhost:8501` i webbläsaren.

### Kör tester

```bash
pytest
```

## Filstruktur

```
kommun-skattekraft-stress/
    app.py                          # Startsida (Översikt)
    pipeline.py                     # Orkestrerar fetch, clean, estimate, predict, decompose
    pages/
        01_Riksoversikt.py          # Nationell vy med karta och rangordning
        02_Kommunjamforelse.py       # Kommundetalj med dekomponering
    src/
        fetch/                      # SCB PxWeb API-klienter
            pxweb_client.py         # Generisk POST + chunking
            fetch_skattekraft.py    # OE0101
            fetch_population.py     # BE0101 (med per-års-chunkning)
            fetch_unemployment.py   # AA0003 (tvåtabellsstrategi)
            fetch_education.py      # UF0506
        clean/                      # Harmonisering och härledda variabler
            harmonize_kommunkod.py  # Kommunkodsmapping till 2024 gränser
            compute_derived.py      # Försörjningskvot, tillväxttakt
            build_panel.py          # Bygg balanserad 290x15 panel
        model/                      # Ekonometri
            estimate.py             # PanelOLS med robusthetsspecifikationer
            predict.py              # Prognos 2025 (utfasad, se DEVIATIONS 6.4)
            forecast.py             # Femårsprognos, grindad av sitt eget backtest
            backtest.py             # Rullande ursprung: testar innan publicering
            decompose.py            # Strukturell dekomponering
        ui/                         # Streamlit-komponenter
            css.py                  # Designsystem (färger, typografi, CSS)
            components.py           # KPI-kort, sidtitel, footer
            sidebar.py              # Gemensam sidebar
            chart_theme.py          # Plotly-tema
            choropleth.py           # Folium-karta
            labels.py               # SWEDISH_LABELS + nummerformatering
    artifacts/                      # Förberäknade resultat (laddas av Streamlit)
        model_results.pkl           # Fitted PanelOLS-objekt
        coefficients.parquet        # Regressionskoefficienter
        predictions.parquet         # 290 kommuner x prognos 2025 (utfasad)
        forecast.parquet            # Femårsprognos + intervall + backtest-resultat
        decomposition.parquet       # Strukturell bidragsanalys
        ranking.parquet             # Sårbarhetsrankning
    data/
        raw/                        # Cachade SCB-svar (JSON)
        processed/panel.parquet     # Rensad 290x15 panel
        geo/kommuner.geojson        # Kommungränser
        lookup/                     # Statisk kommunkodsmapping
    tests/                          # pytest-tester
    docs/                           # Dokumentation
        PRD.md                      # Produktkrav (läst specifikation)
        TASKS.md                    # Implementeringsuppgifter
        METHODOLOGY.md              # Ekonometrisk metod
        KRI_Dataset_Identification.md  # Datakällrevision
    notebooks/
        01_exploratory.ipynb        # EDA
```

## Begränsningar

Modellen har flera kända begränsningar, dokumenterade i `[docs/METHODOLOGY.md` avsnitt 7](docs/METHODOLOGY.md#7-known-limitations-volunteer-in-interviews):

- **Två av fyra variabler går inte att särskilja mellan kommuner.** Försörjningskvot och befolkningstillväxt redovisas som kontroller, inte som drivkrafter. Orsaken är skala, inte kollinearitet: försörjningskvotens spridning mellan kommuner är 0,116
- **Utbildningsandelen ligger nära en omskrivning.** Den korrelerar +0,81 med skattekraften och är inte en spak att dra i — se METHODOLOGY §7.15
- **Dekomponeringen träffar sämst i toppen.** För Danderyd är halva avvikelsen oförklarad; för Filipstad nästan ingen
- **Prognosen är blygsam.** Spearman +0,33 betyder att ordningen mellan kommuner till stor del förblir oförutsägbar. Intervallen är breda av samma skäl, och de redovisas
- **Ettårig tillväxt går inte att förutsäga** ur den här datan; årsavvikelsernas autokorrelation är ungefär −0,05
- Simultaneitet: fixed effects adresserar inte omvänd kausalitet
- Nominell skattekraft inkluderar inflation, inte realt justerad
- Två index med olika nämnare redovisas parallellt och får aldrig blandas — se METHODOLOGY §7.13

## Källor

- SCB Statistikdatabasen: [statistikdatabasen.scb.se](https://www.statistikdatabasen.scb.se/)
  - [OE0101 Skattekraft](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__OE__OE0101/SkatteKraft/)
  - [BE0101 Folkmängd](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__BE__BE0101__BE0101A/BefolkningNy/)
  - [AA0003 Öppen arbetslöshet](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__AA__AA0003/)
  - [UF0506 Utbildningsnivå](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__UF__UF0506__UF0506B/Utbildning/)
- Kommungränser: [okfse/sweden-geojson](https://github.com/okfse/sweden-geojson)

## Licens

MIT, se [LICENSE](LICENSE).
