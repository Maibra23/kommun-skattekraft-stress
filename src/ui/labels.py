"""Authoritative Swedish user-facing label dictionary and number formatters.

SWEDISH_LABELS is the single source of truth for every string visible to
dashboard users.  Code that hardcodes Swedish text in component logic is
rejected in code review — always import from here.

Also provides three number formatting helpers:
  format_sek(value)              — integer SEK with narrow no-break space thousands separator
  format_pct(value, decimals)    — percentage with comma decimal and % suffix
  format_signed_pct(value, decimals) — signed percentage with explicit + or - sign
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
    "kpi_model_r2": "Modellens R²",

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
    "method_period": "Period: 2010 till 2024",
    "method_units": "290 kommuner, 15 ar, 4 350 observationer",

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
    "axis_coefficient": "\u03b2 (koefficient)",

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
        "R\u00b2(within) mäter hur mycket av variationen inom kommuner "
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
