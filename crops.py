

CROPS = {
    "winter_wheat": {
        "name": "Winter wheat", "species": "wheat", "group": "cereal",
        "season": "winter", "legume": False,
        "critical_ph": (5.2, 5.4),  # Koenig et al. FS050E
        "return_years": None,     # wheat every 2-3 years is standard regional practice
        "residue": "high",
    },
    "spring_wheat": {
        "name": "Spring wheat", "species": "wheat", "group": "cereal",
        "season": "spring", "legume": False,
        "critical_ph": (5.2, 5.4),  # Koenig et al. FS050E
        "return_years": None,
        "residue": "high",
    },
    "spring_barley": {
        "name": "Spring barley", "species": "barley", "group": "cereal",
        "season": "spring", "legume": False,
        "critical_ph": (5.2, 5.2),  # Koenig et al. FS050E
        "return_years": None,
        "residue": "high",
    },
    "winter_triticale": {
        "name": "Winter triticale", "species": "triticale", "group": "cereal",
        "season": "winter", "legume": False,
        "critical_ph": None,      # tolerates acidity better than wheat (WSU)
        "return_years": None,
        "residue": "high",        # straw similar to winter wheat (Ritzville trial, 2021)
    },
    "winter_pea": {
        "name": "Winter pea", "species": "pea", "group": "pulse",
        "season": "winter", "legume": True,
        "critical_ph": (5.5, 5.5),  # Koenig et al. FS050E
        "return_years": 6,        # European guidance (France, Germany)
        "residue": "low",         # very little durable residue (Schillinger 2017)
    },
    "spring_pea": {
        "name": "Spring pea", "species": "pea", "group": "pulse",
        "season": "spring", "legume": True,
        "critical_ph": (5.5, 5.5),  # Koenig et al. FS050E
        "return_years": 6,        # European guidance
        "residue": "low",
    },
    "lentil": {
        "name": "Lentil", "species": "lentil", "group": "pulse",
        "season": "spring", "legume": True,
        "critical_ph": (5.6, 5.6),  # Koenig et al. FS050E
        "return_years": 5,        # European guidance (Germany)
        "residue": None,          # no source found
    },
    "chickpea": {
        "name": "Chickpea", "species": "chickpea", "group": "pulse",
        "season": "spring", "legume": True,
        "critical_ph": None,      # no published threshold found
        "return_years": 5,        # European guidance (Germany: 5-6)
        "residue": "low",         # about half of wheat's (Lopez-Bellido et al. 2005, Spain)
    },
    "canola": {
        "name": "Canola", "species": "canola", "group": "oilseed",
        "season": "winter", "legume": False,
        "critical_ph": None,      # better than legumes on acid soil, but manganese-sensitive (WSU)
        "return_years": 3,        # European guidance (France 3, Germany 3-4)
        "residue": "low",         # more blowing dust after oilseeds (cited in Schillinger 2017)
    },
    "forage_cover": {
        "name": "Forage cover crop", "species": "mixed", "group": "forage",
        "season": "spring", "legume": False,
        "critical_ph": None,
        "return_years": None,
        "residue": "removed",     # baled or grazed (Kahl, Boone and Brooks 2022)
    },
    "fallow": {
        "name": "Summer fallow", "species": None, "group": "fallow",
        "season": None, "legume": False,
        "critical_ph": None,
        "return_years": None,
        "residue": None,
    },
}

# Yield relationships from regional trials (used in step 6).
# Winter pea yielded 2,443 kg/ha vs winter wheat 4,878 in the same rotation slot.
WINTER_PEA_VS_WINTER_WHEAT = 2443 / 4878          # Schillinger 2017, Ritzville
# Spring wheat after winter pea yielded 2,298 vs 2,122 kg/ha after winter wheat.
SW_AFTER_PEA_VS_AFTER_WHEAT = 2298 / 2122          # Schillinger 2017
# Winter triticale yielded 86 vs 75 bu/acre for winter wheat (3-year rotation).
TRITICALE_VS_WINTER_WHEAT = 86 / 75                # Ritzville trial, Crops & Soils 2021
# Winter wheat after a crop instead of fallow, compared with after fallow (kg/ha).
WW_LOSS_AFTER_PULSE_KG = 325                       # Maaz et al. 2017
WW_LOSS_AFTER_OILSEED_KG = 600                     # Maaz et al. 2017