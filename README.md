# Kommunal Skattekraft Stress Monitor

En modell over skattekraftens utveckling i Sveriges 290 kommuner, med prognoser och strukturell dekomponering.

## Abstract

A two-way fixed-effects panel model of Swedish municipal tax base growth, with predictive vulnerability ranking and structural decomposition, delivered as a Streamlit dashboard. The panel covers 290 municipalities x 15 years (2010-2024) using four structural drivers: unemployment rate, dependency ratio, population growth, and tertiary education share. Predicted 2025 growth and vulnerability ranks are precomputed and served as Parquet artifacts.

## Om projektet

Skattekraften (beskattningsbar forvarvsinkomst per invanare) ar det centrala mattet pa en kommuns skattemassiga kapacitet. Skillnaderna mellan kommuner ar enorma: Danderyd rapporterade ca 481 000 kr per invanare 2024, medan flera Norrlandskommuner lag under 180 000 kr.

Det har projektet bygger en panelmodell (tvavags fixed effects) som identifierar vilka kommuner som har den svagaste prognosticerade skattekraftstillvaxten och vilka strukturella faktorer som driver variationen. Resultaten levereras som en interaktiv Streamlit-dashboard med tre sidor: en oversikt, en nationell kartvy med rangordning, och en kommundetaljsida med strukturell dekomponering.

**Malgrupp:** Kreditanalytiker, kommunala controllers, SKR-analytiker, regionala beslutsfattare.

## Skarmdumpar

> *Skarmdumpar laggs till efter driftsattning pa Streamlit Cloud.*

| Oversikt | Riksoversikt | Kommunjamforelse |
|:---:|:---:|:---:|
| ![Oversikt](docs/screenshots/landing.png) | ![Riksoversikt](docs/screenshots/riksoversikt.png) | ![Kommunjamforelse](docs/screenshots/kommunjamforelse.png) |

## Modell

Regressionsspecifikation (tvavags fixed effects):

```
DeltaSkattekraft_it = alpha_i + gamma_t + beta_1*Arbetsloshet_it + beta_2*Forsorjningskvot_it
                      + beta_3*Befolkningstillvaxt_it + beta_4*Utbildningsandel_it + epsilon_it
```

Dar *i* indexerar kommun (290), *t* indexerar ar (2010-2024). Standardfel klustrade pa kommunniva. Estimerad med `linearmodels.PanelOLS`.

**Sarbarhetsindex:** Prognosticerad tillvaxt 2025 standardiseras (z-poang, teckenvand sa hogt = sarbar). Nedre kvintilen (58 kommuner) klassas som "Hog risk".

Se [`docs/METHODOLOGY.md`](docs/METHODOLOGY.md) for fullstandig metodbeskrivning inklusive robusthetsanalyser och begransningar.

## Datakallor

| Kalla | Tabell-ID | Variabel | Period |
|---|---|---|---|
| SCB Statistikdatabasen | OE0101 | Skattekraft per invanare | 2009-2024 |
| SCB Statistikdatabasen | BE0101 | Folkmangd (alder, kon) | 2009-2024 |
| SCB Statistikdatabasen | AA0003 | Oppen arbetsloshet (STATIV) | 2010-2024 |
| SCB Statistikdatabasen | UF0506 | Utbildningsniva | 2010-2024 |
| okfse/sweden-geojson | . | Kommungrenser (GeoJSON) | 2024 |

Se [`docs/KRI_Dataset_Identification.md`](docs/KRI_Dataset_Identification.md) for detaljerad datarevision med API-endpoints, query-parametrar och validering.

## Kora lokalt

### Forutsattningar

Python 3.11 och Git.

### Installation

```bash
git clone https://github.com/mustafa-2024/kommun-skattekraft-stress.git
cd kommun-skattekraft-stress
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Kor datapipelinen

Pipelinen hamtar data fran SCB:s API, rensar, estimerar modellen och genererar alla artefakter:

```bash
python pipeline.py
```

### Starta dashboarden

```bash
streamlit run app.py
```

Oppna `http://localhost:8501` i webblasaren.

### Kor tester

```bash
pytest
```

## Filstruktur

```
kommun-skattekraft-stress/
    app.py                          # Startsida (Oversikt)
    pipeline.py                     # Orkestrerar fetch, clean, estimate, predict, decompose
    pages/
        01_Riksoversikt.py          # Nationell vy med karta och rangordning
        02_Kommunjamforelse.py       # Kommundetalj med dekomponering
    src/
        fetch/                      # SCB PxWeb API-klienter
            pxweb_client.py         # Generisk POST + chunking
            fetch_skattekraft.py    # OE0101
            fetch_population.py     # BE0101 (med per-ars-chunkning)
            fetch_unemployment.py   # AA0003 (tvatabellssplitsa)
            fetch_education.py      # UF0506
        clean/                      # Harmonisering och harledda variabler
            harmonize_kommunkod.py  # Kommunkodsmapping till 2024 granser
            compute_derived.py      # Forsorjningskvot, tillvaxttakt
            build_panel.py          # Bygg balanserad 290x15 panel
        model/                      # Ekonometri
            estimate.py             # PanelOLS med robusthetsspecifikationer
            predict.py              # Prognos 2025
            decompose.py            # Strukturell dekomponering
        ui/                         # Streamlit-komponenter
            css.py                  # Designsystem (farger, typografi, CSS)
            components.py           # KPI-kort, sidtitel, footer
            sidebar.py              # Gemensam sidebar
            chart_theme.py          # Plotly-tema
            choropleth.py           # Folium-karta
            labels.py               # SWEDISH_LABELS + nummerformatering
    artifacts/                      # Forberaknade resultat (laddas av Streamlit)
        model_results.pkl           # Fitted PanelOLS-objekt
        coefficients.parquet        # Regressionskoefficienter
        predictions.parquet         # 290 kommuner x prognos 2025
        decomposition.parquet       # Strukturell bidragsanalys
        ranking.parquet             # Sarbarhetsrankning
    data/
        raw/                        # Cachade SCB-svar (JSON)
        processed/panel.parquet     # Rensad 290x15 panel
        geo/kommuner.geojson        # Kommungrenser
        lookup/                     # Statisk kommunkodsmapping
    tests/                          # pytest-tester
    docs/                           # Dokumentation
        PRD.md                      # Produktkrav (last specifikation)
        TASKS.md                    # Implementeringsuppgifter
        METHODOLOGY.md              # Ekonometrisk metod
        KRI_Dataset_Identification.md  # Datakallrevision
    notebooks/
        01_exploratory.ipynb        # EDA
```

## Begransningar

Modellen har flera kanda begransningar, dokumenterade i [`docs/METHODOLOGY.md` avsnitt 7](docs/METHODOLOGY.md#7-known-limitations-volunteer-in-interviews):

- Lag R2(within) (~0,8 %) ar forvantat efter tvavags demeaning; ar-fixed effects absorberar >95 % av variationen
- Befolkningstillvaxtens negativa koefficient reflekterar within-entity-dynamik (tillfallig per-capita-utspadning), inte tvarsnittssamband
- Simultaneitet: tvavags FE adresserar inte omvand kausalitet
- Nominell skattekraft inkluderar inflation, inte realt justerad
- Utbildningsandel insignifikant: for lite within-variation under 15-arsperioden

## Kallor

- SCB Statistikdatabasen: [statistikdatabasen.scb.se](https://www.statistikdatabasen.scb.se/)
  - [OE0101 Skattekraft](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__OE__OE0101/SkatteKraft/)
  - [BE0101 Folkmangd](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__BE__BE0101__BE0101A/BefolkningNy/)
  - [AA0003 Oppen arbetsloshet](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__AA__AA0003/)
  - [UF0506 Utbildningsniva](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__UF__UF0506__UF0506B/Utbildning/)
- Kommungrenser: [okfse/sweden-geojson](https://github.com/okfse/sweden-geojson)

## Licens

MIT, se [LICENSE](LICENSE).
