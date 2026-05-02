# ============================================================
#  Soil Recommendation Engine — Pure Rule-Based
#  No LLM, No RAG, No external APIs, No extra dependencies.
#
#  How it works:
#    1. Compare each soil parameter against ideal thresholds
#    2. Score overall soil health (0-100)
#    3. Match soil profile against crop requirements
#    4. Generate a structured recommendation report as a dict
#
#  Called from main.py ingest route.
#  Result stored in recommendations.result (as JSON string).
# ============================================================

import json
from typing import Optional

# ============================================================
#  IDEAL THRESHOLDS
#  Source: ICAR (Indian Council of Agricultural Research)
#  standard recommendations for Indian smallholder farming.
# ============================================================

THRESHOLDS = {
    "ph":       {"low": 5.5,  "high": 7.5,  "ideal_min": 6.0, "ideal_max": 7.0},
    "n":        {"low": 20,   "high": 280,   "ideal_min": 100, "ideal_max": 200},  # kg/ha
    "p":        {"low": 10,   "high": 60,    "ideal_min": 20,  "ideal_max": 50},   # kg/ha
    "k":        {"low": 10,   "high": 120,   "ideal_min": 40,  "ideal_max": 100},  # kg/ha
    "moisture": {"low": 20,   "high": 80,    "ideal_min": 40,  "ideal_max": 70},   # %
    "ec":       {"low": 0.1,  "high": 4.0,   "ideal_min": 0.5, "ideal_max": 2.0},  # dS/m
}

# ============================================================
#  CROP DATABASE
#  Each crop defines its acceptable range for each parameter.
#  Suitability is calculated by how many parameters fall
#  within that crop's required range.
# ============================================================

CROP_DB = {
    "Rice": {
        "ph":       (5.5, 6.5),
        "n":        (80,  200),
        "p":        (20,  60),
        "k":        (30,  100),
        "moisture": (60,  80),
        "ec":       (0.1, 3.0),
        "note": "Requires high moisture and standing water. Zinc deficiency is common — apply ZnSO4 at 25 kg/ha."
    },
    "Wheat": {
        "ph":       (6.0, 7.5),
        "n":        (80,  180),
        "p":        (20,  50),
        "k":        (30,  80),
        "moisture": (40,  65),
        "ec":       (0.1, 3.0),
        "note": "Critical irrigation at crown root initiation (21 days), jointing, and flowering."
    },
    "Maize": {
        "ph":       (5.8, 7.0),
        "n":        (100, 200),
        "p":        (25,  60),
        "k":        (40,  100),
        "moisture": (45,  70),
        "ec":       (0.1, 2.5),
        "note": "Sensitive to waterlogging. Apply zinc sulphate at 25 kg/ha as basal dose."
    },
    "Cotton": {
        "ph":       (5.8, 8.0),
        "n":        (80,  180),
        "p":        (20,  50),
        "k":        (40,  100),
        "moisture": (35,  65),
        "ec":       (0.1, 4.0),
        "note": "Apply borax at 10 kg/ha to prevent boll dropping. Sensitive to waterlogging."
    },
    "Groundnut": {
        "ph":       (6.0, 7.0),
        "n":        (15,  30),
        "p":        (30,  60),
        "k":        (40,  80),
        "moisture": (35,  60),
        "ec":       (0.1, 2.0),
        "note": "Being a legume, needs only starter nitrogen. Apply gypsum at 400 kg/ha at pegging stage."
    },
    "Soybean": {
        "ph":       (6.0, 7.0),
        "n":        (15,  30),
        "p":        (25,  55),
        "k":        (30,  80),
        "moisture": (40,  65),
        "ec":       (0.1, 2.5),
        "note": "Fixes its own nitrogen via Rhizobium. Sensitive to waterlogging."
    },
    "Tomato": {
        "ph":       (6.0, 6.8),
        "n":        (100, 200),
        "p":        (30,  60),
        "k":        (50,  120),
        "moisture": (50,  70),
        "ec":       (0.1, 2.5),
        "note": "Consistent moisture critical — avoid irregular watering to prevent blossom-end rot."
    },
    "Sugarcane": {
        "ph":       (5.5, 7.5),
        "n":        (150, 280),
        "p":        (40,  70),
        "k":        (60,  120),
        "moisture": (55,  75),
        "ec":       (0.1, 3.0),
        "note": "Heavy feeder requiring large nutrients. Apply in 4-5 splits across the season."
    },
    "Onion": {
        "ph":       (6.0, 7.5),
        "n":        (80,  150),
        "p":        (25,  50),
        "k":        (40,  90),
        "moisture": (45,  65),
        "ec":       (0.1, 1.2),
        "note": "Very sensitive to salinity. Sulfur is essential for pungency — use SSP or ammonium sulphate."
    },
    "Sorghum": {
        "ph":       (5.5, 7.5),
        "n":        (60,  150),
        "p":        (15,  40),
        "k":        (20,  70),
        "moisture": (30,  60),
        "ec":       (0.1, 4.0),
        "note": "Drought-tolerant. Good choice for sandy soils with low water retention."
    },
    "Pearl Millet": {
        "ph":       (5.5, 7.5),
        "n":        (40,  120),
        "p":        (15,  40),
        "k":        (20,  60),
        "moisture": (25,  55),
        "ec":       (0.1, 3.5),
        "note": "Very drought tolerant. Suitable for poor, sandy, low-fertility soils."
    },
}

# ============================================================
#  PARAMETER ANALYSIS
#  For each reading, determine status and what to do.
# ============================================================

def _analyze_parameter(name: str, value: float) -> dict:
    """
    Compare a single parameter against thresholds.
    Returns status, label, and a specific corrective action.
    """
    t = THRESHOLDS[name]

    if value < t["low"]:
        status = "Critical Low"
        color = "red"
    elif value < t["ideal_min"]:
        status = "Low"
        color = "orange"
    elif value <= t["ideal_max"]:
        status = "Ideal"
        color = "green"
    elif value <= t["high"]:
        status = "High"
        color = "orange"
    else:
        status = "Critical High"
        color = "red"

    actions = {
        "ph": {
            "Critical Low": "Apply agricultural lime at 3-4 tonnes/ha. Re-test after 2 months.",
            "Low":          "Apply agricultural lime at 1-2 tonnes/ha before sowing.",
            "Ideal":        "pH is perfect. No correction needed.",
            "High":         "Apply elemental sulfur at 200 kg/ha or add organic compost.",
            "Critical High":"Apply elemental sulfur at 400-500 kg/ha. Avoid alkaline irrigation water.",
        },
        "n": {
            "Critical Low": "Apply urea (46% N) at 150-200 kg/ha in two split doses immediately.",
            "Low":          "Apply urea at 100-120 kg/ha. Split: 50% at sowing, 50% at 30 days.",
            "Ideal":        "Nitrogen is sufficient. Maintain with 50 kg/ha as top dressing.",
            "High":         "Reduce nitrogen application. Excess N causes lodging and pest attacks.",
            "Critical High":"Stop all nitrogen fertilizers. Excess N causes groundwater contamination.",
        },
        "p": {
            "Critical Low": "Apply DAP at 150 kg/ha as basal dose before sowing.",
            "Low":          "Apply DAP at 100 kg/ha or SSP at 250 kg/ha as basal dose.",
            "Ideal":        "Phosphorus is sufficient. No correction needed.",
            "High":         "Reduce phosphorus application. Natural levels are adequate.",
            "Critical High":"Skip phosphorus fertilizer for this season.",
        },
        "k": {
            "Critical Low": "Apply MOP (60% K2O) at 100-120 kg/ha immediately.",
            "Low":          "Apply MOP at 60-80 kg/ha as basal dose.",
            "Ideal":        "Potassium is sufficient. No correction needed.",
            "High":         "Reduce potassium application. Natural levels are adequate.",
            "Critical High":"Skip potassium fertilizer for this season.",
        },
        "moisture": {
            "Critical Low": "Irrigate immediately. Apply 5-6 cm water. Check irrigation system.",
            "Low":          "Irrigate within 24 hours. Consider drip irrigation for efficiency.",
            "Ideal":        "Moisture is perfect. Maintain irrigation schedule.",
            "High":         "Stop irrigation. Improve field drainage channels.",
            "Critical High":"Waterlogged — create drainage furrows. Risk of root rot is high.",
        },
        "ec": {
            "Critical Low": "EC is very low — soil may be nutrient-depleted. Add fertilizers.",
            "Low":          "EC is slightly low. Normal fertilizer application will correct this.",
            "Ideal":        "EC is ideal. No salinity issues.",
            "High":         "Slight salinity. Apply 2 heavy irrigations to leach salts downward.",
            "Critical High":"High salinity. Apply gypsum at 5 tonnes/ha. Leach with 3-4 irrigations. Avoid salt-sensitive crops.",
        },
    }

    return {
        "value": value,
        "status": status,
        "color": color,
        "ideal_range": f"{t['ideal_min']} – {t['ideal_max']}",
        "action": actions[name][status],
    }


# ============================================================
#  SOIL HEALTH SCORE  (0 - 100)
#  Each parameter contributes equally (max ~16.67 points).
#  Ideal = full points, Low/High = partial, Critical = 0.
# ============================================================

SCORE_MAP = {
    "Ideal":        1.0,
    "Low":          0.5,
    "High":         0.5,
    "Critical Low": 0.0,
    "Critical High":0.0,
}

def _calculate_score(analyses: dict) -> int:
    params = list(analyses.values())
    total = sum(SCORE_MAP.get(p["status"], 0) for p in params)
    return round((total / len(params)) * 100)


# ============================================================
#  YIELD STATUS
# ============================================================

def _yield_status(score: int, analyses: dict) -> str:
    critical_count = sum(
        1 for p in analyses.values()
        if "Critical" in p["status"]
    )
    if critical_count >= 2 or score < 35:
        return "Poor"
    elif critical_count == 1 or score < 65:
        return "Moderate"
    else:
        return "Good"


# ============================================================
#  CROP MATCHING
#  Score each crop by how many parameters fall within its
#  required range. Return ranked list with match percentage.
# ============================================================

def _match_crops(
    avg_ph: float,
    avg_n: float,
    avg_p: float,
    avg_k: float,
    avg_moisture: float,
    avg_ec: float,
) -> list:

    readings = {
        "ph": avg_ph,
        "n": avg_n,
        "p": avg_p,
        "k": avg_k,
        "moisture": avg_moisture,
        "ec": avg_ec,
    }

    results = []

    for crop_name, req in CROP_DB.items():
        matched = 0
        total = 0
        mismatches = []

        for param, value in readings.items():
            if param not in req:
                continue
            lo, hi = req[param]
            total += 1
            if lo <= value <= hi:
                matched += 1
            else:
                if value < lo:
                    mismatches.append(f"{param.upper()} too low for {crop_name}")
                else:
                    mismatches.append(f"{param.upper()} too high for {crop_name}")

        match_pct = round((matched / total) * 100) if total else 0

        results.append({
            "crop": crop_name,
            "match_percent": match_pct,
            "parameters_matched": f"{matched}/{total}",
            "mismatches": mismatches,
            "note": req.get("note", ""),
        })

    # Sort by match percentage descending
    results.sort(key=lambda x: x["match_percent"], reverse=True)
    return results


# ============================================================
#  FERTILIZER SUMMARY
#  Consolidates actionable fertilizer recommendations
#  based on N, P, K status into a simple plan.
# ============================================================

def _fertilizer_plan(n_status: str, p_status: str, k_status: str) -> list:
    plan = []

    npk_map = {
        "n": {
            "Critical Low": {"product": "Urea (46% N)",            "dose": "150-200 kg/ha", "timing": "Split: 50% at sowing, 50% at 30 days"},
            "Low":          {"product": "Urea (46% N)",            "dose": "100 kg/ha",     "timing": "50% at sowing, 50% at 30 days"},
            "High":         {"product": "None — skip N fertilizer", "dose": "-",             "timing": "-"},
            "Critical High":{"product": "None — skip N fertilizer", "dose": "-",             "timing": "-"},
        },
        "p": {
            "Critical Low": {"product": "DAP (18-46-0)",            "dose": "150 kg/ha",     "timing": "Basal — before sowing"},
            "Low":          {"product": "DAP (18-46-0) or SSP",     "dose": "100 kg/ha",     "timing": "Basal — before sowing"},
            "High":         {"product": "None — skip P fertilizer", "dose": "-",             "timing": "-"},
            "Critical High":{"product": "None — skip P fertilizer", "dose": "-",             "timing": "-"},
        },
        "k": {
            "Critical Low": {"product": "MOP (60% K2O)",            "dose": "100 kg/ha",     "timing": "50% basal, 50% at 45 days"},
            "Low":          {"product": "MOP (60% K2O)",            "dose": "60 kg/ha",      "timing": "Basal — before sowing"},
            "High":         {"product": "None — skip K fertilizer", "dose": "-",             "timing": "-"},
            "Critical High":{"product": "None — skip K fertilizer", "dose": "-",             "timing": "-"},
        },
    }

    for nutrient, status in [("n", n_status), ("p", p_status), ("k", k_status)]:
        if status == "Ideal":
            continue
        if nutrient in npk_map and status in npk_map[nutrient]:
            entry = npk_map[nutrient][status].copy()
            entry["nutrient"] = nutrient.upper()
            plan.append(entry)

    if not plan:
        plan.append({
            "nutrient": "NPK",
            "product": "Balanced NPK (17-17-17)",
            "dose": "50 kg/ha",
            "timing": "As maintenance dose at sowing",
        })

    return plan


# ============================================================
#  ORGANIC PRACTICES
#  Suggested based on which parameters are deficient.
# ============================================================

def _organic_practices(analyses: dict) -> list:
    practices = []
    statuses = {k: v["status"] for k, v in analyses.items()}

    if "Low" in statuses["n"] or "Critical" in statuses["n"]:
        practices.append("Apply farmyard manure (FYM) at 10-15 tonnes/ha before sowing to improve nitrogen.")
        practices.append("Use Azospirillum biofertilizer (for cereals) or Rhizobium (for legumes) as seed treatment.")

    if "Low" in statuses["p"] or "Critical" in statuses["p"]:
        practices.append("Apply vermicompost at 3-5 tonnes/ha — improves phosphorus availability and soil structure.")
        practices.append("Use PSB (Phosphate Solubilising Bacteria) biofertilizer at 2 kg/ha to unlock soil P.")

    if "Low" in statuses["k"] or "Critical" in statuses["k"]:
        practices.append("Apply wood ash at 500 kg/ha as a natural potassium source (good for acidic soils).")

    if "Low" in statuses["moisture"] or "Critical" in statuses["moisture"]:
        practices.append("Mulch with dry straw or crop residue (5 cm thick) to reduce moisture evaporation by 30-40%.")

    if "High" in statuses["moisture"] or "Critical" in statuses["moisture"]:
        practices.append("Plant Dhaincha (Sesbania) as a green manure crop — it tolerates waterlogging and adds nitrogen.")

    if "High" in statuses["ec"] or "Critical" in statuses["ec"]:
        practices.append("Apply neem cake at 200 kg/ha — reduces salt stress and suppresses soil pests.")

    # Always recommend compost
    if not practices:
        practices.append("Apply compost at 5 tonnes/ha to maintain organic carbon and soil biological activity.")
    practices.append("Deep summer ploughing (30-45 cm) to expose soil to sunlight and break hard pans.")

    return practices


# ============================================================
#  PUBLIC API — called from main.py ingest route
# ============================================================

def generate_recommendation(
    avg_ph: float,
    avg_n: float,
    avg_p: float,
    avg_k: float,
    avg_moisture: float,
    avg_ec: float,
    current_crop: Optional[str],
) -> str:
    """
    Full rule-based analysis pipeline.
    Returns a JSON string stored in recommendations.result.
    """

    # 1. Analyze each parameter
    analyses = {
        "ph":       _analyze_parameter("ph",       avg_ph),
        "n":        _analyze_parameter("n",        avg_n),
        "p":        _analyze_parameter("p",        avg_p),
        "k":        _analyze_parameter("k",        avg_k),
        "moisture": _analyze_parameter("moisture", avg_moisture),
        "ec":       _analyze_parameter("ec",       avg_ec),
    }

    # 2. Overall score and yield status
    score = _calculate_score(analyses)
    yield_status = _yield_status(score, analyses)

    # 3. Crop matching
    crop_matches = _match_crops(avg_ph, avg_n, avg_p, avg_k, avg_moisture, avg_ec)
    top_3_crops = crop_matches[:3]

    # 4. Current crop specific match (if crop is given)
    current_crop_match = None
    if current_crop:
        matched = next(
            (c for c in crop_matches if c["crop"].lower() == current_crop.lower()),
            None
        )
        current_crop_match = matched or {
            "crop": current_crop,
            "match_percent": None,
            "note": "Crop not found in database. Applying general soil advice.",
            "mismatches": [],
        }

    # 5. Fertilizer plan
    fertilizer_plan = _fertilizer_plan(
        n_status=analyses["n"]["status"],
        p_status=analyses["p"]["status"],
        k_status=analyses["k"]["status"],
    )

    # 6. Organic practices
    organic_practices = _organic_practices(analyses)

    # 7. Build final report dict
    report = {
        "summary": {
            "soil_health_score": score,
            "yield_status": yield_status,
            "total_issues": sum(
                1 for p in analyses.values() if p["status"] != "Ideal"
            ),
        },
        "parameter_analysis": {
            param: {
                "value": data["value"],
                "status": data["status"],
                "ideal_range": data["ideal_range"],
                "action": data["action"],
            }
            for param, data in analyses.items()
        },
        "current_crop": current_crop_match,
        "recommended_crops": top_3_crops,
        "fertilizer_plan": fertilizer_plan,
        "organic_practices": organic_practices,
        "crop_suitability_ranking": [
            {
                "rank": i + 1,
                "crop": c["crop"],
                "match_percent": c["match_percent"],
                "parameters_matched": c["parameters_matched"],
            }
            for i, c in enumerate(crop_matches)
        ],
    }

    return json.dumps(report, indent=2)