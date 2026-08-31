"""
Technical vs. Professional track classification.

Per your call: the roadmap should render as two visually separate tracks
rather than one interleaved list. The split is grounded in O*NET's own
Content Model element-ID structure wherever that structure actually
encodes it — confirmed against real IDs before writing this, not guessed:

  - Essential Skills (2.A.*)      = O*NET's "Basic Skills" domain in full
                                     -> always PROFESSIONAL (Reading
                                     Comprehension, Writing, Critical
                                     Thinking, etc. — foundational, not
                                     coding-technical).
  - Transferable Skills (2.B.*)   = O*NET's "Cross-Functional Skills"
                                     domain, which DOES sub-group by ID:
                                       2.B.3.*  Technical Skills subgroup -> TECHNICAL
                                       2.B.1/2/4/5.*  Social, Complex
                                       Problem Solving, Systems, Resource
                                       Management -> PROFESSIONAL
  - Software Skills               = tools -> always TECHNICAL.
  - Knowledge (2.C.*)              O*NET's Knowledge domain does NOT encode
                                     a technical/professional split in its
                                     ID structure the way Skills does, so
                                     this part IS a curated judgment call,
                                     applied at the 2.C sub-group level with
                                     named overrides for the one genuinely
                                     mixed group (2.C.4, which spans
                                     Mathematics/Physics/Chemistry/Biology
                                     alongside Psychology/Sociology/
                                     Geography) — marked curated below.
  - Abilities (1.A.*)              Simplified as always PROFESSIONAL
                                     (cognitive/general capacities — not a
                                     learnable technical skill in the
                                     roadmap sense). A real product would
                                     likely drop most Abilities from the
                                     visible roadmap entirely rather than
                                     track them; deferred, not solved here.
"""

# Curated (see docstring): Knowledge 2.C sub-group defaults.
_KNOWLEDGE_GROUP_DEFAULT = {
    "2.C.1": "professional",  # business/admin/sales/HR/customer service
    "2.C.2": "technical",     # production & processing
    "2.C.3": "technical",     # engineering, CS, design, construction, mechanical
    "2.C.4": "professional",  # math/science group — overridden per-element below
    "2.C.5": "professional",  # medicine/therapy
    "2.C.6": "professional",  # education & training
    "2.C.7": "professional",  # language, arts, history, philosophy
    "2.C.8": "professional",  # public safety, law & government
    "2.C.9": "professional",  # telecom/communications — overridden per-element below
    "2.C.10": "technical",    # transportation (operational)
}
_KNOWLEDGE_ELEMENT_OVERRIDES = {
    "Mathematics": "technical", "Physics": "technical",
    "Chemistry": "technical", "Biology": "technical",
    "Telecommunications": "technical",
}


def classify_track(source: str, element_id: str = "", element_name: str = "") -> str:
    """Returns 'technical' or 'professional'."""
    if source == "software_skills" or source == "tool":
        return "technical"
    if source == "essential_skills":
        return "professional"
    if source == "transferable_skills":
        return "technical" if element_id.startswith("2.B.3.") else "professional"
    if source == "knowledge":
        if element_name in _KNOWLEDGE_ELEMENT_OVERRIDES:
            return _KNOWLEDGE_ELEMENT_OVERRIDES[element_name]
        group = ".".join(element_id.split(".")[:3]) if element_id.count(".") >= 2 else element_id
        return _KNOWLEDGE_GROUP_DEFAULT.get(group, "professional")
    if source == "abilities":
        return "professional"
    # graph-derived nodes (prerequisites, curated skill graph) are all
    # tech-track by construction (python, sql, react, security, etc.)
    if source in ("prerequisite", "graph"):
        return "technical"
    return "professional"


if __name__ == "__main__":
    import json
    from pathlib import Path

    occ = json.loads((Path(__file__).resolve().parents[2] / "data" / "processed" / "occupations.json")
                      .read_text())["15-2051.00"]
    for source in ["essential_skills", "transferable_skills", "knowledge"]:
        print(f"\n=== {source} ===")
        for item in sorted(occ[source], key=lambda x: -(x["importance"] or 0))[:8]:
            track = classify_track(source, item.get("element_id", ""), item["element"])
            print(f"  [{track:12s}] {item['element']} (imp={item['importance']})")
