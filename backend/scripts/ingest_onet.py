"""
LearnAscent AI — O*NET Data Ingestion Pipeline (Phase 1)
==========================================================

Reads the raw O*NET Excel exports (as actually shipped by O*NET — columns
were inspected directly, nothing here is assumed), normalizes them, and
builds:

  1. backend/data/processed/occupations.json
       One record per occupation, keyed by O*NET-SOC Code, containing the
       full "Career Requirement Profile":
         - essential_skills   [{element, importance, level}]
         - software_skills    [{name, hot_technology, in_demand}]
         - knowledge          [{element, importance, level}]
         - abilities          [{element, importance, level}]
         - transferable_skills[{element, importance, level}]
         - training_experience{related_work_experience, on_the_job_training,
                                on_site_training, importance}
         - job_zone           {zone, name, experience, education, job_training,
                                examples, svp_range}
         - interests          {riasec: {...}, high_point: str,
                                specific_interest_areas: [...]}
         - emerging_tasks     [...]

  2. backend/data/processed/occupation_search_index.json
       Lightweight list for fuzzy occupation-title matching (Feature 4:
       Goal Reverse Engineering starts here — user types a target career,
       this resolves it to an O*NET-SOC Code).

  3. backend/data/processed/onet.db (SQLite)
       Same data in queryable relational form, for the backend engines
       (skill-gap analysis, etc.) that need to query by element rather than
       by occupation.

Design notes:
  - The rating tables (Abilities, Essential Skills, Knowledge, Transferable
    Skills) all ship as TWO rows per (occupation, element): one Scale ID=IM
    (Importance, 1-5) and one Scale ID=LV (Level, 0-7). We pivot these back
    into one row per pair — this is real O*NET structure, not an assumption.
  - Training and Experience has a genuinely different shape (RW/OJ/PT are
    categorical codes 1-9/1-11, IM is a 1-5 importance score) and is handled
    on its own branch rather than forced through the same pivot.
  - Software Skills has no Importance/Level scale at all — just presence +
    Hot Technology / In Demand flags — also handled on its own branch.
  - Nothing here is a guess: every branch below matches a column set that
    was directly inspected from the uploaded files before writing this.
"""

import json
import sqlite3
import unicodedata
from pathlib import Path

import pandas as pd

# Raw O*NET workbooks are project data, while this script lives under
# backend/scripts.  Reading backend/data/raw silently used stale output in
# deployments where that directory was absent, leaving every career with an
# old, non-occupation-specific profile.
RAW = Path(__file__).resolve().parents[2] / "data" / "raw"
OUT = Path(__file__).resolve().parents[1] / "data" / "processed"
OUT.mkdir(parents=True, exist_ok=True)


def load(name: str) -> pd.DataFrame:
    path = RAW / f"{name}.xlsx"
    if not path.exists():
        raise FileNotFoundError(f"Expected raw file not found: {path}")
    return pd.read_excel(path)


def normalize_title(title: str) -> str:
    t = unicodedata.normalize("NFKD", str(title)).lower()
    return "".join(ch for ch in t if ch.isalnum() or ch.isspace()).strip()


def pivot_im_lv(df: pd.DataFrame) -> dict:
    """
    Pivot a standard O*NET rating table (Abilities / Essential Skills /
    Knowledge / Transferable Skills) — which has one row per
    (O*NET-SOC Code, Element, Scale ID in {IM, LV}) — into:
        { code: [ {element_id, element, importance, level}, ... ] }
    """
    out: dict[str, list] = {}
    keep_cols = ["O*NET-SOC Code", "Element ID", "Element Name", "Scale ID", "Data Value"]
    sub = df[keep_cols].copy()

    grouped = sub.groupby(["O*NET-SOC Code", "Element ID", "Element Name"])
    for (code, elem_id, elem_name), g in grouped:
        row = {"element_id": elem_id, "element": elem_name, "importance": None, "level": None}
        for _, r in g.iterrows():
            if r["Scale ID"] == "IM":
                row["importance"] = r["Data Value"]
            elif r["Scale ID"] == "LV":
                row["level"] = r["Data Value"]
        out.setdefault(code, []).append(row)
    return out


def build_training_experience(df: pd.DataFrame) -> dict:
    """
    Training and Experience mixes categorical scales (RW/OJ/PT, each with a
    numeric Category 1-9/1-11) with a plain IM importance score. We keep the
    highest-weighted category per scale per occupation (O*NET convention:
    Data Value on these rows is the % of respondents in that category — the
    modal category is the best single descriptor) plus the importance score.
    """
    out: dict[str, dict] = {}
    scale_label = {
        "RW": "related_work_experience",
        "OJ": "on_the_job_training",
        "PT": "on_site_training",
    }
    for code, g in df.groupby("O*NET-SOC Code"):
        entry = {"related_work_experience": None, "on_the_job_training": None,
                 "on_site_training": None, "importance": None}
        for scale, label in scale_label.items():
            rows = g[g["Scale ID"] == scale]
            if len(rows):
                top = rows.loc[rows["Data Value"].idxmax()]
                entry[label] = {"category": top["Category"], "pct_respondents": top["Data Value"]}
        imp_rows = g[g["Scale ID"] == "IM"]
        if len(imp_rows):
            entry["importance"] = imp_rows["Data Value"].iloc[0]
        out[code] = entry
    return out


def build_software_skills(df: pd.DataFrame) -> dict:
    """
    'Element Name' is the broad software CATEGORY (e.g. "Development
    environment software"); 'Workplace Example' is the actual named
    product/tool (e.g. "Python", "GitHub", "Adobe Photoshop"). Verified
    against raw rows — the recommendation engine (Feature 8) needs the real
    tool name, so that's what we expose as `name`, with the O*NET category
    kept alongside for grouping/filtering.
    """
    out: dict[str, list] = {}
    for code, g in df.groupby("O*NET-SOC Code"):
        items = []
        for _, r in g.iterrows():
            items.append({
                "name": r["Workplace Example"],
                "category": r["Element Name"],
                "hot_technology": r["Hot Technology"] == "Y",
                "in_demand": r["In Demand"] == "Y",
            })
        out[code] = items
    return out


def build_job_zones(jz_df: pd.DataFrame, ref_df: pd.DataFrame) -> dict:
    ref = {int(r["Job Zone"]): {
        "name": r["Name"], "experience": r["Experience"], "education": r["Education"],
        "job_training": r["Job Training"], "examples": r["Examples"], "svp_range": r["SVP Range"],
    } for _, r in ref_df.iterrows()}
    out = {}
    for _, r in jz_df.iterrows():
        zone = int(r["Job Zone"])
        out[r["O*NET-SOC Code"]] = {"zone": zone, **ref.get(zone, {})}
    return out


RIASEC_CODE_MAP = {
    1: "Realistic", 2: "Investigative", 3: "Artistic",
    4: "Social", 5: "Enterprising", 6: "Conventional",
}
IH_RANK_ORDER = {
    "First Interest High-Point": 0, "Second Interest High-Point": 1, "Third Interest High-Point": 2,
}


def build_interests(career_df: pd.DataFrame, specific_df: pd.DataFrame) -> dict:
    """
    Career Interest Types packs two different encodings under one sheet:
      - Scale ID 'OI': Element Name IS the RIASEC dimension (Realistic,
        Investigative, ...) and Data Value is that dimension's score.
      - Scale ID 'IH': Element Name is a RANK LABEL ("First/Second/Third
        Interest High-Point") and Data Value is a 1-6 CODE pointing at which
        RIASEC dimension holds that rank (0 = no distinct pick at that rank).
    These must not be conflated — confirmed against raw rows before writing
    this branch (e.g. Software Developers: First->2(Investigative, its top
    OI score), Second->6(Conventional, its 2nd-highest OI score), Third->0).
    """
    out: dict[str, dict] = {}
    for code, g in career_df.groupby("O*NET-SOC Code"):
        riasec = {}
        high_points_by_rank: list = [None, None, None]
        for _, r in g.iterrows():
            if r["Scale ID"] == "OI":
                riasec[r["Element Name"]] = r["Data Value"]
            elif r["Scale ID"] == "IH":
                rank_idx = IH_RANK_ORDER.get(r["Element Name"])
                code_val = int(r["Data Value"]) if pd.notna(r["Data Value"]) else 0
                if rank_idx is not None:
                    high_points_by_rank[rank_idx] = RIASEC_CODE_MAP.get(code_val)
        out[code] = {
            "riasec": riasec,
            "high_points": high_points_by_rank,  # ordered [1st, 2nd, 3rd], None = no distinct pick
            "specific_interest_areas": [],
        }

    for code, g in specific_df.groupby("O*NET-SOC Code"):
        areas = []
        for _, r in g[g["Scale ID"] == "OI"].iterrows():
            areas.append({"element": r["Element Name"], "score": r["Data Value"]})
        out.setdefault(code, {"riasec": {}, "high_points": [None, None, None], "specific_interest_areas": []})
        out[code]["specific_interest_areas"] = sorted(areas, key=lambda x: -(x["score"] or 0))[:8]
    return out


def build_emerging_tasks(df: pd.DataFrame) -> dict:
    out: dict[str, list] = {}
    for code, g in df.groupby("O*NET-SOC Code"):
        out[code] = [{"task": r["Task"], "category": r["Category"]} for _, r in g.iterrows()]
    return out


def main():
    print("Loading raw O*NET tables...")
    occ = load("Occupation Data")
    abilities = load("Abilities")
    essential = load("Essential Skills")
    knowledge = load("Knowledge")
    transferable = load("Transferable Skills")
    training = load("Training and Experience")
    software = load("Software Skills")
    job_zones = load("Job Zones")
    job_zone_ref = load("Job Zone Reference")
    career_interest = load("Career Interest Types")
    specific_interest = load("Specific Interest Areas")
    emerging = load("Emerging Tasks")
    # Education Categories / Task Categories are small reference/lookup
    # tables (24 and 7 rows respectively) — copied through as-is for the
    # engines to reference, not joined onto occupations.
    education_cats = load("Education Categories")
    task_cats = load("Task Categories")

    print(f"  {len(occ)} occupations")

    print("Pivoting IM/LV rating tables...")
    abilities_by_code = pivot_im_lv(abilities)
    essential_by_code = pivot_im_lv(essential)
    knowledge_by_code = pivot_im_lv(knowledge)
    transferable_by_code = pivot_im_lv(transferable)

    print("Building Training & Experience, Software Skills, Job Zones, Interests, Emerging Tasks...")
    training_by_code = build_training_experience(training)
    software_by_code = build_software_skills(software)
    jobzone_by_code = build_job_zones(job_zones, job_zone_ref)
    interests_by_code = build_interests(career_interest, specific_interest)
    emerging_by_code = build_emerging_tasks(emerging)

    print("Assembling per-occupation Career Requirement Profiles...")
    occupations = {}
    for _, r in occ.iterrows():
        code = r["O*NET-SOC Code"]
        occupations[code] = {
            "code": code,
            "title": r["Title"],
            "description": r["Description"],
            "essential_skills": essential_by_code.get(code, []),
            "software_skills": software_by_code.get(code, []),
            "knowledge": knowledge_by_code.get(code, []),
            "abilities": abilities_by_code.get(code, []),
            "transferable_skills": transferable_by_code.get(code, []),
            "training_experience": training_by_code.get(code, {}),
            "job_zone": jobzone_by_code.get(code, {}),
            "interests": interests_by_code.get(code, {}),
            "emerging_tasks": emerging_by_code.get(code, []),
        }

    (OUT / "occupations.json").write_text(json.dumps(occupations, indent=None, default=lambda o: None))
    print(f"  wrote occupations.json ({len(occupations)} occupations, "
          f"{(OUT / 'occupations.json').stat().st_size / 1e6:.1f} MB)")

    print("Building search index...")
    search_index = [
        {"code": code, "title": rec["title"], "normalized_title": normalize_title(rec["title"])}
        for code, rec in occupations.items()
    ]
    (OUT / "occupation_search_index.json").write_text(json.dumps(search_index))
    print(f"  wrote occupation_search_index.json ({len(search_index)} entries)")

    (OUT / "education_categories.json").write_text(
        education_cats.to_json(orient="records", default_handler=str))
    (OUT / "task_categories.json").write_text(
        task_cats.to_json(orient="records", default_handler=str))

    print("Building SQLite store (backend/data/processed/onet.db)...")
    db_path = OUT / "onet.db"
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(db_path)

    occ[["O*NET-SOC Code", "Title", "Description"]].rename(
        columns={"O*NET-SOC Code": "code", "Title": "title", "Description": "description"}
    ).to_sql("occupations", conn, index=False)

    def flat_rating_table(by_code: dict, table_name: str):
        rows = []
        for code, items in by_code.items():
            for it in items:
                rows.append({"code": code, **it})
        pd.DataFrame(rows).to_sql(table_name, conn, index=False)

    flat_rating_table(essential_by_code, "essential_skills")
    flat_rating_table(knowledge_by_code, "knowledge")
    flat_rating_table(abilities_by_code, "abilities")
    flat_rating_table(transferable_by_code, "transferable_skills")

    sw_rows = []
    for code, items in software_by_code.items():
        for it in items:
            sw_rows.append({"code": code, **it})
    pd.DataFrame(sw_rows).to_sql("software_skills", conn, index=False)

    jz_rows = [{"code": c, **v} for c, v in jobzone_by_code.items()]
    pd.DataFrame(jz_rows).to_sql("job_zones", conn, index=False)

    conn.execute("CREATE INDEX idx_essential_code ON essential_skills(code)")
    conn.execute("CREATE INDEX idx_essential_elem ON essential_skills(element)")
    conn.execute("CREATE INDEX idx_knowledge_code ON knowledge(code)")
    conn.execute("CREATE INDEX idx_abilities_code ON abilities(code)")
    conn.execute("CREATE INDEX idx_transferable_code ON transferable_skills(code)")
    conn.execute("CREATE INDEX idx_software_code ON software_skills(code)")
    conn.execute("CREATE INDEX idx_software_name ON software_skills(name)")
    conn.commit()
    conn.close()
    print(f"  wrote onet.db ({db_path.stat().st_size / 1e6:.1f} MB)")

    print("\nPhase 1 ingestion complete.")


if __name__ == "__main__":
    main()
