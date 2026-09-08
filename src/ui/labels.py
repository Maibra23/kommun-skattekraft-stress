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
    "brand_sub": "Läge och förflyttning",
    "nav_landing": "Startsida",
    "nav_national": "Riksöversikt",
    "nav_kommun": "Kommunjämförelse",

    # Page eyebrows and titles
    "eyebrow_landing": "SKATTEKRAFT I SVERIGES KOMMUNER",
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
    "band_mid": (
        "90 till 110"
    ),
    "band_high": "Över 110",
    "band_legend_note": (
        "Kommunens skattekraft i procent av det oviktade riksgenomsnittet."
    ),
    "label_kommun_select": "VÄLJ KOMMUN",

    # Quintiles of the retired vulnerability score, relabelled by T4.2.
    # The cut is *relative*: exactly 58 kommuner land in the bottom fifth every
    # year, including years when every kommun's tax base grew. "Hög risk" said
    # fiscal distress; the data only ever said "lowest fifth of this ranking".
    "risk_low": "Översta femtedelen",
    "risk_medium": "De mittersta tre femtedelarna",
    "risk_high": "Nedersta femtedelen",

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
    "method_model_name": "Två modeller, två olika frågor",
    "method_period": (
        "Period: 2010 till 2026 (modellen skattas på 2010 till 2024)"
    ),
    "method_units": (
        "290 kommuner, 17 år, 4 930 observationer. Skattekraft finns till och "
        "med 2026, befolkning och utbildning till 2025 och arbetslöshet till "
        "2024. Modellen använder de år där alla variabler finns."
    ),
    "landing_lead": (
        "Var står din kommun mot riksgenomsnittet, och åt vilket håll rör den "
        "sig? Skillnaderna mellan kommuner är stora, trögrörliga och mätbara. "
        "Modellen förklarar dem, den förutsäger dem inte."
    ),
    "landing_stat_kommuner": "KOMMUNER",
    "landing_stat_panel": "ÅR MED DATA",
    "landing_stat_vars": "STRUKTURVARIABLER",
    "landing_stat_fe": "FIXED EFFECTS",
    "landing_stat_identified": "MÄTBARA DRIVKRAFTER",
    # The stat strip is four numbers and four one-word labels. "2 mätbara
    # drivkrafter" beside "4 strukturvariabler" is the single most important
    # fact about the model, and it was left for the reader to notice.
    "landing_stats_explanation": (
        "Så läser du raden ovan. {kommuner} kommuner är samtliga kommuner i "
        "Sverige, ingen är utelämnad. {years} år med data betyder att "
        "underlaget sträcker sig från {first_year} till {last_year}. "
        "{n_vars} strukturvariabler matas in i modellen: öppen arbetslöshet, "
        "försörjningskvot, befolkningstillväxt och andel eftergymnasialt "
        "utbildade. Av dem är det bara {n_identified} vars effekt går att "
        "mäta säkert när kommuner jämförs med varandra, nämligen "
        "utbildningsnivån och arbetslösheten. Övriga ingår som kontroller, "
        "och deras effekt kan mycket väl vara noll."
    ),
    "landing_model_title": "Modellöversikt",
    "landing_vars_title": "Variabler & koefficienter",
    "landing_pipeline_title": "Så blir statistiken till siffrorna på sidan",
    "landing_nav_title": "Utforska dashboarden",
    "landing_sources_title": "Källor & metod",
    # Four bare table codes. A reader could not tell which number came from
    # which source, or that the oldest unemployment years are a saved copy.
    "landing_sources_explanation": (
        "Alla siffror kommer från SCB. Koderna är SCB:s egna namn på "
        "tabellerna, så att den som vill kan hämta samma underlag själv. "
        "OE0101 är den beskattningsbara inkomsten per invånare, alltså "
        "skattekraften, och även SCB:s eget index. BE0101 är folkmängden, "
        "som ger både befolkningstillväxt och försörjningskvot. AA0003 är "
        "den öppna arbetslösheten; de äldsta åren finns inte längre kvar hos "
        "SCB och läses från en sparad kopia i projektet. UF0506 är "
        "utbildningsnivån i befolkningen."
    ),

    # Landing page — section explanations (collapsible)
    "landing_model_explanation": (
        "Fyra strukturvariabler matas in i modellen, men de bär inte lika "
        "mycket. Mellan kommuner går bara två av dem att särskilja: "
        "utbildningsnivå, som är den klart starkaste, och öppen arbetslöshet. "
        "Försörjningskvot och befolkningstillväxt ingår som kontroller. Deras "
        "effekt går inte att skilja från noll när kommuner jämförs med "
        "varandra. Resultatet är en förklaring av kommunens läge, inte en "
        "prognos för nästa år."
    ),
    "landing_vars_explanation": (
        "Varje punkt är effekten av en variabel, mätt i indexenheter per "
        "standardavvikelse. Strecket genom punkten är ett 95-procentigt "
        "konfidensintervall. Rör strecket den streckade nollinjen går "
        "effekten inte att skilja från slumpen, och variabeln redovisas som "
        "kontroll snarare än som drivkraft."
    ),
    "landing_vars_example": (
        "**Ett scenario**"
        "\n\n"
        "Du är ekonomichef i en kommun som ligger på index 84, alltså 16 "
        "indexenheter under riksgenomsnittet. Du vill veta vad den skillnaden "
        "består av innan du tar den vidare till nämnden. Diagrammet ovan "
        "svarar på precis den frågan, och det svarar inte på frågan om vad "
        "som skulle hända om ni ändrade något."
        "\n\n"
        "**Så läser du diagrammet**"
        "\n\n"
        "Punkten är effekten av en variabel och strecket genom den är ett "
        "95-procentigt konfidensintervall."
        "\n\n"
        "Den streckade nollinjen avgör tolkningen. Ligger hela strecket på "
        "ena sidan av linjen skiljer variabeln kommuner åt. Rör strecket "
        "linjen går effekten inte att skilja från noll, och punkten ritas "
        "grå. En grå variabel finns kvar i modellen som kontroll, men den "
        "förklarar inte varför en kommun ligger högre än en annan."
        "\n\n"
        "Effekten mäts per standardavvikelse i stället för per enhet. Det "
        "behövs för att de fyra variablerna ska gå att jämföra med varandra: "
        "en försörjningskvot rör sig mellan 0,5 och 1,2 medan "
        "utbildningsandelen rör sig mellan 6 och 61 procent, så råa "
        "koefficienter säger ingenting om vilken variabel som betyder mest."
        "\n\n"
        "**Vad diagrammet säger just nu**"
        "\n\n"
        "Utbildningsandelen ligger på +10,0 indexenheter per "
        "standardavvikelse, med intervallet +6,4 till +13,7. Hela strecket "
        "ligger klart över noll. Öppen arbetslöshet ligger på -2,7 med "
        "intervallet -3,8 till -1,5, alltså helt under noll."
        "\n\n"
        "Försörjningskvoten ligger på -0,6 med intervallet -2,4 till +1,2, "
        "som omsluter noll. Räknat i råa koefficienter ser försörjningskvoten "
        "störst ut av alla fyra. Räknat i verklig effekt mellan kommuner går "
        "den inte att skilja från ingenting."
        "\n\n"
        "**Två färdiga uträkningar**"
        "\n\n"
        "Filipstad ligger 16,7 indexenheter under riksgenomsnittet. Modellen "
        "hänför 12,9 av dem till utbildningsnivån och 4,0 till "
        "arbetslösheten, och lämnar 0,1 oförklarat."
        "\n\n"
        "Danderyd ligger 99,3 enheter över, och där förklarar samma modell "
        "knappt hälften. Sambandet är starkast i mitten av fördelningen och "
        "svagast i toppen, så för de allra rikaste kommunerna ska "
        "dekomponeringen läsas med försiktighet."
        "\n\n"
        "**Det viktigaste förbehållet**"
        "\n\n"
        "Utbildningsandelen samvarierar 0,81 med skattekraften. Sambandet är "
        "robust, men det ligger nära en omskrivning av samma sak: en "
        "befolkning med höga inkomster och en befolkning med lång utbildning "
        "är i stor utsträckning samma befolkning. Stapelns längd säger alltså "
        "inte hur mycket skattekraft en utbildningssatsning skulle ge."
    ),
    "landing_vars_expander": (
        "Hur läser jag diagrammet? Med exempel"
    ),
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
    # The four step boxes rendered with no heading and no explanation at all,
    # so "Rensning" and "Estimering" were labels a reader had to guess at.
    "landing_pipeline_explanation": (
        "Ingen siffra på sidan är inmatad för hand. Underlaget går genom "
        "fyra steg varje gång det uppdateras. Datainsamling hämtar "
        "statistiken direkt från SCB:s öppna API. Rensning lägger ihop "
        "källorna till en tabell med en rad per kommun och år, och rättar de "
        "kommuner som slagits ihop eller delats sedan {first_year}. "
        "Estimering skattar modellen och räknar fram varje kommuns läge mot "
        "riksgenomsnittet. Förklaring delar upp det läget på de variabler "
        "modellen kan mäta, och redovisar öppet hur stor del den inte kan "
        "förklara."
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
    "svg_identified_heading": "TYDLIG EFFEKT",
    "svg_controls_heading": "KONTROLLER: EFFEKTEN KAN VARA NOLL",
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
    "map_legend_drift": "Indexenheter, 5 år · orange = sjunkit mot riket",
    "map_legend_position_full": (
        "Kommunens skattekraft i procent av det oviktade riksgenomsnittet. "
        "Mörkare blå = högre. Skalan är beskuren vid 80 och 130, eftersom "
        "mediankommunen ligger på 97 och den högsta på 208. En obeskuren "
        "skala skulle ge nio kommuner av tio samma färg."
    ),
    "map_legend_drift_full": (
        "Förändring i indexenheter de senaste fem åren. Orange betyder att "
        "kommunens index har sjunkit, alltså att kommunen vuxit långsammare "
        "än övriga kommuner. Det betyder inte att skattekraften minskat: en "
        "kommun kan växa i kronor varje år och ändå sjunka i index. Blått "
        "betyder att indexet stigit, alltså att kommunen vuxit snabbare än "
        "övriga. Skalan är centrerad på noll och beskuren vid fyra "
        "indexenheter åt vardera hållet."
    ),
    "index_compare_title": "Två mått på samma sak",
    "index_compare_explanation": (
        "Vi jämför med ett snitt där alla 290 kommuner väger lika mycket. "
        "SCB jämför med ett snitt där stora kommuner väger tyngre. Därför "
        "ligger vårt tal alltid lite högre, i snitt 8 indexenheter. Båda är "
        "rätt, de svarar bara på olika frågor. <strong>Jämför aldrig ett tal "
        "från det ena måttet med ett tal från det andra.</strong>"
    ),
    "index_compare_ours": "Vårt index (oviktat)",
    "index_compare_scb": "SCB:s index (viktat)",

    # Pick specific kommuner by name, alongside the sidebar's band pills
    "kommun_filter_label": "Välj kommuner",
    "kommun_filter_placeholder": "Alla kommuner",
    "kommun_filter_help": (
        "Sök och välj en eller flera kommuner för att visa bara dem i "
        "tabellen. Lämna tomt för att visa alla."
    ),
    "kommun_filter_active": (
        "Visar {shown} av {total} kommuner. Rensa valet för att se alla."
    ),

    # Riksöversikt KPI row after the cutover
    "kpi_index_spread": "Högsta / lägsta index",
    "kpi_largest_fall_10y": "Största fall, 10 år",
    "kpi_largest_rise_10y": "Största ökning, 10 år",
    "kpi_index_spread_tooltip": (
        "Den högsta och den lägsta kommunens index, där riksgenomsnittet är "
        "100. Avståndet mellan talen visar hur olika kommunerna är: den "
        "högsta har mer än dubbelt så stor skattekraft per invånare som den "
        "lägsta."
    ),
    "kpi_largest_fall_tooltip": (
        "Den kommun vars index sjunkit mest på tio år, mätt i indexenheter. "
        "Ett fall betyder att kommunen vuxit långsammare än riket, inte att "
        "skattekraften minskat."
    ),
    "kpi_largest_rise_tooltip": (
        "Den kommun vars index stigit mest på tio år, mätt i indexenheter. "
        "Kommunen har alltså vuxit snabbare än riket."
    ),
    "kpi_cross_r2": "Modellens förklaringsgrad",
    "kpi_cross_r2_tooltip": (
        "Andel av skillnaderna i skattekraft mellan kommuner som de fyra "
        "strukturvariablerna förklarar, i tvärsnittet för {year}. Det är ett "
        "annat mått än panelmodellens R² inom kommuner, som är lågt av "
        "konstruktion och redovisas separat längre ner."
    ),
    "national_position_summary": (
        "Skillnaderna mellan kommuner är stora och trögrörliga. {high_name} "
        "ligger på index {high:.0f} och {low_name} på {low:.0f}. "
        "Rangordningen är i praktiken låst: sambandet mellan ett års position "
        "och nästa års är 0,99, och över tio år 0,93. Det som rör sig gör det "
        "långsamt. Därför visas förflyttning över fem och tio år, inte över "
        "ett."
    ),
    "kommun_position_lead": (
        "{kommun} ligger på index <strong>{position}</strong> av "
        "riksgenomsnittet, en förflyttning på <strong>{drift} "
        "indexenheter</strong> sedan {since}."
    ),
    "kommun_position_lead_no_drift": (
        "{kommun} ligger på index <strong>{position}</strong> av "
        "riksgenomsnittet."
    ),
    "kommun_kpi_explanation": (
        "De fyra talen hör ihop två och två. De första två är samma sak mätt "
        "på två sätt, och i båda är 100 genomsnittet: vårt index jämför med "
        "genomsnittet av de 290 kommunerna, SCB:s med riksmedelvärdet där "
        "varje invånare väger lika mycket. De sista två är förflyttning, "
        "alltså hur många indexenheter kommunen flyttat sig på fem "
        "respektive tio år. Ett minustal betyder att kommunen vuxit "
        "långsammare än riket, inte att skattekraften minskat."
    ),
    "chart_position_history": "Position över tid",
    "chart_position_history_note": (
        "Linjen visar vårt oviktade index, samma mått som det första "
        "nyckeltalet ovanför. SCB:s index ligger något lägre och ritas inte "
        "här."
    ),
    "explain_position_history_expander": "Hur läser jag diagrammet?",
    "explain_position_history_text": (
        "Linjen är kommunens skattekraft i procent av genomsnittet av de 290 "
        "kommunerna, ett år i taget. Den streckade linjen vid 100 är det "
        "genomsnittet, och den ligger på 100 varje år av konstruktion. "
        "Diagrammet visar alltså inte om kommunen fått mer pengar, utan om "
        "den flyttat sig i förhållande till de andra kommunerna."
        "\n\n"
        "**Exempel**: en linje som ligger stilla på 92 betyder att kommunen "
        "legat 8 procent under genomsnittet hela perioden, även om "
        "skattekraften i kronor stigit varje år. En linje som lutar nedåt "
        "betyder att kommunen vuxit långsammare än de andra. Diagrammet "
        "under det här visar samma kommun i kronor, och de två kan mycket "
        "väl peka åt olika håll."
    ),
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
        "skilja från noll: konfidensintervallen omsluter noll i varje år 2021 "
        "till {year}. De visas därför som siffror, inte som staplar. En "
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
        "i olika enheter. En försörjningskvot rör sig mellan 0,5 och 1,2 "
        "medan utbildningsandelen rör sig mellan 6 och 61 procent."
    ),
    "axis_beta_sd": "Effekt i indexenheter per standardavvikelse",
    "vars_table_effect_sd": "Effekt per standardavvikelse",
    "vars_table_ci": "Effekt per standardavvikelse, 95 % KI",
    "decomp_contribution_col": "Bidrag för kommunen (indexenheter)",
    "vars_table_identified": "Går att särskilja",
    "identified_yes": "Ja",
    "identified_no": (
        "Nej, intervallet omsluter noll"
    ),
    # A plain-language glossary. Terms like indexenheter, forflyttning,
    # forsorjningskvot and konfidensintervall appear dozens of times across
    # the app and were defined nowhere, so a reader had to infer them.
    # The idiom "tappa mark" was retired here and everywhere else: it reads
    # as losing territory or as the tax base shrinking, and it means neither.
    # Movement is stated literally instead, as the index rising or falling.
    "glossary_expander": "Ord och begrepp: vad betyder orden?",
    "glossary_text": (
        "Alla ord som används i dashboarden, förklarade utan fackspråk."
        "\n\n"
        "**Skattekraft** är den beskattningsbara inkomsten per invånare i "
        "kommunen. Det är summan som kommunen tar ut sin kommunalskatt på, "
        "och därmed grunden för vad den har råd med."
        "\n\n"
        "**Index och indexenheter.** För att kunna jämföra kommuner räknas "
        "skattekraften om till ett index där genomsnittet är 100. En kommun "
        "med index 80 har alltså 80 procent av genomsnittets skattekraft. "
        "Skillnaden mellan två indextal mäts i indexenheter: från 80 till 84 "
        "är fyra indexenheter."
        "\n\n"
        "**Förflyttning.** Förflyttning är hur mycket kommunens index har "
        "ändrats under en period, mätt i indexenheter. Ett minustal betyder "
        "att indexet har sjunkit, alltså att kommunen vuxit långsammare än "
        "riket. Det betyder inte att skattekraften har minskat. En kommun kan "
        "öka sin skattekraft i kronor varje år och ändå sjunka i index, om "
        "övriga kommuner ökar mer. Ett plustal är samma sak omvänt: kommunen "
        "har vuxit snabbare än riket, oavsett om det gick fort eller långsamt "
        "i kronor."
        "\n\n"
        "**Två genomsnitt som inte är samma sak.** Vårt index jämför med "
        "genomsnittet av de 290 kommunerna, där varje kommun väger lika "
        "mycket. SCB:s publicerade index jämför med riksmedelvärdet, där "
        "varje invånare väger lika mycket, så folkrika kommuner drar upp det. "
        "Därför ligger vårt tal alltid något högre än SCB:s. Båda är rätt, "
        "men de svarar på olika frågor, och ett tal från det ena måttet ska "
        "aldrig jämföras med ett tal från det andra."
        "\n\n"
        "**De fyra variablerna.**"
        "\n\n"
        "**Öppen arbetslöshet** är andelen av invånarna i arbetsför ålder som "
        "är inskrivna som arbetslösa utan att delta i något program. Ordet "
        "öppen betyder just att program inte räknas med."
        "\n\n"
        "**Försörjningskvot** är antalet invånare under 20 år plus antalet "
        "över 64 år, delat med antalet mellan 20 och 64. Kvoten 1,0 betyder "
        "att det går en person utanför arbetsför ålder på varje person i "
        "arbetsför ålder. Ju högre kvot, desto färre i arbetsför ålder att "
        "bära försörjningen."
        "\n\n"
        "**Befolkningstillväxt** är hur många procent folkmängden ändrats "
        "sedan året innan."
        "\n\n"
        "**Andel eftergymnasialt utbildade** är andelen av invånarna 25 till "
        "64 år som har minst tre års utbildning efter gymnasiet."
        "\n\n"
        "**Statistiken, i vardagliga ord.**"
        "\n\n"
        "**Standardavvikelse** är ett mått på hur mycket kommunerna skiljer "
        "sig åt i en variabel. När en effekt anges per standardavvikelse "
        "betyder det: så här mycket skiljer sig indexet om man jämför en "
        "kommun med en annan som ligger ett normalt kliv högre i just den "
        "variabeln. Måttet behövs för att variabler som mäts i olika enheter "
        "ska gå att jämföra med varandra."
        "\n\n"
        "**Konfidensintervall** är det spann som det sanna värdet rimligen "
        "ligger inom. Vi visar 95-procentiga intervall, vilket betyder att "
        "fem gånger av hundra hamnar det sanna värdet utanför. Innehåller "
        "intervallet noll kan vi inte påstå att effekten finns alls."
        "\n\n"
        "**Kontrollvariabel** är en variabel som finns med i modellen men "
        "vars effekt inte går att skilja från noll. Den redovisas som en "
        "siffra i stället för som en stapel, eftersom en stapel skulle se "
        "säkrare ut än den är."
        "\n\n"
        "**Residual** är den del av kommunens avvikelse som modellen inte "
        "förklarar. En stor residual betyder att något annat än de fyra "
        "variablerna avgör läget."
        "\n\n"
        "**Prognos och intervall.** Prognosen är hur många indexenheter "
        "kommunen väntas flytta sig på fem år. Intervallet visar hur osäker "
        "den siffran är, och bygger på hur fel prognosen faktiskt haft när "
        "den testats mot verkliga utfall."
        "\n\n"
        "**Träffsäkerhet** är hur väl prognosen träffat historiskt. Den mäts "
        "på två sätt: hur väl den får ordningen mellan kommuner rätt, och hur "
        "stort medelfelet är jämfört med att bara gissa genomsnittet."
    ),

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
        "att bara gissa riksgenomsnittet. Riskklasserna skilde sig inte "
        "heller åt i utfallet: låg 4,74 %, medel 4,52 %, hög 4,68 %. Lagret "
        "ligger kvar tills det tas bort helt; använd position och "
        "förflyttning i stället."
    ),
    "index_scatter_title": "Vårt index mot SCB:s, alla 290 kommuner",
    "index_scatter_note": (
        "Varje punkt är en kommun. Den streckade linjen är där måtten skulle "
        "sammanfalla. Alla 290 ligger ovanför den. Skillnaden är systematisk "
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
        "kommande {horizon} åren, utifrån strukturvariablerna i dag. "
        "Intervallet är {coverage} % och kommer från prognosens egna träffar "
        "i efterhandstestet, inte från regressionens nominella standardfel, "
        "som beskriver osäkerheten om linjen snarare än om en enskild kommun."
    ),
    "forecast_col": "Prognos {horizon} år",
    "forecast_interval_col": "Intervall",
    "backtest_title": "Prognosens träffsäkerhet",
    "backtest_lead": (
        "Prognosen är testad mot utfall som den inte fått se: modellen skattas "
        "om vid varje startår och jämförs med vad som faktiskt hände "
        "{horizon} år senare. {origins} startår, {n} kommunår."
    ),
    "backtest_spearman": "Hur väl ordningen stämmer",
    "backtest_rmse": "Medelfel (RMSE)",
    "backtest_naive": "Jämförelse: gissa genomsnittet",
    "backtest_persistence": "Jämförelse: anta att trenden fortsätter",
    "backtest_coverage": "Intervallets träffsäkerhet",
    "backtest_coverage_sentence": (
        "Intervallets träffsäkerhet: i efterhandstestet hamnade det verkliga "
        "utfallet inom intervallet i {measured} av fallen, mot de {nominal} "
        "intervallet är byggt för. Ligger de två talen nära varandra lovar "
        "intervallet ungefär så mycket som det håller."
    ),
    "backtest_spearman_tooltip": (
        "Hur väl prognosens ordning mellan kommuner stämmer med den verkliga "
        "ordningen, på en skala från 0 till 1. 1 betyder exakt rätt ordning, "
        "0 betyder att ordningen var slumpmässig."
    ),
    "backtest_rmse_tooltip": (
        "Genomsnittligt fel i indexenheter när prognosen jämförs med vad som "
        "faktiskt hände. Lägre är bättre, och talet säger ingenting ensamt: "
        "det ska läsas mot de två jämförelserna bredvid."
    ),
    "backtest_naive_tooltip": (
        "Samma fel för den enklaste tänkbara prognosen: att varje kommun rör "
        "sig lika mycket som genomsnittet av alla kommuner gjorde senast. "
        "Slår modellen inte det här talet är den inte värd att använda."
    ),
    "backtest_persistence_tooltip": (
        "Samma fel för prognosen att kommunens rörelse de senaste fem åren "
        "upprepas de kommande fem. Det är den svårare av de två "
        "jämförelserna."
    ),
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

    "within_section_guide_expander": "Hur läser jag tabellen? Med exempel",
    "within_section_guide": (
        "**Ett scenario**"
        "\n\n"
        "Du är controller och har sett att kommunens öppna arbetslöshet steg "
        "med en procentenhet förra året. Frågan du får är vad det betyder för "
        "skattekraften. Tabellen här svarar på den frågan, och det är en "
        "annan fråga än den som resten av sidan svarar på."
        "\n\n"
        "**Så läser du tabellen**"
        "\n\n"
        "Koefficienten säger hur skattekraftstillväxten förändras när "
        "variabeln ändras med en enhet i just den här kommunen, jämfört med "
        "kommunens egen normalnivå. Variablerna mäts året före tillväxten, "
        "eftersom sambandet är starkast med ett års fördröjning."
        "\n\n"
        "**Vad tabellen säger just nu**"
        "\n\n"
        "Arbetslösheten har koefficienten -0,106. En procentenhets högre "
        "arbetslöshet ett år hänger alltså ihop med ungefär 0,11 "
        "procentenheters lägre skattekraftstillväxt året därpå, inom samma "
        "kommun. Det är det starkaste och mest tillförlitliga sambandet i "
        "tabellen."
        "\n\n"
        "Försörjningskvoten har koefficienten -3,80, men den mäts som en kvot "
        "och inte i procent. En förändring på 0,1 motsvarar därför ungefär "
        "0,38 procentenheters lägre tillväxt, inte 3,8."
        "\n\n"
        "**Kolumnen Signifikans**"
        "\n\n"
        "Stjärnorna säger hur säkert sambandet är. Tre stjärnor betyder att "
        "ett samband så starkt skulle uppstå av ren slump i mindre än ett "
        "fall av tusen, två stjärnor i mindre än ett av hundra och en stjärna "
        "i mindre än fem av hundra. Står det ej sign. går sambandet inte att "
        "skilja från noll, och raden ska läsas som att vi inte vet."
        "\n\n"
        "**Varför den här tabellen inte kan rangordna kommuner**"
        "\n\n"
        "Modellen räknar bort allt som ligger fast för en kommun: geografi, "
        "näringsliv, historia. Kvar blir hur kommunen avviker från sig själv "
        "över tid. Eftersom 98 procent av skillnaderna i skattekraft ligger "
        "mellan kommuner och inte inom dem, är det just den variation som "
        "räknas bort här. Rangordningen kommer i stället från "
        "tvärsnittsmodellen högre upp på sidan."
        "\n\n"
        "Modellen förklarar 3,6 procent av variationen inom kommuner. Det "
        "låter lite och är förväntat: det mesta som händer med en kommuns "
        "skattekraft ett enskilt år är nationell konjunktur, och även den är "
        "borträknad."
    ),
    "decomp_guide_expander": "Hur läser jag diagrammet? Med exempel",
    "decomp_guide": (
        "**Ett scenario**"
        "\n\n"
        "Din kommun ligger under riksgenomsnittet och nämnden vill veta "
        "varför. Diagrammet delar upp avståndet i de delar modellen kan "
        "hänföra till en orsak, och redovisar öppet hur stor del den inte kan "
        "förklara."
        "\n\n"
        "**Så läser du diagrammet**"
        "\n\n"
        "Staplarna mäts i indexenheter, samma enhet som kommunens läge. Lägg "
        "ihop dem och du får hela avståndet till riksgenomsnittet. Den grå "
        "stapeln är residualen: den del som de fyra variablerna inte "
        "förklarar."
        "\n\n"
        "**En färdig uträkning**"
        "\n\n"
        "Östra Göinge ligger 12,7 indexenheter under riksgenomsnittet. "
        "Modellen hänför 8,4 av dem till utbildningsnivån och 4,4 till "
        "arbetslösheten, och lämnar 0,03 oförklarat. Nästan hela avståndet "
        "går alltså att peka på."
        "\n\n"
        "**Vad du inte kan läsa ut**"
        "\n\n"
        "Att utbildningsstapeln är lång betyder inte att en "
        "utbildningssatsning ger motsvarande skattekraft. Utbildningsnivå och "
        "skattekraft är till stor del två mätningar av samma sak."
        "\n\n"
        "Modellen är dessutom linjär och träffar sämst i toppen av "
        "fördelningen. För de allra rikaste kommunerna är en stor del av "
        "avvikelsen residual, och då säger uppdelningen mindre."
    ),
    "forecast_guide_expander": "Vad betyder prognosen för min kommun?",
    "forecast_guide": (
        "**Ett scenario**"
        "\n\n"
        "Du planerar på fem års sikt och vill veta om kommunen är på väg att "
        "sjunka i förhållande till riket. Prognosen ger ett svar, och lika "
        "viktigt ger "
        "den ett intervall som säger hur säkert svaret är."
        "\n\n"
        "**Så läser du prognosen**"
        "\n\n"
        "Talet är hur många indexenheter kommunen väntas flytta sig på fem "
        "år. Intervallet rymmer utfallet i ungefär fyra fall av fem, och det "
        "bygger på hur fel prognosen faktiskt haft tidigare, inte på en "
        "teoretisk formel."
        "\n\n"
        "**Två kommuner som skiljer sig åt**"
        "\n\n"
        "Solna har prognosen +5,0 med intervallet +2,5 till +7,3. Hela "
        "intervallet ligger över noll, så riktningen är tydlig."
        "\n\n"
        "Högsby har prognosen +0,2 med intervallet -2,3 till +2,5. "
        "Intervallet omsluter noll. Den ärliga slutsatsen är att vi inte vet "
        "åt vilket håll Högsby är på väg, och det är värt att veta innan man "
        "planerar som om man visste."
        "\n\n"
        "**Hur bra är prognosen?**"
        "\n\n"
        "Rangkorrelationen 0,33 betyder att den får ordningen ungefär rätt, "
        "men långt ifrån helt rätt. Den slår båda jämförelserna: medelfelet "
        "är 2,1 mot 2,3 för att gissa genomsnittet och 3,0 för att anta att "
        "trenden fortsätter. Använd den som en av flera ingångar, inte som "
        "ett facit."
    ),
    "peers_guide_expander": "Vad visar kolumnerna?",
    "peers_guide": (
        "**Vad tabellen visar**"
        "\n\n"
        "De fem kommuner som ligger närmast din i skattekraft mot "
        "riksgenomsnittet. Urvalet görs enbart på läge, inte på storlek, "
        "geografi eller näringsliv. Poängen är att se hur kommuner på samma "
        "nivå kan ha hamnat där av olika skäl."
        "\n\n"
        "**Kolumnerna**"
        "\n\n"
        "**Kommun** och **Län** anger vilken kommun raden gäller."
        "\n\n"
        "**Index ({position_year})** är kommunens skattekraft i procent av "
        "det oviktade riksgenomsnittet, där 100 är genomsnittet. Talet är "
        "från {position_year}, det senaste år skattekraften finns."
        "\n\n"
        "**Förflyttning 5 år** är hur många indexenheter kommunen flyttat sig "
        "de senaste fem åren. Plus betyder att kommunen stigit i förhållande "
        "till riket, minus att den sjunkit."
        "\n\n"
        "**Arbetslöshet ({analysis_year})** och **Utbildning "
        "({analysis_year})** är två av de strukturvariabler som förklarar "
        "läget. De är från {analysis_year} därför att "
        "arbetslöshetsstatistiken inte finns för senare år, medan "
        "skattekraften gör det."
        "\n\n"
        "**Så använder du tabellen**"
        "\n\n"
        "Om grannarna har samma index men klart högre utbildningsandel står "
        "din kommun på samma nivå av andra skäl än de gör. Det är en bra "
        "öppning för en jämförelse, inte ett svar i sig."
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
        "Primär specifikation: variablerna mäts året före tillväxten (t-1). "
        "Sambandet är genomgående starkare med ett års fördröjning. För "
        "arbetslöshet -0,50 mot -0,18 samtidigt, vilket följer av att "
        "skattekraften publiceras med två års eftersläpning. Den samtida "
        "specifikationen redovisas som robusthetskontroll."
    ),
    "within_section_caveat": (
        "Koefficienterna jämför varje kommun med sig själv över tid. De kan "
        "inte rangordna kommuner och förklarar inte varför en kommun ligger "
        "högre än en annan. 98 % av skillnaderna i skattekraft finns mellan "
        "kommuner, och just den variationen räknar den här modellen bort."
    ),
    "kpi_r2_tooltip": (
        "R2(within) mäter hur mycket av variationen inom kommuner som "
        "förklaras av strukturvariablerna, efter att kommun- och årseffekter "
        "absorberats. Ett lågt värde är förväntat och säger inget om hur väl "
        "modellen förklarar skillnader mellan kommuner. Det måttet är "
        "tvärsnittets R2, som redovisas separat och ligger på 0,69."
    ),
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
        "**Skattekraft** (beskattningsbar förvärvsinkomst per invånare) är "
        "det centrala måttet på en kommuns skattemässiga kapacitet. Det anger "
        "hur mycket inkomstskatt kommunen kan ta in per person, och avgör i "
        "praktiken vilka tjänster kommunen har råd att erbjuda sina invånare."
        "\n\n"
        "Skillnaderna är enorma: 2024 hade Danderyd ca 481 000 kr per "
        "invånare medan flera Norrlandskommuner låg under 180 000 kr. Det "
        "innebär att vissa kommuner har mer än dubbelt så stor skattebas per "
        "invånare."
        "\n\n"
        "Sverige har ett utjämningssystem som delvis kompenserar för dessa "
        "skillnader, men den underliggande skattekraften förblir en avgörande "
        "faktor för kommunens ekonomiska handlingsutrymme."
        "\n\n"
        "### Varför är det viktigt att följa skattekraftens utveckling?"
        "\n\n"
        "**Scenario 1: Kreditanalytiker på en bank** Du bedömer en kommuns "
        "kreditvärdighet inför ett obligationslån. Dashboarden visar att "
        "kommunen har sjunkande skattekraftstillväxt och hög "
        "försörjningskvot. Det signalerar ökad risk och påverkar din "
        "kreditbedömning."
        "\n\n"
        "**Scenario 2: Kommunal controller** Du planerar nästa års budget. "
        "Dashboarden visar att er kommun ligger 12 indexenheter under "
        "riksgenomsnittet, och att modellen hänför merparten till "
        "utbildningsnivån snarare än till arbetslösheten. Det är en "
        "förklaring av läget, inte en prognos för nästa år, och "
        "utbildningsstapeln är inte en spak att dra i, utan till stor del en "
        "omskrivning av samma sak."
        "\n\n"
        "**Scenario 3: Regional beslutsfattare (SKR/länsstyrelse)** Du vill "
        "se vilka kommuner i ditt län som halkar efter riket. Riksöversiktens "
        "förflyttningslager visar det direkt, över fem år, utan att du "
        "behöver samla in data manuellt. Ettårsrörelser visas inte, eftersom "
        "de nästan uteslutande är brus."
        "\n\n"
        "**Scenario 4: Forskare eller student** Du studerar kommunal ekonomi "
        "och vill förstå vilka strukturella faktorer som driver skillnaderna. "
        "Dekomponeringen bryter ner exakt hur mycket arbetslöshet, demografi, "
        "befolkning och utbildning bidrar för varje kommun."
    ),
    "guide_expander": "Hur använder jag dashboarden?",
    "guide_text": (
        "### Sidorna"
        "\n\n"
        "Dashboarden har tre sidor som du navigerar via sidopanelen till "
        "vänster."
        "\n\n"
        "1. Startsida (denna sida): översikt av modellen, variablerna och "
        "pipelinestegen."
        "\n\n"
        "2. Riksöversikt: alla 290 kommuner på en karta och i en tabell, med "
        "deras läge mot riksgenomsnittet och deras förflyttning."
        "\n\n"
        "3. Kommunjämförelse: välj en kommun och se dess position över tid, "
        "vad som förklarar läget, och jämförbara kommuner."
        "\n\n"
        "### Positionsfiltret i sidopanelen"
        "\n\n"
        "Filtret Position mot riket låter dig begränsa vyn till ett intervall "
        "av indexvärden: under 90, mellan 90 och 110, eller över 110. Till "
        "skillnad från den riskklassindelning som fanns här tidigare är detta "
        "ett mått på ett observerat läge, inte på en prognos, och antalet "
        "kommuner i varje band ändras när verkligheten gör det."
        "\n\n"
        "### Vad dashboarden inte gör"
        "\n\n"
        "Den rangordnar inte kommuner efter förväntad kris. Den visar var de "
        "står, åt vilket håll de rört sig, och vad som statistiskt förklarar "
        "skillnaderna. Femårsprognosen som finns redovisas alltid tillsammans "
        "med sitt eget träffsäkerhetstest."
    ),
    "vars_table_header": "Koefficientvärden",
    "vars_table_variable": "Variabel",
    "vars_table_coef": "Koefficient",
    "vars_table_sig": "Signifikans",
    "vars_table_interpretation": "Tolkning",

    # Graph explanations (collapsible, standardized)
    "explain_choropleth_expander": "Hur läser jag kartan?",
    "explain_choropleth_text": (
        "Kartan visar alla 290 kommuner. Vad färgen betyder beror på vilket "
        "lager du valt ovanför kartan, och de två skalorna är avsiktligt "
        "olika. Nuvarande position är en nivå: mörkare blått betyder högre "
        "skattekraft mot riksgenomsnittet, och skalan är beskuren vid 80 och "
        "130 eftersom mediankommunen ligger på 97 och den högsta på 208. "
        "Förflyttning 5 år är en förändring med ett tecken: orange betyder "
        "att kommunens index sjunkit i förhållande till riket, blått att det "
        "stigit, och skalan är centrerad på noll."
        "\n\n"
        "Exempel: i positionslagret framträder Stockholmsregionen mörk och "
        "delar av inlandet ljusa, nivåskillnader som ligger fast över "
        "decennier. I förflyttningslagret ser samma karta helt annorlunda ut, "
        "eftersom en kommun kan ligga lågt och ändå stiga i index. Håll "
        "muspekaren över en kommun för att se båda talen."
    ),
    "explain_histogram_expander": "Hur läser jag fördelningen?",
    "explain_histogram_text": (
        "Histogrammet visar samma storhet som kartan och byter när du byter "
        "lager. Varje stapel är ett intervall, och höjden anger hur många av "
        "de 290 kommunerna som hamnar där. Den streckade linjen markerar "
        "riksgenomsnittet: index 100 för en nivå, noll för en förflyttning."
        "\n\n"
        "Exempel: i positionslagret är fördelningen kraftigt högerskev. De "
        "flesta kommuner ligger tätt mellan 85 och 110, och en tunn svans "
        "sträcker sig upp mot 208. Det är därför kartans färgskala är "
        "beskuren. Utan beskärning skulle nio kommuner av tio få samma färg."
    ),
    "explain_trend_expander": "Hur läser jag trenddiagrammet?",
    # The span was written as "2010 till 2024" and the chart has plotted to
    # 2026 since skattekraft gained two years. It is formatted from the panel.
    "explain_trend_text": (
        "Linjediagrammet visar den valda kommunens skattekraft per invånare "
        "i kronor, från {first_year} till {last_year}, jämfört med "
        "genomsnittet av alla kommuner (streckad linje). Här är talen kronor "
        "och inte index, så diagrammet visar den faktiska nivån och inte "
        "kommunens placering. Ligger kommunens linje under den streckade har "
        "den lägre skattekraft per invånare än en genomsnittskommun."
        "\n\n"
        "**Exempel**: om linjen lutar uppåt men inte lika brant som den "
        "streckade, växer kommunen men långsammare än de andra. Då stiger "
        "kronorna samtidigt som indexet sjunker, och det är just därför de "
        "två diagrammen på sidan kan peka åt olika håll."
    ),

    "explain_ranking_expander": "Hur läser jag tabellen?",
    "explain_ranking_text": (
        "Tabellen listar alla 290 kommuner sorterade efter position, högst "
        "först. Den visar båda indexmåtten, skillnaden mellan dem, "
        "förflyttningen över fem och tio år samt femårsprognosen med sitt "
        "intervall."
        "\n\n"
        "Exempel: en kommun med index 88 och förflyttning -2,4 ligger under "
        "riksgenomsnittet och har sjunkit ytterligare de senaste fem åren. "
        "En kommun med index 88 och +1,1 ligger lika lågt men rör sig "
        "uppåt. Samma nivå, olika riktning, och det är skillnaden tabellen "
        "finns för att visa. Klicka på en kolumnrubrik för att sortera om."
    ),
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


#: How many decimals each displayed quantity carries.  Collected here because
#: the same number was previously shown three different ways: relative position
#: appeared as "79,9" on one card, "80" in a selector and "208.1" in a table,
#: and the effect chart said "-2,7" where the table beside it said "-2,69".
#: More decimals than the measurement supports reads as false precision.
DISPLAY_DECIMALS = {
    "index": 0,         # an index point is the meaningful unit; SCB rounds too
    "index_points": 1,  # movements are small, so the first decimal is signal
    "effect": 1,        # same unit as the index; the interval denies more
    "rate": 1,          # unemployment, education share
    "correlation": 2,   # 0,33 against 0,3 matters at this scale
    "error": 1,         # RMSE; 2,11 implies precision the backtest lacks
    "share": 0,         # R2 and coverage, shown as whole percent
}


def format_index(value: float) -> str:
    """Format a position index for display: whole numbers, no sign.

    Args:
        value: Index where the unweighted national mean is 100.

    Returns:
        Formatted string like '208'.
    """
    return f"{value:.{DISPLAY_DECIMALS['index']}f}"


def format_effect(value: float) -> str:
    """Format an effect per standard deviation, signed.

    Args:
        value: Effect in index points.

    Returns:
        Formatted string like '+10,0'.
    """
    return _signed(value, DISPLAY_DECIMALS["effect"])


def format_interval(low: float, high: float) -> str:
    """Format a confidence interval, with no dash between the bounds.

    Args:
        low: Lower bound.
        high: Upper bound.

    Returns:
        Formatted string like '+6,4 till +13,7'.
    """
    return f"{format_effect(low)} till {format_effect(high)}"


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
    return _signed(value, decimals)


def _signed(value: float, decimals: int) -> str:
    """Format a signed number, without producing a negative zero.

    A movement that rounds to nothing rendered as "-0,0", which reads as a
    fall that is not there. Zero carries no direction, so it carries no sign.

    Args:
        value: The number to format.
        decimals: Digits after the comma.

    Returns:
        Formatted string like '+1,3', '-0,4' or '0,0'.
    """
    rounded = round(value, decimals)
    if rounded == 0:
        return f"{0:.{decimals}f}".replace(".", ",")
    return f"{rounded:+.{decimals}f}".replace(".", ",")


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
