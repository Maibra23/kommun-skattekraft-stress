"""Authoritative Swedish user-facing label dictionary and number formatters.

SWEDISH_LABELS is the single source of truth for every string visible to
dashboard users.  Code that hardcodes Swedish text in component logic is
rejected in code review, always import from here.

Also provides three number formatting helpers:
  format_sek(value)              - integer SEK with narrow no-break space thousands separator
  format_pct(value, decimals)    - percentage with comma decimal and % suffix
  format_signed_pct(value, decimals) - signed percentage with explicit + or - sign
"""

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
    "chart_distribution": "Fördelning av prognosticerad tillväxt",

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
    "map_subtitle": "Sårbarhetsindex per kommun",
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
    "method_model_name": "Tvåvägs fixed effects panelmodell",
    "method_period": "Period: 2010 till 2026 (modellen skattas på 2010–2024)",
    "method_units": (
        "290 kommuner, 17 år, 4 930 observationer. Skattekraft finns till och "
        "med 2026, befolkning och utbildning till 2025 och arbetslöshet till "
        "2024 — modellen använder de år där alla variabler finns."
    ),

    # Landing page
    "landing_lead": (
        "En panelmodell som identifierar kommuner med svag prognosticerad "
        "skattekraftstillväxt och dekomponerar drivkrafterna bakom "
        "skillnaderna mellan kommuner."
    ),
    "landing_stat_kommuner": "KOMMUNER",
    "landing_stat_panel": "ÅR PANEL",
    "landing_stat_vars": "STRUKTURVARIABLER",
    "landing_stat_fe": "FIXED EFFECTS",
    "landing_model_title": "Modellöversikt",
    "landing_vars_title": "Variabler & vikter",
    "landing_pipeline_title": "Pipelinesteg",
    "landing_nav_title": "Utforska dashboarden",
    "landing_sources_title": "Källor & metod",

    # Landing page — section explanations (collapsible)
    "landing_model_explanation": (
        "Diagrammet ovan visar hur modellen fungerar: fyra strukturvariabler "
        "(arbetslöshet, försörjningskvot, befolkningstillväxt och utbildningsnivå) "
        "matas in i en regressionsmodell som producerar tre resultat: "
        "en tillväxtprognos för 2025, en sårbarhetsrangordning och en "
        "strukturell dekomponering av drivkrafterna."
    ),
    "landing_model_example": (
        "Tänk dig en kommun med stigande arbetslöshet och åldrande befolkning. "
        "Modellen fångar att dessa faktorer historiskt sett hänger samman med "
        "lägre skattekraftstillväxt, och ger kommunen en högre sårbarhetspoäng. "
        "Kommunalrådet kan sedan se exakt hur mycket arbetslösheten respektive "
        "demografin bidrar till den svaga prognosen, och prioritera insatser därefter."
    ),
    "landing_model_expander": "Hur läser jag diagrammet?",
    "landing_vars_explanation": (
        "Staplarna visar hur starkt varje variabel påverkar skattekraftstillväxten. "
        "Negativa värden (röda) innebär att en ökning av variabeln är förknippad "
        "med lägre tillväxt. Stjärnorna (***) anger statistisk signifikans."
    ),
    "landing_vars_example": (
        "Exempel: koefficienten för öppen arbetslöshet är ca −0,06. Det innebär "
        "att om en kommuns arbetslöshet ökar med 1 procentenhet (t.ex. från 8 % "
        "till 9 %), förväntas skattekraftstillväxten minska med ungefär 0,06 "
        "procentenheter, allt annat lika. Effekten är liten per enhet men "
        "kan bli betydande vid stora förändringar."
    ),
    "landing_vars_expander": "Hur tolkar jag koefficienterna?",
    "landing_nav_explanation": (
        "Dashboarden har två huvudvyer. Välj den som passar din frågeställning."
    ),
    "landing_nav_national_desc": (
        "Kartvy och rangordning av alla 290 kommuners "
        "prognosticerade skattekraftstillväxt."
    ),
    "landing_nav_kommun_desc": (
        "Detaljerad vy med historisk trend, strukturell "
        "dekomponering och jämförelse med liknande kommuner."
    ),
    "landing_step_1": "Datainsamling",
    "landing_step_2": "Rensning",
    "landing_step_3": "Estimering",
    "landing_step_4": "Prognos",

    # Riksöversikt
    "chart_ranking_title": "Rangordning",

    # Kommunjämförelse
    "chart_national_avg": "Riksgenomsnitt",
    "chart_peers_title": "Jämförbara kommuner",
    "subtitle_national": "Skattekraftens prognosticerade utveckling 2025, alla 290 kommuner",
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
    "svg_decomposition": "Dekomponering",

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
