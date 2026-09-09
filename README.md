# Skattekraftspanelen

## Skattekraft i svenska kommuner: läge, förflyttning och vad som förklarar dem

Det här projektet mäter var Sveriges 290 kommuner står i skattekraft mot riksgenomsnittet, åt vilket håll de rör sig, och vilka strukturella faktorer som förklarar skillnaderna. Det är i första hand **beskrivande**: modellen förklarar skillnader mellan kommuner, den förutsäger dem inte.

**Vad ingår?**

- 290 kommuner över 17 år (2010–2026), 4 930 observationer
- **Relativ position och förflyttning** över 1, 3, 5 och 10 år — projektets mest tillförlitliga resultat, och det enda som inte kräver någon modell
- **Tvärsnittsmodell** som förklarar 69 % av skillnaderna mellan kommuner, med explicit redovisning av vilka variabler som går att särskilja och vilka som inte gör det
- **Panelmodell** (tvåvägs fixed effects) för samband inom kommuner över tid — en annan fråga, och inte en rangordning
- **Femårsprognos** för förflyttning, testad mot utfall innan den publiceras (Spearman +0,33), med intervall som kommer från prognosens egna träffar
- Interaktivt Streamlit-dashboard med tre vyer, en ordlista och en läsanvisning till varje diagram

**Varför?** Skattekraften varierar enormt: 2026 hade Danderyd 517 000 kr per invånare medan Högsby, den lägsta kommunen, hade 198 000 kr, alltså index 208 respektive 80. Frågan projektet svarar på är *vad som förklarar den skillnaden* — och, i andra hand, hur mycket av den som går att förutsäga. Svaret på det andra är: mindre än man skulle vilja, och projektet redovisar det öppet.

> **Om projektets historia och namnet.** En tidigare version hette *Kommunal Skattekraft Stress Monitor* och rangordnade kommuner efter en prognosticerad tillväxt för 2025 som aldrig hade testats mot utfall. När horisonten stängde och den testades blev korrelationen med faktisk tillväxt **+0,02**, och den förlorade mot att gissa riksgenomsnittet. Hela modellagret gjordes om under 2026-09, och namnet byttes när det som gjorde det till en "stress monitor" var borttaget. Se `docs/REMEDIATION_PLAN.md` och `docs/DEVIATIONS.md` §6.4.

## Modell

Projektet har **två modeller som svarar på olika frågor**, och de får inte läsas som en.

### 1. Tvärsnittsmodell: varför ligger kommunen där den ligger?

Det här är den modell dashboarden leder med. Samma fyra variabler, utan kommun-effekter, skattad på det senaste året där alla fyra finns:

```
Index_i = alpha + beta_1*Arbetsloshet_i + beta_2*Forsorjningskvot_i
          + beta_3*Befolkningstillvaxt_i + beta_4*Utbildningsandel_i + epsilon_i
```

R² = 0,69. Av de fyra variablerna går bara två att särskilja mellan kommuner:

| Variabel | Effekt per standardavvikelse | 95 % KI | Går att särskilja |
| --- | --- | --- | --- |
| Andel eftergymnasialt utbildade | +10,0 indexenheter | +6,4 till +13,7 | Ja |
| Öppen arbetslöshet | −2,7 indexenheter | −3,8 till −1,5 | Ja |
| Försörjningskvot | −0,6 indexenheter | −2,4 till +1,2 | Nej, omsluter noll |
| Befolkningstillväxt | −0,6 indexenheter | −2,0 till +0,9 | Nej, omsluter noll |

Försörjningskvot och befolkningstillväxt ingår som kontroller och redovisas som siffror, aldrig som staplar. Effekterna anges per standardavvikelse därför att råa koefficienter inte går att jämföra när variablerna mäts i olika enheter.

### 2. Panelmodell: vad hänger ihop med tillväxten inom en kommun över tid?

```
DeltaSkattekraft_it = alpha_i + gamma_t + beta_1*Arbetsloshet_it + beta_2*Forsorjningskvot_it
                      + beta_3*Befolkningstillvaxt_it + beta_4*Utbildningsandel_it + epsilon_it
```

Där *i* indexerar kommun (290), *t* indexerar år. Standardfel klustrade på kommunnivå, estimerad med `linearmodels.PanelOLS`. **Den primära specifikationen laggar högerledet ett år** — sambandet är genomgående starkast vid t−1, vilket följer av att skattekraften publiceras med eftersläpning.

Den här modellen **kan inte rangordna kommuner**: 98 % av variationen i relativ position ligger *mellan* kommuner, och det är precis den variation kommun-effekterna räknar bort. R²(within) = 0,036, vilket är lågt av konstruktion och inte ett tecken på att modellen är dålig.

### 3. Prognos

Femårig förflyttning i relativ position, inte ettårig tillväxt — den senare går inte att återskapa ur datan. Prognosen testas mot varje tillgängligt startår innan den publiceras och skrivs inte alls om den inte klarar sin egen gräns.

| Mått | Värde |
| --- | --- |
| Rangkorrelation (Spearman) | +0,33 |
| Medelfel (RMSE) | 2,11 indexenheter |
| Jämförelse: gissa genomsnittet | 2,35 |
| Jämförelse: anta att trenden fortsätter | 2,98 |
| Intervallets täckning | 81 % uppmätt mot 80 % nominellt |
| Efterhandstest | 7 startår, 2 030 kommunår |

Se [docs/METHODOLOGY.md](docs/METHODOLOGY.md) för fullständig metodbeskrivning inklusive robusthetsanalyser och begränsningar.

## Datakällor

Panelen är **ojämn i toppen**: källorna slutar olika år. Position och förflyttning behöver bara skattekraft och går därför till 2026, medan modellen stannar vid det senaste året där alla fyra variabler finns. Se `src/provenance.py`.

| Källa | Tabell-ID | Variabel | Period i panelen |
| --- | --- | --- | --- |
| SCB Statistikdatabasen | OE0101 | Skattekraft per invånare, samt SCB:s eget index | 2010–2026 |
| SCB Statistikdatabasen | BE0101 | Folkmängd (ålder, kön) | 2010–2025 |
| SCB Statistikdatabasen | UF0506 | Utbildningsnivå | 2010–2025 |
| SCB Statistikdatabasen | AA0003 | Öppen arbetslöshet (STATIV) | 2010–2024 |
| okfse/sweden-geojson | . | Kommungränser (GeoJSON) | 2024 |

> **Reproducerbarhet, en känd inskränkning.** SCB drog in hela arkivgruppen `AA0003X` under 2026. Öppen arbetslöshet för **2010–2021 går inte längre att hämta från SCB via någon väg** och läses i stället från en incheckad ögonblicksbild, `data/lookup/unemployment_2010_2021.csv`. 2022 och framåt hämtas fortfarande live. Se METHODOLOGY §8.1 och §12.6.

Se [docs/KRI_Dataset_Identification.md](docs/KRI_Dataset_Identification.md) för detaljerad datarevision med API-endpoints, query-parametrar och validering.

## Två index som inte får blandas

Projektet redovisar två mått på samma sak, och de har olika nämnare:

- **Vårt index (oviktat)** jämför med genomsnittet av de 290 kommunerna, där varje kommun väger lika mycket.
- **SCB:s index (viktat)** jämför med riksmedelvärdet, där varje invånare väger lika mycket, så folkrika kommuner drar upp det.

Vårt tal ligger därför systematiskt högre, i snitt ~8 indexenheter, för alla 290 kommuner. Rangkorrelationen mellan måtten är 0,999, så de rangordnar kommunerna nästan identiskt: skillnaden är en nivåförskjutning, inte en oenighet. **Ett tal från det ena måttet får aldrig jämföras med ett tal från det andra.** Se METHODOLOGY §7.13.

## Köra lokalt

### Förutsättningar

Python 3.11 och Git.

### Installation

```bash
git clone https://github.com/Maibra23/skattekraftspanelen.git
cd skattekraftspanelen
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

### Kör datapipelinen

Pipelinen hämtar data från SCB:s API, rensar, estimerar båda modellerna och genererar alla artefakter:

```bash
python pipeline.py
```

Kartan kräver kommungränser, som hämtas separat en gång:

```bash
python scripts/download_geojson.py
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
skattekraftspanelen/
    app.py                          # Startsida: modellöversikt, koefficienter, ordlista
    pipeline.py                     # Orkestrerar fetch, clean, estimate, decompose, forecast
    pages/
        01_Riksoversikt.py          # Nationell vy: karta, fördelning, prognos, rangordning
        02_Kommunjamforelse.py      # Kommundetalj: position över tid, dekomponering, grannar
    src/
        provenance.py               # Vilket år har alla variabler? Aldrig hårdkodat
        fetch/                      # SCB PxWeb API-klienter
            pxweb_client.py         # Generisk POST + chunking
            fetch_skattekraft.py    # OE0101
            fetch_population.py     # BE0101 (med per-års-chunkning)
            fetch_unemployment.py   # AA0003 (live 2022-, ögonblicksbild 2010-2021)
            fetch_education.py      # UF0506
        clean/                      # Harmonisering och härledda variabler
            harmonize_kommunkod.py  # Kommunkodsmapping till 2024 gränser
            generate_kommunkod_lookup.py
            compute_derived.py      # Försörjningskvot, tillväxttakt
            build_panel.py          # Bygger panelen + data_provenance.json
        model/                      # Ekonometri
            position.py             # Relativ position och förflyttning, utan modell
            estimate_cross.py       # Tvärsnittsmodellen (rangordningens källa)
            decompose_cross.py      # Dekomponering av läget
            estimate.py             # PanelOLS, samband inom kommuner över tid
            forecast.py             # Femårsprognos, grindad av sitt eget backtest
            backtest.py             # Rullande ursprung: testar innan publicering
            diagnostics.py          # Robusthets- och diagnostikmått
        ui/                         # Streamlit-komponenter
            css.py                  # Designsystem (färger, typografi, CSS)
            components.py           # KPI-kort, sidtitel, footer
            sidebar.py              # Gemensam sidebar med positionsfilter
            filters.py              # Kommunfilter
            chart_theme.py          # Plotly-tema
            choropleth.py           # Folium-karta med lagerväxling
            labels.py               # SWEDISH_LABELS + nummerformatering
    artifacts/                      # Förberäknade resultat (laddas av Streamlit)
        data_provenance.json        # Vilka år varje källa täcker
        position.parquet            # Relativ position och förflyttning, 2010-2026
        coefficients_cross.parquet  # Tvärsnittskoefficienter + identifieringsflagga
        decomposition_cross.parquet # Dekomponering av läget per kommun
        coefficients.parquet        # Panelmodellens koefficienter
        forecast.parquet            # Femårsprognos + intervall + backtest-resultat
        diagnostics.parquet         # Diagnostik och robusthet
        model_results.pkl           # Fitted PanelOLS-objekt
    data/
        raw/                        # Cachade SCB-svar (JSON)
        processed/panel.parquet     # Rensad panel, 290 kommuner x 17 år
        geo/kommuner.geojson        # Kommungränser
        lookup/                     # Kommunkodsmapping + arbetslöshetsögonblicksbild
    scripts/
        download_geojson.py         # Hämtar kommungränser
        freeze_unemployment_snapshot.py  # Fryser 2010-2021 efter SCB:s indragning
        screenshot_dashboard.py     # Skärmbilder för dokumentationen
    tests/                          # pytest-tester
    docs/
        METHODOLOGY.md              # Ekonometrisk metod
        KRI_Dataset_Identification.md  # Datakällrevision
        DEVIATIONS.md               # Avvikelser från ursprunglig plan
        REMEDIATION_PLAN.md         # Ombyggnaden av modellagret, 2026-09
        PRD.md                      # Ursprunglig produktkravspecifikation (historisk)
        TASKS.md                    # Ursprungliga implementeringsuppgifter (historisk)
    notebooks/
        01_exploratory.ipynb        # EDA
```

## Begränsningar

Modellen har flera kända begränsningar, dokumenterade i [docs/METHODOLOGY.md avsnitt 7](docs/METHODOLOGY.md):

- **Två av fyra variabler går inte att särskilja mellan kommuner.** Försörjningskvot och befolkningstillväxt redovisas som kontroller, inte som drivkrafter. Orsaken är skala, inte kollinearitet: försörjningskvotens spridning mellan kommuner är 0,116
- **Utbildningsandelen ligger nära en omskrivning.** Den korrelerar +0,81 med skattekraften och är inte en spak att dra i — se METHODOLOGY §7.15
- **Dekomponeringen träffar sämst i toppen.** För Danderyd är halva avvikelsen oförklarad; för Filipstad nästan ingen
- **Prognosen är blygsam.** Spearman +0,33 betyder att ordningen mellan kommuner till stor del förblir oförutsägbar. Intervallen är breda av samma skäl, och de redovisas
- **Ettårig tillväxt går inte att förutsäga** ur den här datan; årsavvikelsernas autokorrelation är ungefär −0,05
- **Panelen är ojämn i toppen.** Strukturvariablerna slutar tidigare än skattekraften, så modellen och positionen kan avse olika år. Varje kolumn i dashboarden bär sitt eget årtal
- Simultaneitet: fixed effects adresserar inte omvänd kausalitet
- Nominell skattekraft inkluderar inflation, inte realt justerad
- Två index med olika nämnare redovisas parallellt och får aldrig blandas — se METHODOLOGY §7.13
- Öppen arbetslöshet 2010–2021 är inte längre hämtbar från SCB och kommer från en incheckad ögonblicksbild — se METHODOLOGY §8.1

## Källor

- SCB Statistikdatabasen: [statistikdatabasen.scb.se](https://www.statistikdatabasen.scb.se/)
  - [OE0101 Skattekraft](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__OE__OE0101/SkatteKraft/)
  - [BE0101 Folkmängd](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__BE__BE0101__BE0101A/BefolkningNy/)
  - [AA0003 Öppen arbetslöshet](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__AA__AA0003/)
  - [UF0506 Utbildningsnivå](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__UF__UF0506__UF0506B/Utbildning/)
- Kommungränser: [okfse/sweden-geojson](https://github.com/okfse/sweden-geojson)

## Licens

MIT, se [LICENSE](LICENSE).
