"""Authoritative Swedish user-facing label dictionary and number formatters.

SWEDISH_LABELS is the single source of truth for every string visible to
dashboard users.  Code that hardcodes Swedish text in component logic is
rejected in code review, always import from here.

Also provides number formatting helpers:
  format_sek(value)              - integer SEK with narrow no-break space thousands separator
  format_pct(value, decimals)    - percentage with comma decimal and % suffix
  format_signed_pct(value, decimals) - signed percentage with explicit + or - sign
  format_index_points(value)     - signed movement in index points

and the position bands that replaced the risk-class quintiles at the T1.2
cutover: POSITION_BANDS and classify_position.
"""

from typing import NamedTuple

# ---------------------------------------------------------------------------
# Swedish labels (PRD §9, verbatim)
# ---------------------------------------------------------------------------

SWEDISH_LABELS = {
    # Brand and navigation
    "brand_mark": "KSS",
    "brand_title": "Skattekraft Stress",
    "brand_sub": "Kommunal panelmodell",
    "nav_landing": "Startsida",
    "nav_national": "Riksöversikt",
    "nav_kommun": "Kommunjämförelse",

    # Page eyebrows and titles
    "eyebrow_landing": "KOMMUNAL SKATTEKRAFT STRESS MONITOR",
    "eyebrow_national": "NATIONELL VY",
    "eyebrow_kommun": "KOMMUNDETALJ",
    "title_landing": "Skattekraftens utveckling i Sveriges 290 kommuner",
    "title_national": "Riksöversikt",
    "title_kommun": "Kommunjämförelse",

    # Sidebar controls
    "label_year": "ÅR",
    "label_risk_filter": "RISKKLASS",
    "label_position_filter": "POSITION MOT RIKET",

    # Position bands (replaced the risk-class quintiles at the T1.2 cutover)
    "band_low": "Under 90",
    "band_mid": "90–110",
    "band_high": "Över 110",
    "band_legend_note": (
        "Kommunens skattekraft i procent av det oviktade riksgenomsnittet."
    ),
    "label_kommun_select": "VÄLJ KOMMUN",

    # Risk classes
    "risk_low": "Låg",
    "risk_medium": "Medel",
    "risk_high": "Hög",

    # KPI labels (national)
    "kpi_median_prognosis": "Median prognos 2025",
    "kpi_high_risk_count": "Kommuner i hög risk",
    "kpi_largest_decline": "Största nedgång (prognos)",
    "kpi_model_r2": "Modellens R2",

    # KPI labels (kommun)
    "kpi_skattekraft_2024": "Skattekraft 2024",
    "kpi_growth_2024": "Tillväxt 2024",
    "kpi_prognosis_2025": "Prognos 2025",
    "kpi_vulnerability_rank": "Sårbarhetsrang",

    # Chart axes and titles
    "axis_year": "År",
    "axis_skattekraft": "Skattekraft per invånare (kr)",
    "axis_growth_pct": "Tillväxt (%)",
    "axis_kommuner_count": "Antal kommuner",
    "chart_historical": "Historisk skattekraft",
    "chart_decomposition": "Strukturell dekomponering",
    "chart_distribution": "Fördelning av position",
    "chart_distribution_of": "Fördelning: {quantity}",

    # Table headers
    "th_rank": "Rang",
    "th_kommun": "Kommun",
    "th_lan": "Län",
    "th_prognosis": "Prognos 2025 (%)",
    "th_risk_class": "Riskklass",
    "th_skattekraft": "Skattekraft (kr)",
    "th_unemployment": "Arbetslöshet (%)",
    "th_dependency": "Försörjningskvot",
    "th_pop_growth": "Befolkning (%)",
    "th_education": "Utbildning (%)",

    # Variable display names
    "var_unemployment": "Öppen arbetslöshet",
    "var_dependency": "Försörjningskvot",
    "var_population": "Befolkningstillväxt",
    "var_education": "Andel eftergymnasialt utbildade",
    "var_residual": "Residual (kommunspecifika faktorer)",

    # Decomposition contributions
    "contrib_unemployment": "Bidrag: arbetslöshet",
    "contrib_dependency": "Bidrag: försörjningskvot",
    "contrib_population": "Bidrag: befolkning",
    "contrib_education": "Bidrag: utbildning",
    "contrib_residual": "Bidrag: residual",

    # Map
    "map_title": "Geografisk fördelning",
    "map_subtitle": "Välj vad kartan ska visa",
    "map_legend_caption": "Sårbarhetsindex (Lägre = bättre, Högre = sämre)",
    "map_color_scale_note": "Färgskala: Grön = låg sårbarhet, Gul = medel, Röd = hög sårbarhet",

    # Buttons and actions
    "btn_download_csv": "Ladda ned som CSV",
    "btn_show_method": "Visa metod",

    # States
    "state_loading": "Laddar data...",
    "state_no_data": "Inga data tillgängliga för den valda perioden",
    "state_error_io": "Kunde inte hämta data. Försök igen senare.",
    "state_error_compute": "Beräkningsfel. Se metodologisidan för detaljer.",

    # Footer
    "footer_source_label": "KÄLLA",
    "footer_source": "SCB (OE0101, BE0101, AA0003, UF0506)",
    "footer_method_link": "Metodologi",

    # Methodology callouts
    "method_model_name": "Tvärsnittsmodell + panelmodell för samband över tid",
    "method_period": "Period: 2010 till 2026 (modellen skattas på 2010–2024)",
    "method_units": (
        "290 kommuner, 17 år, 4 930 observationer. Skattekraft finns till och "
        "med 2026, befolkning och utbildning till 2025 och arbetslöshet till "
        "2024 — modellen använder de år där alla variabler finns."
    ),

    # Landing page
    "landing_lead": (
        "Var står din kommun mot riksgenomsnittet, och åt vilket håll rör den "
        "sig? Skillnaderna mellan kommuner är stora, trögrörliga och mätbara — "
        "modellen förklarar dem, den förutsäger dem inte."
    ),
    "landing_stat_kommuner": "KOMMUNER",
    "landing_stat_panel": "ÅR PANEL",
    "landing_stat_vars": "STRUKTURVARIABLER",
    "landing_stat_fe": "FIXED EFFECTS",
    "landing_stat_identified": "IDENTIFIERADE DRIVKRAFTER",
    "landing_model_title": "Modellöversikt",
    "landing_vars_title": "Variabler & koefficienter",
    "landing_pipeline_title": "Pipelinesteg",
    "landing_nav_title": "Utforska dashboarden",
    "landing_sources_title": "Källor & metod",

    # Landing page — section explanations (collapsible)
    "landing_model_explanation": (
        "Fyra strukturvariabler matas in i modellen, men de bär inte lika "
        "mycket. Mellan kommuner går bara två av dem att särskilja: "
        "utbildningsnivå, som är den klart starkaste, och öppen arbetslöshet. "
        "Försörjningskvot och befolkningstillväxt ingår som kontroller — deras "
        "effekt går inte att skilja från noll när kommuner jämförs med "
        "varandra. Resultatet är en förklaring av kommunens läge, inte en "
        "prognos för nästa år."
    ),
    "landing_model_example": (
        "Filipstad ligger 16,7 indexenheter under riksgenomsnittet. Modellen "
        "hänför 12,9 av dem till utbildningsnivån och 4,0 till arbetslösheten, "
        "och lämnar 0,1 oförklarat. Danderyd ligger 99,3 enheter över — där "
        "förklarar samma modell knappt hälften. Sambandet är starkast i mitten "
        "av fördelningen och svagast i toppen."
    ),
    "landing_model_expander": "Hur läser jag diagrammet?",
    "landing_vars_explanation": (
        "Staplarna visar hur mycket kommunens indexläge skiljer sig när en "
        "variabel ändras med en standardavvikelse. Strecken är 95-procentiga "
        "konfidensintervall: omsluter strecket noll går effekten inte att "
        "skilja från slumpen, och variabeln redovisas som kontroll."
    ),
    "landing_vars_example": (
        "Exempel: utbildningsnivån ligger på +10,0 indexenheter. En kommun vars "
        "andel eftergymnasialt utbildade är en standardavvikelse högre än en "
        "annans ligger alltså ungefär 10 indexenheter högre i skattekraft. "
        "Det är ett starkt och robust samband — men det ligger nära en "
        "omskrivning av samma sak, inte en knapp att trycka på."
    ),
    "landing_vars_expander": "Hur tolkar jag koefficienterna?",
    "landing_nav_explanation": (
        "Dashboarden har två huvudvyer. Välj den som passar din frågeställning."
    ),
    "landing_nav_national_desc": (
        "Karta och tabell över alla 290 kommuners position mot riket och deras "
        "förflyttning över fem och tio år."
    ),
    "landing_nav_kommun_desc": (
        "Detaljerad vy med historisk trend, strukturell "
        "dekomponering och jämförelse med liknande kommuner."
    ),
    "landing_step_1": "Datainsamling",
    "landing_step_2": "Rensning",
    "landing_step_3": "Estimering",
    "landing_step_4": "Förklaring",

    # Riksöversikt
    "chart_ranking_title": "Rangordning",

    # Kommunjämförelse
    "chart_national_avg": "Riksgenomsnitt",
    "chart_peers_title": "Jämförbara kommuner",
    "subtitle_national": "Alla 290 kommuners läge mot riksgenomsnittet och deras förflyttning",
    "subtitle_kommun": "Strukturell dekomponering för vald kommun",

    # Choropleth tooltip
    "tooltip_population": "Befolkning",

    # Coefficient chart axis
    "axis_coefficient": "Koefficient (beta)",

    # SVG diagram labels (landing page)
    "svg_regression_model": "Regressionsmodell",
    "svg_panel_ols": "PanelOLS, 2-way FE",
    "svg_prognosis": "Prognos 2025",
    "svg_ranking": "Rangordning",
    "svg_decomposition": "Dekomponering av läget",
    # The flow diagram must not draw four equal drivers: two of the four are
    # not separately identified between kommuner (T1.2).
    "svg_identified_heading": "GÅR ATT SÄRSKILJA",
    "svg_controls_heading": "KONTROLLER — EFFEKT EJ SKILD FRÅN NOLL",
    "svg_cross_section": "Tvärsnittsmodell",
    "svg_position": "Kommunens läge mot riket",

    # Contextual summary (Riksöversikt)
    "national_summary_template": (
        "Mediankommunen förväntas se {median} nominell tillväxt under 2025. "
        "{count} kommuner klassas som högrisk, med störst förväntad nedgång "
        "i {kommun} ({decline})."
    ),

    # Decomposition explanation (Kommunjämförelse)
    "decomp_explanation": (
        "Staplarna visar hur varje strukturvariabel bidrar till kommunens "
        "avvikelse från riksgenomsnittet. Positiva staplar (gröna) drar "
        "uppåt, negativa (röda) drar nedåt."
    ),

    # ---- Position and drift: the descriptive spine (T1.1, rendered by T1.2) ----
    "position_index": "Index mot riksgenomsnittet",
    "position_index_short": "Index",
    "position_scb_index": "SCB:s index",
    "drift_5y": "Förflyttning 5 år",
    "drift_10y": "Förflyttning 10 år",
    "unit_index_points": "indexenheter",

    # Choropleth layer toggle
    "map_layer_label": "Vad kartan visar",
    "map_layer_position": "Nuvarande position",
    "map_layer_drift": "Förflyttning 5 år",
    "map_layer_vulnerability": "Sårbarhetsindex (avvecklas)",
    "map_legend_position": "Index mot riket · mörkare = högre",
    "map_legend_drift": "Indexenheter, 5 år · orange = tappat mark",
    "map_legend_position_full": (
        "Kommunens skattekraft i procent av det oviktade riksgenomsnittet. "
        "Mörkare blå = högre. Skalan är beskuren vid 80 och 130, eftersom "
        "mediankommunen ligger på 97 och den högsta på 208 — en obeskuren "
        "skala skulle ge nio kommuner av tio samma färg."
    ),
    "map_legend_drift_full": (
        "Förändring i indexenheter de senaste fem åren. Orange = kommunen har "
        "tappat mark mot riket, blått = vunnit mark. Skalan är centrerad på "
        "noll och beskuren vid ±4 indexenheter."
    ),

    # The two index measures have different denominators (METHODOLOGY §7.13)
    "index_compare_title": "Två mått på samma sak",
    "index_compare_explanation": (
        "Vårt index delar kommunens skattekraft med det <strong>oviktade</strong> "
        "genomsnittet av de 290 kommunerna. SCB:s publicerade index delar med "
        "<strong>riksmedelvärdet</strong>, som är befolkningsviktat och därför "
        "högre — "
        "storstadskommuner väger tyngre i det. Därför ligger vårt tal alltid "
        "över SCB:s, i genomsnitt med 7,0 indexenheter och som mest med 17,6. "
        "Ingen av dem är fel; de svarar på olika frågor. Jämför aldrig ett "
        "tal från det ena måttet med ett tal från det andra."
    ),
    "index_compare_ours": "Vårt index (oviktat)",
    "index_compare_scb": "SCB:s index (viktat)",

    # Riksöversikt KPI row after the cutover
    "kpi_index_spread": "Högsta / lägsta index",
    "kpi_largest_fall_10y": "Största fall, 10 år",
    "kpi_largest_rise_10y": "Största ökning, 10 år",
    "kpi_cross_r2": "Modellens förklaringsgrad",
    "kpi_cross_r2_tooltip": (
        "Andel av skillnaderna i skattekraft mellan kommuner som de fyra "
        "strukturvariablerna förklarar, i tvärsnittet för {year}. Det är ett "
        "annat mått än panelmodellens R² inom kommuner, som är lågt av "
        "konstruktion och redovisas separat längre ner."
    ),
    "national_position_summary": (
        "Skillnaderna mellan kommuner är stora och trögrörliga. {high_name} "
        "ligger på index {high:.0f} och {low_name} på {low:.0f}. Rangordningen "
        "är i praktiken låst: sambandet mellan ett års position och nästa års "
        "är 0,99, och över tio år 0,93. Det som rör sig gör det långsamt — "
        "därför visas förflyttning över fem och tio år, inte över ett."
    ),

    # Kommun page lead
    "kommun_position_lead": (
        "{kommun} ligger på index <strong>{position}</strong> av "
        "riksgenomsnittet, en förflyttning på <strong>{drift} "
        "indexenheter</strong> sedan {since}."
    ),
    "kommun_position_lead_no_drift": (
        "{kommun} ligger på index <strong>{position}</strong> av "
        "riksgenomsnittet."
    ),
    "chart_position_history": "Position över tid",
    "axis_index": "Index (riket = 100)",

    # Decomposition of the position gap (T2.2)
    "decomp_position_title": "Vad förklarar kommunens läge?",
    "decomp_position_explanation": (
        "Staplarna visar hur långt kommunen ligger från riksgenomsnittet i "
        "indexenheter, uppdelat på de variabler som går att särskilja mellan "
        "kommuner. Resten är oförklarad."
    ),
    "decomp_controls_title": "Ingår i modellen, går inte att särskilja",
    "decomp_controls_explanation": (
        "Försörjningskvot och befolkningstillväxt ingår i modellen som "
        "kontrollvariabler, men mellan kommuner går deras effekt inte att "
        "skilja från noll: konfidensintervallen omsluter noll i varje år "
        "2021–{year}. De visas därför som siffror, inte som staplar — en "
        "stapel skulle påstå en säkerhet som inte finns."
    ),
    "decomp_residual_note": (
        "Modellen är linjär och träffar sämst i toppen av fördelningen. För de "
        "allra rikaste kommunerna är en stor del av avvikelsen oförklarad."
    ),

    # Coefficients shown on a comparable scale (T2.1)
    "landing_vars_scale_note": (
        "Effekterna visas per standardavvikelse, inte per enhet. Råa "
        "koefficienter går inte att jämföra med varandra när variablerna mäts "
        "i olika enheter — en försörjningskvot rör sig mellan 0,5 och 1,2 "
        "medan utbildningsandelen rör sig mellan 6 och 61 procent."
    ),
    "axis_beta_sd": "Effekt i indexenheter per standardavvikelse",
    "vars_table_effect_sd": "Effekt per standardavvikelse",
    "vars_table_ci": "Effekt per standardavvikelse, 95 % KI",
    "decomp_contribution_col": "Bidrag för kommunen (indexenheter)",
    "vars_table_identified": "Går att särskilja",
    "identified_yes": "Ja",
    "identified_no": "Nej — intervallet omsluter noll",

    # Data vintage.  The panel is ragged: position runs to the last skattekraft
    # year, the structural variables stop where unemployment stops.  Numbers of
    # different vintages sit side by side on these pages, so both the strip and
    # the column headers name their year.
    "vintage_note": (
        "Position och förflyttning till {position_year} · strukturvariabler "
        "till {analysis_year} (arbetslöshet är den bindande källan)"
    ),
    "col_with_year": "{label} ({year})",

    # Shown when the retired score's map layer is selected.
    "vulnerability_retired_title": "Det här måttet är på väg bort",
    "vulnerability_retired_text": (
        "Sårbarhetsindexet bygger på en tillväxtprognos för 2025 som nu går "
        "att pröva mot utfallet. Den träffade inte: korrelationen med faktisk "
        "tillväxt blev +0,02 och medelfelet 1,51 procentenheter, mot 0,97 för "
        "att bara gissa riksgenomsnittet. Riskklasserna skilde sig inte heller "
        "åt i utfallet — låg 4,74 %, medel 4,52 %, hög 4,68 %. Lagret ligger "
        "kvar tills det tas bort helt; använd position och förflyttning i "
        "stället."
    ),

    # The two index measures, shown rather than only described.
    "index_scatter_title": "Vårt index mot SCB:s, alla 290 kommuner",
    "index_scatter_note": (
        "Varje punkt är en kommun. Den streckade linjen är där måtten skulle "
        "sammanfalla. Alla 290 ligger ovanför den — skillnaden är systematisk "
        "och beror på nämnaren, inte på att någon av dem är fel."
    ),
    "index_diff": "Skillnad",
    "axis_our_index": "Vårt index (oviktat)",
    "axis_scb_index": "SCB:s index (viktat)",

    # The forecast and its track record (T3.2, T3.3).  The panel is permanent
    # and needs no interaction: a dashboard that shows its own hit rate is
    # worth more than one showing an untested number, and it is the standing
    # defence against this project repeating its own history.
    "forecast_title": "Prognos: förflyttning {horizon} år framåt",
    "forecast_lead": (
        "Modellen skattar hur långt en kommun rör sig mot riksgenomsnittet de "
        "kommande {horizon} åren, utifrån strukturvariablerna i dag. Intervallet "
        "är {coverage} % och kommer från prognosens egna träffar i "
        "efterhandstestet — inte från regressionens nominella standardfel, som "
        "beskriver osäkerheten om linjen snarare än om en enskild kommun."
    ),
    "forecast_col": "Prognos {horizon} år",
    "forecast_interval_col": "Intervall",
    "backtest_title": "Prognosens träffsäkerhet",
    "backtest_lead": (
        "Prognosen är testad mot utfall som den inte fått se: modellen skattas "
        "om vid varje startår och jämförs med vad som faktiskt hände "
        "{horizon} år senare. {origins} startår, {n} kommunår."
    ),
    "backtest_spearman": "Rangkorrelation (Spearman)",
    "backtest_rmse": "Medelfel (RMSE)",
    "backtest_naive": "Jämförelse: gissa genomsnittet",
    "backtest_persistence": "Jämförelse: anta att trenden fortsätter",
    "backtest_coverage": "Intervallets träffsäkerhet",
    "backtest_verdict_better": (
        "Modellen slår båda jämförelserna. Den är ändå blygsam: en "
        "rangkorrelation på {rho} betyder att ordningen mellan kommuner till "
        "stor del förblir oförutsägbar, och intervallen är breda av samma skäl."
    ),
    "backtest_caveat": (
        "Den tidigare prognosen i det här projektet redovisades aldrig mot "
        "utfall. När den till slut testades hamnade korrelationen på 0,02 och "
        "den förlorade mot att gissa riksgenomsnittet. Därför står den här "
        "rutan kvar permanent: om prognosen försämras syns det här."
    ),

    # Within-time inference panel (REMEDIATION_PLAN.md T2.4).
    # The two-way FE model answers a different question than the ranking and
    # must be shown under its own heading, physically separated from it.
    # Added ahead of the UI cutover; no page renders these yet (T1.2 does).
    "within_section_title": "Samband inom kommuner över tid",
    "within_section_lead": (
        "Panelmodellen med kommun- och årseffekter svarar på en annan fråga än "
        "jämförelsen mellan kommuner: när förhållandena i en enskild kommun "
        "förändras över tid, hur hänger det samman med kommunens "
        "skattekraftstillväxt? Kommunens egna, tidsoberoende egenskaper och "
        "alla nationella konjunktursvängningar är borträknade."
    ),
    "within_section_spec": (
        "Primär specifikation: variablerna mäts året före tillväxten (t−1). "
        "Sambandet är genomgående starkare med ett års fördröjning — för "
        "arbetslöshet −0,50 mot −0,18 samtidigt — vilket följer av att "
        "skattekraften publiceras med två års eftersläpning. Den samtida "
        "specifikationen redovisas som robusthetskontroll."
    ),
    "within_section_caveat": (
        "Koefficienterna jämför varje kommun med sig själv över tid. De kan "
        "inte rangordna kommuner och förklarar inte varför en kommun ligger "
        "högre än en annan — 98 % av skillnaderna i skattekraft finns mellan "
        "kommuner, och just den variationen räknar den här modellen bort."
    ),

    # R² KPI tooltip
    "kpi_r2_tooltip": (
        "R2(within) mäter hur mycket av variationen inom kommuner "
        "som förklaras av strukturvariablerna, efter att kommun- och "
        "årseffekter absorberats. Lågt värde är förväntat."
    ),

    # Footer data freshness
    "footer_updated": "Senast uppdaterad",

    # Choropleth tooltip label for vulnerability score
    "tooltip_vulnerability_score": "Sårbarhetsindex",

    # Risk boundary labels (histogram)
    "risk_boundary_high_medium": "Hög / Medel",
    "risk_boundary_medium_low": "Medel / Låg",

    # Units (use these everywhere)
    "unit_sek": "kr",
    "unit_pct": "%",
    "unit_per_capita": "per invånare",

    # Concept explanation (landing page, collapsible)
    "concept_skattekraft_expander": "Vad är Skattekraft och varför är det viktigt?",
    "concept_skattekraft_text": (
        "**Skattekraft** (beskattningsbar förvärvsinkomst per invånare) är det "
        "centrala måttet på en kommuns skattemässiga kapacitet. Det anger hur "
        "mycket inkomstskatt kommunen kan ta in per person, och avgör i praktiken "
        "vilka tjänster kommunen har råd att erbjuda sina invånare.\n\n"
        "Skillnaderna är enorma: 2024 hade Danderyd ca 481 000 kr per invånare "
        "medan flera Norrlandskommuner låg under 180 000 kr. Det innebär att "
        "vissa kommuner har mer än dubbelt så stor skattebas per invånare.\n\n"
        "Sverige har ett utjämningssystem som delvis kompenserar för dessa "
        "skillnader, men den underliggande skattekraften förblir en avgörande "
        "faktor för kommunens ekonomiska handlingsutrymme.\n\n"
        "### Varför är det viktigt att följa skattekraftens utveckling?\n\n"
        "**Scenario 1: Kreditanalytiker på en bank**\n"
        "Du bedömer en kommuns kreditvärdighet inför ett obligationslån. "
        "Dashboarden visar att kommunen har sjunkande skattekraftstillväxt och "
        "hög försörjningskvot. Det signalerar ökad risk och påverkar din "
        "kreditbedömning.\n\n"
        "**Scenario 2: Kommunal controller**\n"
        "Du planerar nästa års budget. Modellen visar att er kommun rankas "
        "som 45:e mest sårbara av 290. Dekomponeringen avslöjar att det "
        "främst beror på stigande arbetslöshet, inte demografi. Du kan rikta "
        "insatser mot arbetsmarknadsåtgärder.\n\n"
        "**Scenario 3: Regional beslutsfattare (SKR/länsstyrelse)**\n"
        "Du behöver identifiera vilka kommuner i ditt län som riskerar "
        "ekonomisk stress de kommande åren. Riksöversikten visar kartan och "
        "rangordningen direkt, utan att du behöver samla in data manuellt.\n\n"
        "**Scenario 4: Forskare eller student**\n"
        "Du studerar kommunal ekonomi och vill förstå vilka strukturella "
        "faktorer som driver skillnaderna. Dekomponeringen bryter ner exakt "
        "hur mycket arbetslöshet, demografi, befolkning och utbildning "
        "bidrar för varje kommun."
    ),

    # Usage guide (landing page, collapsible)
    "guide_expander": "Hur använder jag dashboarden?",
    "guide_text": (
        "### Sidorna\n\n"
        "Dashboarden har tre sidor som du navigerar via sidopanelen till vänster:\n\n"
        "1. **Startsida** (denna sida): Ger en översikt av modellen, variablerna "
        "och pipelinestegen.\n"
        "2. **Riksöversikt**: Visar alla 290 kommuner på en karta och i en "
        "rangordningstabell. Här ser du vilka kommuner som har starkast respektive "
        "svagast prognosticerad skattekraftstillväxt.\n"
        "3. **Kommunjämförelse**: Välj en specifik kommun och se dess historiska "
        "skattekraftsutveckling, strukturella dekomponering och jämförbara "
        "kommuner.\n\n"
        "### Riskklasser i sidopanelen\n\n"
        "Filtret **Riskklass** i sidopanelen låter dig filtrera kommuner efter "
        "deras prognosticerade sårbarhet:\n\n"
        "- **Hög**: De 20 % av kommunerna (58 st) med svagast prognosticerad "
        "tillväxt. Dessa kommuner har den mest ogynnsamma kombinationen av "
        "strukturella faktorer.\n"
        "- **Medel**: De mellersta 60 % (174 kommuner). Varken tydligt utsatta "
        "eller tydligt gynnade.\n"
        "- **Låg**: De 20 % (58 st) med starkast prognosticerad tillväxt. "
        "Dessa kommuner har de mest gynnsamma strukturella förutsättningarna.\n\n"
        "Du kan välja en eller flera riskklasser samtidigt. Valet påverkar vilka "
        "kommuner som visas i tabeller och histogram.\n\n"
        "### Hur läser jag resultaten?\n\n"
        "- **Sårbarhetsrang**: Rang 1 = mest sårbar kommun, rang 290 = minst "
        "sårbar. Baserat på modellens prognosticerade tillväxt för 2025.\n"
        "- **Prognos 2025 (%)**: Modellens beräknade nominella "
        "skattekraftstillväxt. Inkluderar inflation.\n"
        "- **Dekomponering**: Visar hur mycket varje faktor (arbetslöshet, "
        "försörjningskvot, befolkning, utbildning) bidrar till skillnaden "
        "mot riksgenomsnittet."
    ),

    # Variabler & vikter table header
    "vars_table_header": "Koefficientvärden",
    "vars_table_variable": "Variabel",
    "vars_table_coef": "Koefficient",
    "vars_table_sig": "Signifikans",
    "vars_table_interpretation": "Tolkning",

    # Graph explanations (collapsible, standardized)
    "explain_coef_chart_expander": "Hur läser jag detta diagram?",
    "explain_coef_chart_text": (
        "Staplarna visar regressionskoefficienten (beta) för varje variabel. "
        "Koefficientens storlek anger hur starkt variabeln samvarierar med "
        "skattekraftstillväxten. Observera att försörjningskvoten mäts i en "
        "annan skala (kvot, inte procent) och har därför ett större absolutvärde.\n\n"
        "**Exempel**: Försörjningskvotens koefficient på ca -3,75 innebär att om "
        "en kommuns försörjningskvot ökar med 0,1 (t.ex. från 0,70 till 0,80), "
        "förväntas skattekraftstillväxten minska med ca 0,38 procentenheter. "
        "Stjärnorna anger statistisk signifikans: *** = p < 0,001, ** = p < 0,01, "
        "* = p < 0,05."
    ),

    "explain_choropleth_expander": "Hur läser jag kartan?",
    "explain_choropleth_text": (
        "Kartan visar alla 290 kommuner färgkodade efter sårbarhetsindex. "
        "Gröna kommuner har låg sårbarhet (stark prognosticerad tillväxt), "
        "gula har medelsårbarhet, och röda har hög sårbarhet (svag tillväxt).\n\n"
        "**Exempel**: Om du ser att kommunerna i norra Norrland lyser rött "
        "medan Stockholmsregionen är grön, indikerar det att norrlandskommunerna "
        "har en mer ogynnsam kombination av arbetslöshet, försörjningskvot, "
        "befolkningsutveckling och utbildningsnivå. Håll muspekaren över en "
        "kommun för att se detaljerad information."
    ),

    "explain_histogram_expander": "Hur läser jag fördelningen?",
    "explain_histogram_text": (
        "Histogrammet visar hur de 290 kommunernas prognosticerade "
        "skattekraftstillväxt fördelar sig. Varje stapel representerar ett "
        "intervall av tillväxtvärden, och höjden anger hur många kommuner "
        "som hamnar i det intervallet.\n\n"
        "De streckade linjerna visar gränserna mellan riskklasserna. "
        "Kommuner till vänster om den röda linjen klassas som Hög risk, "
        "kommuner till höger om den gröna som Låg risk.\n\n"
        "**Exempel**: Om de flesta kommuner samlas kring 3 % tillväxt men "
        "du ser en svans åt vänster (ned mot 1 %), representerar den svansen "
        "de mest sårbara kommunerna."
    ),

    "explain_trend_expander": "Hur läser jag trenddiagrammet?",
    "explain_trend_text": (
        "Linjediagrammet visar den valda kommunens skattekraft per invånare "
        "(kr) från 2010 till 2024 jämfört med riksgenomsnittet (streckad linje). "
        "Om kommunens linje ligger under riksgenomsnittet har den lägre "
        "skattekraft per invånare än en genomsnittskommun.\n\n"
        "**Exempel**: Om linjen lutar uppåt men inte lika brant som "
        "riksgenomsnittet, betyder det att kommunen visserligen växer, men "
        "halkar efter relativt sett. Tvärtom, om linjen stiger brantare, "
        "stärks kommunens relativa position."
    ),

    "explain_decomp_expander": "Hur läser jag dekomponeringen?",
    "explain_decomp_text": (
        "Staplarna visar hur varje strukturfaktor bidrar till kommunens "
        "avvikelse från riksgenomsnittet. Gröna staplar (positiva) innebär "
        "att faktorn drar kommunen uppåt, röda (negativa) drar nedåt.\n\n"
        "**Exempel**: Om 'Bidrag: arbetslöshet' visar -0,3 % innebär det "
        "att kommunens högre arbetslöshet (jämfört med riksgenomsnittet) "
        "bidrar med 0,3 procentenheter lägre skattekraftstillväxt. "
        "Residualen fångar kommunspecifika faktorer som inte förklaras av "
        "de fyra variablerna."
    ),

    "explain_ranking_expander": "Hur läser jag tabellen?",
    "explain_ranking_text": (
        "Tabellen rangordnar alla kommuner efter prognosticerad "
        "skattekraftstillväxt 2025. Rang 1 = mest sårbar (svagast prognos). "
        "Riskklass anger om kommunen tillhör de 20 % mest sårbara (Hög), "
        "de mellersta 60 % (Medel), eller de 20 % starkaste (Låg).\n\n"
        "**Exempel**: En kommun på rang 15 med riskklass Hög och prognos "
        "+1,5 % har en av de svagaste prognoserna i landet, trots att "
        "tillväxten fortfarande är positiv (nominellt). Tabellen kan sorteras "
        "genom att klicka på kolumnrubrikerna."
    ),

    "explain_peers_expander": "Hur läser jag jämförelsetabellen?",
    "explain_peers_text": (
        "Tabellen visar de fem kommuner som liknar den valda kommunen mest, "
        "baserat på sårbarhetsindex. Jämförbara kommuner har liknande "
        "kombination av strukturella förutsättningar.\n\n"
        "**Exempel**: Om din kommun har sårbarhetsrang 50 och de jämförbara "
        "kommunerna visar liknande arbetslöshet men lägre försörjningskvot, "
        "tyder det på att demografin är en relativt sett viktigare faktor "
        "för just din kommun."
    ),

    # Kommun comparison (multi-select)
    "compare_label": "Jämför med andra kommuner",
    "compare_placeholder": "Välj en eller flera kommuner",
    "compare_legend_national_avg": "Riksgenomsnitt",

    # Coefficient table — significance label for non-significant results
    "sig_not_significant": "ej sign.",

    # Choropleth — missing GeoJSON warning
    "choropleth_missing_geojson": (
        "GeoJSON-fil saknas. Kör scripts/download_geojson.py för att "
        "ladda ned kommunkartan."
    ),

    # Coefficient table — interpretation templates (use .format(v=effect_str))
    "interp_unemployment": "1 procentenhets ökning i arbetslöshet ger ca {v} procentenheter tillväxt",
    "interp_dependency": "0,1 ökning i försörjningskvot ger ca {v} procentenheter tillväxt",
    "interp_population": "1 procentenhets befolkningstillväxt ger ca {v} procentenheter tillväxt",
    "interp_education": "1 procentenhets ökning i utbildningsandel ger ca {v} procentenheter tillväxt",
}

# ---------------------------------------------------------------------------
# Number formatting helpers (PRD §9)
# ---------------------------------------------------------------------------


def format_sek(value: float) -> str:
    """Format integer SEK with narrow no-break space thousands separator.

    Args:
        value: Numeric value in SEK.

    Returns:
        Formatted string like '271\u202f000 kr'.
    """
    return f"{int(round(value)):,}".replace(",", "\u202f") + " kr"


def format_pct(value: float, decimals: int = 1) -> str:
    """Format percentage with comma decimal separator and % suffix.

    Args:
        value: Numeric percentage value (e.g. 2.3 for 2.3%).
        decimals: Number of decimal places.

    Returns:
        Formatted string like '2,3 %'.
    """
    return f"{value:.{decimals}f}".replace(".", ",") + " %"


def format_signed_pct(value: float, decimals: int = 1) -> str:
    """Format signed percentage with explicit + or - sign.

    Args:
        value: Numeric percentage value.
        decimals: Number of decimal places.

    Returns:
        Formatted string like '+2,3 %' or '-1,8 %'.
    """
    return f"{value:+.{decimals}f}".replace(".", ",") + " %"


def format_index_points(value: float, decimals: int = 1) -> str:
    """Format a signed movement in index points.

    Drift is a difference in index points, not a growth rate — "Filipstad fell
    1,2 indexenheter" is a statement about position relative to the country,
    not about its tax base shrinking (METHODOLOGY §2.7).

    Args:
        value: Movement in index points.
        decimals: Number of decimal places.

    Returns:
        Formatted string like '+1,2' or '-0,4'.
    """
    return f"{value:+.{decimals}f}".replace(".", ",")


# ---------------------------------------------------------------------------
# Position bands
# ---------------------------------------------------------------------------


class PositionBand(NamedTuple):
    """One band of relative position, used for filtering and for legends.

    These replaced the risk-class quintiles at the T1.2 cutover. The quintiles
    cut a forecast that scored r = +0.016 against realised growth, and they
    were relative by construction — exactly 58 kommuner were always "hög risk",
    even in a year when every tax base grew. A band is a cut of an observed
    level, so it means what it says and its membership can change.
    """

    key: str
    lower: float
    upper: float
    label: str


#: Contiguous and exhaustive: every kommun falls in exactly one band. The cuts
#: sit at 90 and 110 because the middle band then holds roughly the central
#: two-thirds of kommuner (the median sits at 96,6).
POSITION_BANDS: tuple[PositionBand, ...] = (
    PositionBand("low", float("-inf"), 90.0, SWEDISH_LABELS["band_low"]),
    PositionBand("mid", 90.0, 110.0, SWEDISH_LABELS["band_mid"]),
    PositionBand("high", 110.0, float("inf"), SWEDISH_LABELS["band_high"]),
)


def classify_position(index: float) -> PositionBand | None:
    """Return the band a relative-position index falls in.

    Args:
        index: Relative position, riket = 100.

    Returns:
        The matching band, or None when the value is missing.
    """
    if index is None or index != index:  # NaN
        return None
    for band in POSITION_BANDS:
        if band.lower <= index < band.upper:
            return band
    return None
