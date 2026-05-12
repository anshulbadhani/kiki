from __future__ import annotations
import json
import tempfile
import webbrowser
import hashlib
from dataclasses import dataclass, field

from .base import Skill


def _category_color(category: str) -> str:
    """Deterministically derive a muted hex color from a category name."""
    h = int(hashlib.md5(category.encode()).hexdigest()[:6], 16)
    # extract HSL-like values — keep saturation/lightness in a pleasant range
    hue   = h % 360
    return _hsl_to_hex(hue, 45, 38)


def _hsl_to_hex(h: int, s: int, l: int) -> str:
    s /= 100
    l /= 100
    c = (1 - abs(2 * l - 1)) * s
    x = c * (1 - abs((h / 60) % 2 - 1))
    m = l - c / 2
    if   h < 60:  r, g, b = c, x, 0
    elif h < 120: r, g, b = x, c, 0
    elif h < 180: r, g, b = 0, c, x
    elif h < 240: r, g, b = 0, x, c
    elif h < 300: r, g, b = x, 0, c
    else:         r, g, b = c, 0, x
    r = int((r + m) * 255)
    g = int((g + m) * 255)
    b = int((b + m) * 255)
    return f"#{r:02x}{g:02x}{b:02x}"


@dataclass
class ShowSkillsSkill(Skill):
    name:        str       = "show_skills"
    description: str       = "show visualise graph skills capabilities what can you do map"
    examples:    list[str] = field(default_factory=lambda: [
        "show your skills",
        "skill graph",
        "what can you do",
        "show me your capabilities",
        "visualise skills",
        "map of skills",
        "show skill map",
        "show all skills",
        "capabilities graph",
    ])
    category:   str  = "kiki"
    parameters: dict = field(default_factory=dict)

    def run(self, **kwargs) -> str:
        registry = kwargs.get("registry")
        if registry is None:
            return "registry unavailable — can't build skill graph."
        graph_data = self._build_graph_data(registry)
        html       = self._generate_html(graph_data)

        tmp = tempfile.NamedTemporaryFile(
            suffix=".html", delete=False, mode="w", encoding="utf-8"
        )
        tmp.write(html)
        tmp.close()

        webbrowser.open(f"file://{tmp.name}")
        return "skill map opened in your browser."

    # -----------------------------------------------------------------------
    # Graph builder — fully dynamic, no hardcoded categories
    # -----------------------------------------------------------------------

    def _build_graph_data(self, registry) -> dict:
        skills = registry.all_skills()

        # collect unique categories directly from skills
        categories = {skill.category for skill in skills}

        nodes = []

        # category hub nodes
        for cat in categories:
            nodes.append({
                "id":    f"cat_{cat}",
                "label": cat,
                "type":  "category",
                "color": _category_color(cat),
                "size":  28,
            })

        # skill nodes
        for skill in skills:
            nodes.append({
                "id":       skill.name,
                "label":    skill.name,
                "type":     "skill",
                "color":    _category_color(skill.category),
                "size":     18,
                "examples": skill.examples[:3],
                "desc":     skill.description,
            })

        # edges: category hub → skill
        edges = [
            {"from": f"cat_{skill.category}", "to": skill.name}
            for skill in skills
        ]

        return {"nodes": nodes, "edges": edges}

    # -----------------------------------------------------------------------
    # HTML — unchanged from original
    # -----------------------------------------------------------------------

    def _generate_html(self, graph_data: dict) -> str:
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

  Object.values(nodeMap).forEach(n => {{
    const isHovered = hovering === n.id;
    const r         = n.size + (isHovered ? 4 : 0);

    if (isHovered) {{
      const g = ctx.createRadialGradient(n.x, n.y, r, n.x, n.y, r * 2.5);
      g.addColorStop(0, n.color + "44");
      g.addColorStop(1, "transparent");
      ctx.beginPath();
      ctx.arc(n.x, n.y, r * 2.5, 0, Math.PI * 2);
      ctx.fillStyle = g;
      ctx.fill();
    }}

    const grad = ctx.createRadialGradient(
      n.x - r * 0.3, n.y - r * 0.3, r * 0.1,
      n.x, n.y, r
    );
    grad.addColorStop(0, "#ffffff22");
    grad.addColorStop(0.4, n.color);
    grad.addColorStop(1, n.color + "aa");
    ctx.beginPath();
    ctx.arc(n.x, n.y, r, 0, Math.PI * 2);
    ctx.fillStyle = grad;
    ctx.fill();

    ctx.fillStyle    = n.type === "category" ? "#fff" : "#bbb";
    ctx.font         = n.type === "category"
                       ? "bold 11px Consolas, monospace"
                       : "10px Consolas, monospace";
    ctx.textAlign    = "center";
    ctx.textBaseline = "middle";
    ctx.fillText(n.label, n.x, n.y + r + 14);
  }});
}}

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
# Tests
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    class _StubSkill:
        def __init__(self, name, category, examples):
            self.name        = name
            self.category    = category
            self.examples    = examples
            self.description = f"{name} skill"

    class _StubRegistry:
        def all_skills(self):
            return [
                _StubSkill("open_app",    "system", ["open chrome"]),
                _StubSkill("web_search",  "web",    ["search for recipes"]),
                _StubSkill("clipboard",   "system", ["read my clipboard"]),
                _StubSkill("notify",      "system", ["remind me to drink water"]),
                _StubSkill("help",        "kiki",   ["help"]),
                _StubSkill("show_skills", "kiki",   ["show skill graph"]),
                _StubSkill("my_skill",    "custom", ["do the thing"]),  # new category
            ]

    result = ShowSkillsSkill().run(registry=_StubRegistry())
    assert "browser" in result, f"unexpected: {result}"

    # verify colors are derived, not hardcoded
    assert _category_color("custom") != _category_color("system")
    assert _category_color("system") == _category_color("system")  # deterministic

    print(f"system color : {_category_color('system')}")
    print(f"web color    : {_category_color('web')}")
    print(f"custom color : {_category_color('custom')}")
    print("show_skills.py — all tests passed.")