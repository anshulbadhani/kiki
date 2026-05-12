"""
Skill: show_skills
Generates an interactive skill graph and opens it in the browser.
Uses networkx + pyvis. Zero extra deps beyond what's already installed
if pyvis is added — otherwise falls back to a plain HTML table.
"""
from __future__ import annotations
import json
import tempfile
import webbrowser
from pathlib import Path

NAME        = "show_skills"
DESCRIPTION = "show visualise graph skills capabilities what can you do map"
EXAMPLES    = [
    "show your skills",
    "skill graph",
    "what can you do",
    "show me your capabilities",
    "visualise skills",
    "map of skills",
    "show skill map",
    "what skills do you have",
    "show all skills",
    "capabilities graph",
]
PARAMETERS      = {}
REQUIRES_VISION = False


# ---------------------------------------------------------------------------
# Graph data builder
# ---------------------------------------------------------------------------

def _build_graph_data(registry) -> dict:
    """
    Build nodes and edges from the registry.
    Groups skills by rough category based on name keywords.
    """
    skills = registry.all_skills()

    categories = {
        "system":  ["open_app", "notify", "clipboard"],
        "vision":  ["screenshot"],
        "web":     ["web_search"],
        "kiki":    ["help", "show_skills"],
    }

    # reverse map: skill_name → category
    skill_cat = {}
    for cat, names in categories.items():
        for name in names:
            skill_cat[name] = cat

    cat_colors = {
        "system": "#3a7bd5",
        "vision": "#0f6e56",
        "web":    "#8a4af3",
        "kiki":   "#185FA5",
        "other":  "#5F5E5A",
    }

    nodes = []

    # category hub nodes
    seen_cats = set()
    for skill in skills:
        cat = skill_cat.get(skill.name, "other")
        if cat not in seen_cats:
            nodes.append({
                "id":    f"cat_{cat}",
                "label": cat,
                "type":  "category",
                "color": cat_colors.get(cat, cat_colors["other"]),
                "size":  28,
            })
            seen_cats.add(cat)

    # skill nodes
    for skill in skills:
        cat = skill_cat.get(skill.name, "other")
        nodes.append({
            "id":       skill.name,
            "label":    skill.name,
            "type":     "skill",
            "color":    cat_colors.get(cat, cat_colors["other"]),
            "size":     18,
            "examples": skill.examples[:3],
            "desc":     skill.description,
        })

    # edges: category hub → skill
    edges = []
    for skill in skills:
        cat = skill_cat.get(skill.name, "other")
        edges.append({
            "from": f"cat_{cat}",
            "to":   skill.name,
        })

    return {"nodes": nodes, "edges": edges}


# ---------------------------------------------------------------------------
# HTML generator
# ---------------------------------------------------------------------------

def _generate_html(graph_data: dict) -> str:
    nodes_json = json.dumps(graph_data["nodes"])
    edges_json = json.dumps(graph_data["edges"])

    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>kiki — skill map</title>
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{
    background: #0d0d0d;
    color: #ccc;
    font-family: Consolas, monospace;
    overflow: hidden;
  }}
  #header {{
    position: fixed;
    top: 16px; left: 20px;
    font-size: 13px;
    color: #444;
    z-index: 10;
  }}
  #header span {{ color: #185FA5; }}
  #tooltip {{
    position: fixed;
    background: #111;
    border: 0.5px solid #2a2a2a;
    border-radius: 8px;
    padding: 10px 14px;
    font-size: 12px;
    color: #ccc;
    pointer-events: none;
    display: none;
    max-width: 240px;
    line-height: 1.6;
    z-index: 100;
  }}
  #tooltip .t-name {{ color: #fff; font-size: 13px; margin-bottom: 4px; }}
  #tooltip .t-dim  {{ color: #555; font-size: 11px; }}
  canvas {{ display: block; }}
</style>
</head>
<body>
<div id="header"><span>kiki</span> — skill map</div>
<div id="tooltip">
  <div class="t-name" id="tt-name"></div>
  <div id="tt-desc"></div>
  <div class="t-dim" id="tt-examples"></div>
</div>
<canvas id="c"></canvas>

<script>
const NODES = {nodes_json};
const EDGES = {edges_json};

const canvas  = document.getElementById("c");
const ctx     = canvas.getContext("2d");
const tooltip = document.getElementById("tooltip");

let W, H, nodeMap = {{}};
let dragging = null, dragOffX = 0, dragOffY = 0;
let hovering = null;

function resize() {{
  W = canvas.width  = window.innerWidth;
  H = canvas.height = window.innerHeight;
  layout();
  draw();
}}

function layout() {{
  // place category hubs in a circle, skills around their hub
  const cats    = NODES.filter(n => n.type === "category");
  const catR    = Math.min(W, H) * 0.28;
  const centerX = W / 2, centerY = H / 2;

  cats.forEach((cat, i) => {{
    const angle = (i / cats.length) * Math.PI * 2 - Math.PI / 2;
    if (!nodeMap[cat.id]) {{
      nodeMap[cat.id] = {{
        ...cat,
        x: centerX + Math.cos(angle) * catR,
        y: centerY + Math.sin(angle) * catR,
        vx: 0, vy: 0,
      }};
    }}
  }});

  const skillsByCat = {{}};
  EDGES.forEach(e => {{
    if (!skillsByCat[e.from]) skillsByCat[e.from] = [];
    skillsByCat[e.from].push(e.to);
  }});

  Object.entries(skillsByCat).forEach(([catId, skillIds]) => {{
    const hub = nodeMap[catId];
    skillIds.forEach((sid, i) => {{
      const angle = (i / skillIds.length) * Math.PI * 2;
      const r     = 110;
      if (!nodeMap[sid]) {{
        const skill = NODES.find(n => n.id === sid);
        nodeMap[sid] = {{
          ...skill,
          x: hub.x + Math.cos(angle) * r,
          y: hub.y + Math.sin(angle) * r,
          vx: 0, vy: 0,
        }};
      }}
    }});
  }});
}}

function draw() {{
  ctx.clearRect(0, 0, W, H);

  // edges
  EDGES.forEach(e => {{
    const a = nodeMap[e.from], b = nodeMap[e.to];
    if (!a || !b) return;
    ctx.beginPath();
    ctx.moveTo(a.x, a.y);
    ctx.lineTo(b.x, b.y);
    ctx.strokeStyle = "#1e1e1e";
    ctx.lineWidth   = 1.5;
    ctx.stroke();
  }});

  // nodes
  Object.values(nodeMap).forEach(n => {{
    const isHovered = hovering === n.id;
    const r         = n.size + (isHovered ? 4 : 0);

    // glow
    if (isHovered) {{
      const g = ctx.createRadialGradient(n.x, n.y, r, n.x, n.y, r * 2.5);
      g.addColorStop(0, n.color + "44");
      g.addColorStop(1, "transparent");
      ctx.beginPath();
      ctx.arc(n.x, n.y, r * 2.5, 0, Math.PI * 2);
      ctx.fillStyle = g;
      ctx.fill();
    }}

    // circle
    const grad = ctx.createRadialGradient(
      n.x - r * 0.3, n.y - r * 0.3, r * 0.1,
      n.x, n.y, r
    );
    grad.addColorStop(0, "#ffffff22");
    grad.addColorStop(0.4, n.color);
    grad.addColorStop(1, n.color + "aa");
    ctx.beginPath();
    ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
    ctx.fillStyle   = grad;
    ctx.fill();

    // label
    ctx.fillStyle   = n.type === "category" ? "#fff" : "#bbb";
    ctx.font        = n.type === "category"
                      ? "bold 11px Consolas, monospace"
                      : "10px Consolas, monospace";
    ctx.textAlign   = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(n.label, n.x, n.y + r + 14);
  }});
}}

// interaction
canvas.addEventListener("mousemove", e => {{
  const mx = e.clientX, my = e.clientY;

  if (dragging) {{
    nodeMap[dragging].x = mx + dragOffX;
    nodeMap[dragging].y = my + dragOffY;
    draw();
    return;
  }}

  hovering = null;
  for (const [id, n] of Object.entries(nodeMap)) {{
    const dx = mx - n.x, dy = my - n.y;
    if (Math.sqrt(dx*dx + dy*dy) < n.size + 6) {{
      hovering = id;
      canvas.style.cursor = "pointer";

      document.getElementById("tt-name").textContent     = n.label;
      document.getElementById("tt-desc").textContent     = n.desc || "";
      document.getElementById("tt-examples").textContent =
        n.examples ? "e.g. " + n.examples.join(" · ") : "";

      tooltip.style.display = "block";
      tooltip.style.left    = (mx + 16) + "px";
      tooltip.style.top     = (my - 10) + "px";
      draw();
      return;
    }}
  }}

  canvas.style.cursor   = "default";
  tooltip.style.display = "none";
  if (hovering !== null) {{ hovering = null; draw(); }}
}});

canvas.addEventListener("mousedown", e => {{
  for (const [id, n] of Object.entries(nodeMap)) {{
    const dx = e.clientX - n.x, dy = e.clientY - n.y;
    if (Math.sqrt(dx*dx + dy*dy) < n.size + 6) {{
      dragging = id;
      dragOffX = n.x - e.clientX;
      dragOffY = n.y - e.clientY;
      return;
    }}
  }}
}});

canvas.addEventListener("mouseup",    () => {{ dragging = null; }});
canvas.addEventListener("mouseleave", () => {{ dragging = null; }});
window.addEventListener("resize",     resize);

resize();
</script>
</body>
</html>"""


# ---------------------------------------------------------------------------
# Run
# ---------------------------------------------------------------------------

def run(**kwargs) -> str:
    registry = kwargs.get("registry")
    if registry is None:
        return "registry unavailable — can't build skill graph."

    graph_data = _build_graph_data(registry)

    html = _generate_html(graph_data)

    tmp = tempfile.NamedTemporaryFile(
        suffix=".html",
        delete=False,
        mode="w",
        encoding="utf-8",
    )
    tmp.write(html)
    tmp.close()

    webbrowser.open(f"file://{tmp.name}")
    return "skill map opened in your browser."


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    class _StubSkill:
        def __init__(self, name, examples):
            self.name        = name
            self.examples    = examples
            self.description = f"{name} skill"

    class _StubRegistry:
        def all_skills(self):
            return [
                _StubSkill("open_app",   ["open chrome", "launch spotify"]),
                _StubSkill("web_search", ["search for recipes"]),
                _StubSkill("clipboard",  ["read my clipboard"]),
                _StubSkill("screenshot", ["what is on my screen"]),
                _StubSkill("notify",     ["remind me to drink water"]),
                _StubSkill("help",       ["help", "what can you do"]),
                _StubSkill("show_skills",["show skill graph"]),
            ]

    print("generating skill graph...")
    result = run(registry=_StubRegistry())
    assert "browser" in result, f"unexpected: {result}"
    print(f"result: {result}")
    print("show_skills.py — all tests passed.")