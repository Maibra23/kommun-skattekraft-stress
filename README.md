# Skattekraftspanelen

## Skattekraft i svenska kommuner: läge, förflyttning och vad som förklarar dem

Det här projektet mäter var Sveriges 290 kommuner står i skattekraft mot riksgenomsnittet, åt vilket håll de rör sig, och vilka strukturella faktorer som förklarar skillnaderna. Det är i första hand **beskrivande**: modellen förklarar skillnader mellan kommuner, den förutsäger dem inte.

**Innehåll:** [Frågor projektet svarar på](#frågor-projektet-svarar-på) · [Så läser du siffrorna](#så-läser-du-siffrorna) · [Snabbstart](#snabbstart) · [Modell](#modell) · [Datakällor](#datakällor) · [Två index](#två-index-som-inte-får-blandas) · [Regenerera datan](#regenerera-datan) · [Vad testerna garanterar](#vad-testerna-garanterar) · [Begränsningar](#begränsningar) · [Felsökning](#felsökning)

**Varför?** Skattekraften varierar enormt: 2026 hade Danderyd 517 000 kr per invånare medan Högsby, den lägsta kommunen, hade 198 000 kr, alltså index 208 respektive 80.

---

## Frågor projektet svarar på

Varje fråga med vägen till svaret i dashboarden.

| Fråga | Var svaret finns |
| --- | --- |
| **Var ligger min kommun jämfört med riket?** | Kommunjämförelse → indexvärdet överst. 100 är genomsnittet av de 290 kommunerna. |
| **Har vi närmat oss eller halkat efter de senaste tio åren?** | Kommunjämförelse → Förflyttning 10 år. Ett minustal betyder att kommunen vuxit långsammare än riket, inte att skattekraften minskat. |
| **Varför ligger vi där vi ligger?** | Kommunjämförelse → *Vad förklarar kommunens läge?* Avståndet till riksgenomsnittet delas upp på utbildningsnivå och arbetslöshet, med den oförklarade delen öppet redovisad. |
| **Vilka kommuner liknar oss, och skiljer vi oss från dem?** | Kommunjämförelse → Jämförbara kommuner. Fem kommuner på samma indexnivå, valda enbart på läge. Ligger de på samma nivå av andra skäl är det en bra öppning för en jämförelse. |
| **Vilka kommuner i länet halkar efter?** | Riksöversikt → kartlagret *Förflyttning 5 år*, plus tabellen som går att sortera och ladda ned som CSV. |
| **Vad driver skillnaderna mellan kommuner i stort?** | Startsidan → *Variabler & koefficienter*. Av fyra strukturvariabler går bara två att särskilja: utbildningsnivå och öppen arbetslöshet. |
| **Hur säker är prognosen för min kommun?** | Riksöversikt → prognospanelen, som alltid visar sitt eget efterhandstest bredvid siffran. |

**Frågor projektet medvetet inte svarar på:** vilka kommuner som riskerar en ekonomisk kris, vad som händer med skattekraften nästa år, eller vad som skulle hända om en kommun ändrade något. Se [Begränsningar](#begränsningar).

---

## Så läser du siffrorna

Fyra begrepp räcker för att läsa hela dashboarden. Den fullständiga ordlistan finns i appen.

* **Index.** Kommunens skattekraft i procent av genomsnittet. **100 = genomsnittet.** Index 80 betyder 80 procent av genomsnittlig skattekraft, index 208 drygt dubbelt.
* **Indexenheter.** Enheten för skillnaden mellan två indextal. Från 80 till 84 är fyra indexenheter. Det är inte procent.
* **Förflyttning.** Hur mycket indexet ändrats under en period. **Ett minustal betyder inte att skattekraften minskat** — mellan 2021 och 2026 ökade skattekraften i kronor i samtliga 290 kommuner, men 173 av dem sjönk ändå i index, eftersom de övriga växte snabbare.
* **Konfidensintervall.** Spannet det sanna värdet rimligen ligger inom. **Omsluter intervallet noll går effekten inte att skilja från slumpen**, och variabeln redovisas som kontroll i stället för som drivkraft.

---

## Snabbstart

**Du behöver inte hämta något från SCB.** Panelen, artefakterna och kommungränserna ligger i repot, så dashboarden startar direkt.

```bash
git clone https://github.com/Maibra23/skattekraftspanelen.git
cd skattekraftspanelen
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
streamlit run app.py
```

Öppna `http://localhost:8501`. Kräver Python 3.11.

Dashboarden läser bara förberäknade filer i `artifacts/` och rör aldrig SCB:s API. Att regenerera datan är ett separat, frivilligt steg.

### Så hänger delarna ihop

```
SCB PxWeb API
  └─→ data/raw/*.json                    cachade svar, återanvänds i 7 dagar
      └─→ harmonisering + härledda variabler
          └─→ data/processed/panel.parquet          290 kommuner × 17 år
              └─→ src/model/       läge, tvärsnitt, panel, prognos
                  └─→ artifacts/*.parquet
                      └─→ Streamlit läser BARA artifacts/
```

Sista ledet är poängen: appen är helt frikopplad från SCB vid körning.

| Vill du... | Titta i |
| --- | --- |
| köra dashboarden | `app.py`, `pages/` |
| regenerera allt | `pipeline.py` |
| ändra ekonometrin | `src/model/` |
| lägga till en datakälla | `src/fetch/` + `src/clean/build_panel.py` |
| ändra utseendet | `src/ui/css.py`, `src/ui/chart_theme.py` |
| förstå vilka år som gäller | `src/provenance.py` |
| ändra text som visas | `src/ui/labels.py` (all svensk text bor här) |
| läsa resultaten utan Python | `artifacts/*.parquet` |

---

## Modell

Projektet har **två modeller som svarar på olika frågor**, och de får inte läsas som en.

### 1. Tvärsnittsmodell: varför ligger kommunen där den ligger?

Det här är den modell dashboarden leder med. Fyra strukturvariabler, utan kommun-effekter, skattad på det senaste året där alla fyra finns:

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

Standardfel klustrade på kommunnivå, estimerad med `linearmodels.PanelOLS`. **Den primära specifikationen laggar högerledet ett år.**

Den här modellen **kan inte rangordna kommuner**: 98 % av variationen i relativ position ligger *mellan* kommuner, och det är precis den variation kommun-effekterna räknar bort. R²(within) = 0,036, vilket är lågt av konstruktion.

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

Se [docs/METHODOLOGY.md](docs/METHODOLOGY.md) för fullständig metodbeskrivning, robusthetsanalyser och beslutslogg.

> **Om projektets historia och namnet.** En tidigare version hette *Kommunal Skattekraft Stress Monitor* och rangordnade kommuner efter en prognosticerad tillväxt för 2025 som aldrig hade testats mot utfall. När horisonten stängde och den testades blev korrelationen med faktisk tillväxt **+0,02**, och den förlorade mot att gissa riksgenomsnittet. Hela modellagret gjordes om under 2026-09, och namnet byttes när det som gjorde det till en "stress monitor" var borttaget. Se `docs/METHODOLOGY.md` §13.4.

---

## Datakällor

Panelen är **ojämn i toppen**: källorna slutar olika år. Position och förflyttning behöver bara skattekraft och går därför till 2026, medan modellen stannar vid det senaste året där alla fyra variabler finns.

| Källa | Tabell-ID | Variabel | Period i panelen |
| --- | --- | --- | --- |
| SCB Statistikdatabasen | OE0101 | Skattekraft per invånare, samt SCB:s eget index | 2010–2026 |
| SCB Statistikdatabasen | BE0101 | Folkmängd (ålder, kön) | 2010–2025 |
| SCB Statistikdatabasen | UF0506 | Utbildningsnivå | 2010–2025 |
| SCB Statistikdatabasen | AA0003 | Öppen arbetslöshet (STATIV) | 2010–2024 |
| okfse/sweden-geojson | . | Kommungränser (GeoJSON) | 2024 |

**Datan i repot hämtades 2026-09-07.** `artifacts/data_provenance.json` är källan till vilka år varje variabel täcker; läs den via `src/provenance.py` i stället för att anta `max(panel.year)`. Arbetslöshetsstatistiken är den bindande källan och släpar mest, så det är den som avgör vilket år modellen kan skattas på.

> **Reproducerbarhet, en känd inskränkning.** SCB drog in hela arkivgruppen `AA0003X` under 2026. Öppen arbetslöshet för **2010–2021 går inte längre att hämta från SCB via någon väg** och läses i stället från en incheckad ögonblicksbild, `data/lookup/unemployment_2010_2021.csv`. 2022 och framåt hämtas fortfarande live. Se METHODOLOGY §8.1, §12.6 och §13.1.

Se [docs/KRI_Dataset_Identification.md](docs/KRI_Dataset_Identification.md) för datarevision med API-endpoints, query-parametrar och validering.

---

## Två index som inte får blandas

Projektet redovisar två mått på samma sak, och de har olika nämnare:

* **Vårt index (oviktat)** jämför med genomsnittet av de 290 kommunerna, där varje kommun väger lika mycket.
* **SCB:s index (viktat)** jämför med riksmedelvärdet, där varje invånare väger lika mycket, så folkrika kommuner drar upp det.

Vårt tal ligger därför systematiskt högre, i snitt ~8 indexenheter, för alla 290 kommuner. Rangkorrelationen mellan måtten är 0,999, så de rangordnar kommunerna nästan identiskt: skillnaden är en nivåförskjutning, inte en oenighet. **Ett tal från det ena måttet får aldrig jämföras med ett tal från det andra.** Se METHODOLOGY §7.13.

---

## Regenerera datan

Behövs bara om du vill uppdatera med nyare SCB-data eller ändra modellen.

```bash
python pipeline.py                  # använder cachade svar där de finns
python pipeline.py --force-refresh  # hämtar om allt från SCB
```

**Vad du kan förvänta dig.** Ett fullt hämtningsvarv gör i storleksordningen 40 anrop till SCB:s öppna API — folkmängd och utbildning hämtas ett år i taget för att hålla sig under SCB:s cellgräns. Svaren cachas i `data/raw/` och återanvänds i **sju dagar**, så en omkörning utan `--force-refresh` hoppar över nätverket helt. Ett fullt varv kräver internet och tar några minuter, mest väntan på SCB.

Svarar SCB med 403 eller 429 är det hastighetsbegränsning: vänta och kör om. Cachen behålls, så du börjar inte om från noll. Varje steg loggas till `data/raw/pipeline.log`.

Kartan behöver kommungränser, som redan ligger i repot men kan hämtas om:

```bash
python scripts/download_geojson.py
```

**Prognosen har en grind.** Klarar den inte sitt eget efterhandstest skrivs `artifacts/forecast.parquet` inte alls, och dashboarden renderar utan prognospanel. Det är ett avsiktligt utfall, inte ett fel.

---

## Vad testerna garanterar

```bash
pytest
```

336 testfunktioner, 430 fall. Två av dem bär mer förtroende än antalet:

* **`tests/test_copy_matches_artifacts.py`** kontrollerar att varje siffra som står i dashboardens text fortfarande är siffran i artefakterna. Skrivs modellen om utan att texten uppdateras faller sviten. Givet projektets historia är det den viktigaste garantin här: texten kan inte glida ifrån modellen.
* **`tests/test_pages_render.py`** kör alla tre sidorna på riktigt mot de incheckade artefakterna. En sida som annars skulle krascha för en användare faller i stället här.

---

## Begränsningar

Dokumenterade i [docs/METHODOLOGY.md](docs/METHODOLOGY.md) avsnitt 7.

**Använd inte det här för** budgetprognoser för en enskild kommun, för att rangordna kommuner efter risk för ekonomisk kris, eller för kausala policyslutsatser. Modellen beskriver samband, inte orsaker, och prognosen är avsiktligt trubbig.

* **Två av fyra variabler går inte att särskilja mellan kommuner.** Orsaken är skala, inte kollinearitet: försörjningskvotens spridning mellan kommuner är 0,116
* **Utbildningsandelen ligger nära en omskrivning.** Den korrelerar +0,81 med skattekraften och är inte en spak att dra i — se METHODOLOGY §7.15
* **Dekomponeringen träffar sämst i toppen.** För Danderyd är halva avvikelsen oförklarad; för Filipstad nästan ingen
* **Prognosen är blygsam.** Spearman +0,33 betyder att ordningen mellan kommuner till stor del förblir oförutsägbar
* **Ettårig tillväxt går inte att förutsäga** ur den här datan; årsavvikelsernas autokorrelation är ungefär −0,05
* **Panelen är ojämn i toppen.** Modellen och positionen kan avse olika år; varje kolumn i dashboarden bär sitt eget årtal
* Simultaneitet: fixed effects adresserar inte omvänd kausalitet
* Nominell skattekraft inkluderar inflation, inte realt justerad
* Öppen arbetslöshet 2010–2021 kommer från en incheckad ögonblicksbild

---

## Felsökning

| Symptom | Åtgärd |
| --- | --- |
| Kartan är tom | Kör `python scripts/download_geojson.py` |
| SCB svarar 403 eller 429 | Hastighetsbegränsning. Vänta och kör om; cachen behålls |
| `linearmodels` bygger inte | Kräver Python 3.11; kontrollera med `python --version` |
| Port 8501 upptagen | `streamlit run app.py --server.port 8502` |
| Prognospanelen saknas | Förväntat om prognosen inte klarade sin grind. Se `data/raw/pipeline.log` |

---

## Källor och licens

* SCB Statistikdatabasen: [statistikdatabasen.scb.se](https://www.statistikdatabasen.scb.se/)
  * [OE0101 Skattekraft](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__OE__OE0101/SkatteKraft/)
  * [BE0101 Folkmängd](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__BE__BE0101__BE0101A/BefolkningNy/)
  * [AA0003 Öppen arbetslöshet](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__AA__AA0003/)
  * [UF0506 Utbildningsnivå](https://www.statistikdatabasen.scb.se/pxweb/sv/ssd/START__UF__UF0506__UF0506B/Utbildning/)
* Kommungränser: [okfse/sweden-geojson](https://github.com/okfse/sweden-geojson)

**Licens:** MIT för koden, se [LICENSE](LICENSE). **Licensen omfattar inte SCB:s data.** Statistiken i `data/` och `artifacts/` publiceras av SCB under deras egna användarvillkor; ange SCB som källa vid vidareanvändning.
