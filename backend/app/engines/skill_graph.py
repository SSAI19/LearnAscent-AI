"""
Skill Prerequisite Graph (Feature 6).

O*NET tells us WHAT skills/knowledge/tools an occupation needs and HOW
IMPORTANT/at what LEVEL — it does not tell us the order in which a learner
should acquire them (e.g. that Pandas depends on Python, or that Deep
Learning depends on Machine Learning fundamentals). The spec explicitly
calls for a separate curated layer for this and requires marking curated
edges rather than presenting them as if they were O*NET-sourced — done here
via `source="curated"` on every edge, with no edge in this file claiming
`source="onet"` since O*NET provides no prerequisite relationships at all
in the files provided.

This is a small, hand-built starter graph (not exhaustive) scoped to the
tech-adjacent occupations these datasets are being exercised against. It's
meant to be extended, not treated as complete — each node also carries an
`onet_element` link where one exists, so the graph can be cross-referenced
against a learner's O*NET-scale skill levels from the skill-gap engine.
"""

from dataclasses import dataclass, field


@dataclass
class SkillNode:
    id: str
    label: str
    onet_element: str | None = None   # links back to an O*NET Element Name, if one exists
    prerequisites: list[str] = field(default_factory=list)   # ids of nodes required first
    source: str = "curated"


# Curated graph — deliberately starter-sized, grouped by the learning tracks
# most relevant to the datasets this project ingests (software/data/security).
SKILL_GRAPH: dict[str, SkillNode] = {
    "programming_fundamentals": SkillNode(
        id="programming_fundamentals", label="Programming Fundamentals",
        onet_element="Programming", prerequisites=[]),
    "python": SkillNode(
        id="python", label="Python", prerequisites=["programming_fundamentals"]),
    "data_structures_algorithms": SkillNode(
        id="data_structures_algorithms", label="Data Structures & Algorithms",
        prerequisites=["programming_fundamentals"]),
    "sql": SkillNode(
        id="sql", label="SQL", onet_element="Database and File Management",
        prerequisites=["programming_fundamentals"]),
    "numpy_pandas": SkillNode(
        id="numpy_pandas", label="NumPy & Pandas", prerequisites=["python"]),
    "statistics": SkillNode(
        id="statistics", label="Statistics", onet_element="Mathematics", prerequisites=[]),
    "data_visualization": SkillNode(
        id="data_visualization", label="Data Visualization", prerequisites=["numpy_pandas"]),
    "machine_learning": SkillNode(
        id="machine_learning", label="Machine Learning",
        prerequisites=["numpy_pandas", "statistics", "data_structures_algorithms"]),
    "deep_learning": SkillNode(
        id="deep_learning", label="Deep Learning", prerequisites=["machine_learning"]),
    "html_css": SkillNode(id="html_css", label="HTML & CSS", prerequisites=[]),
    "javascript": SkillNode(
        id="javascript", label="JavaScript", prerequisites=["html_css"]),
    "react": SkillNode(id="react", label="React", prerequisites=["javascript"]),
    "backend_apis": SkillNode(
        id="backend_apis", label="Backend APIs",
        onet_element="Computers and Electronics", prerequisites=["python", "sql"]),
    "git_version_control": SkillNode(
        id="git_version_control", label="Git & Version Control", prerequisites=[]),
    "networking_fundamentals": SkillNode(
        id="networking_fundamentals", label="Networking Fundamentals",
        onet_element="Telecommunications", prerequisites=[]),
    "operating_systems": SkillNode(
        id="operating_systems", label="Operating Systems", prerequisites=[]),
    "security_fundamentals": SkillNode(
        id="security_fundamentals", label="Security Fundamentals",
        prerequisites=["networking_fundamentals", "operating_systems"]),
    "threat_detection": SkillNode(
        id="threat_detection", label="Threat Detection & Analysis",
        prerequisites=["security_fundamentals"]),
    "cloud_fundamentals": SkillNode(
        id="cloud_fundamentals", label="Cloud Fundamentals",
        prerequisites=["networking_fundamentals", "operating_systems"]),
    "devops_cicd": SkillNode(
        id="devops_cicd", label="DevOps & CI/CD",
        prerequisites=["git_version_control", "cloud_fundamentals"]),
}


def get_prerequisite_chain(node_id: str) -> list[str]:
    """Full ordered prerequisite chain (topological) needed before node_id, node_id last."""
    visited: list[str] = []
    seen: set[str] = set()

    def visit(nid: str):
        if nid in seen or nid not in SKILL_GRAPH:
            return
        seen.add(nid)
        for prereq in SKILL_GRAPH[nid].prerequisites:
            visit(prereq)
        visited.append(nid)

    visit(node_id)
    return visited


def compute_states(node_id_targets: list[str], mastered_ids: set[str]) -> dict[str, str]:
    """
    States per Feature 11: "locked" | "available" | "currently_learning" | "mastered"
    for every node reachable as a prerequisite of the given target list.
    - mastered: in mastered_ids
    - available: not mastered, but all prerequisites ARE mastered
    - locked: not mastered, and at least one prerequisite is not mastered
    "currently_learning" is set by the roadmap/adaptive-path engine (Phase
    2 continues there) since it depends on what the learner is actively
    doing today, not on graph structure alone — left as "available" here.
    """
    all_nodes: set[str] = set()
    for t in node_id_targets:
        all_nodes.update(get_prerequisite_chain(t))

    states: dict[str, str] = {}
    for nid in all_nodes:
        if nid in mastered_ids:
            states[nid] = "mastered"
        else:
            prereqs = SKILL_GRAPH[nid].prerequisites
            states[nid] = "available" if all(p in mastered_ids for p in prereqs) else "locked"
    return states


if __name__ == "__main__":
    print("Prerequisite chain for 'deep_learning':")
    print("  " + " -> ".join(SKILL_GRAPH[n].label for n in get_prerequisite_chain("deep_learning")))

    print("\nPrerequisite chain for 'threat_detection':")
    print("  " + " -> ".join(SKILL_GRAPH[n].label for n in get_prerequisite_chain("threat_detection")))

    print("\nStates for a learner who has mastered programming_fundamentals + python only,")
    print("targeting machine_learning:")
    states = compute_states(["machine_learning"], mastered_ids={"programming_fundamentals", "python"})
    for nid, state in states.items():
        print(f"  {state:10s} {SKILL_GRAPH[nid].label}")
