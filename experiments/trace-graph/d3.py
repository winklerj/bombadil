#!/usr/bin/env python3
import json
import sys
from pathlib import Path
from PIL import Image

# usage: python3 trace_to_d3_graph.py trace.jsonl /path/to/output_dir
trace_file = sys.argv[1]
out_dir = Path(sys.argv[2])
img_dir = out_dir / "images"
out_dir.mkdir(parents=True, exist_ok=True)
img_dir.mkdir(parents=True, exist_ok=True)

# ---------- load trace ----------
trace = []
with open(trace_file) as f:
    for line in f:
        t = json.loads(line)
        trace.append(
            {
                "prev": t.get("hash_previous"),
                "curr": t.get("hash_current"),
                "screenshot": t.get("screenshot_path"),
                "action": t.get("action"),
            }
        )


# ---------- hamming clustering ----------
def hamming(a, b):
    return bin(a ^ b).count("1")


THRESHOLD = 8
all_hashes = {t["prev"] for t in trace if t["prev"] is not None} | {
    t["curr"] for t in trace if t["curr"] is not None
}

clusters = []
hash_to_cluster = {}

for h in all_hashes:
    for ci, cluster in enumerate(clusters):
        if hamming(h, cluster[0]) <= THRESHOLD:
            cluster.append(h)
            hash_to_cluster[h] = ci
            break
    else:
        clusters.append([h])
        hash_to_cluster[h] = len(clusters) - 1

# ---------- earliest screenshot per hash ----------
hash_screenshot_info = {}
for idx, t in enumerate(trace):
    screenshot = t.get("screenshot")
    if not screenshot:
        continue
    for h in (t["prev"], t["curr"]):
        if h is None:
            continue
        if h not in hash_screenshot_info or idx < hash_screenshot_info[h]["idx"]:
            hash_screenshot_info[h] = {
                "idx": idx,
                "screenshot": screenshot,
            }

# ---------- earliest screenshot per cluster ----------
cluster_images = {}
for ci, cluster in enumerate(clusters):
    earliest = None
    for h in cluster:
        info = hash_screenshot_info.get(h)
        if not info:
            continue
        if earliest is None or info["idx"] < earliest["idx"]:
            earliest = info
    cluster_images[ci] = earliest["screenshot"] if earliest else None

# ---------- copy/convert images ----------
for ci, screenshot in cluster_images.items():
    if not screenshot:
        continue
    src = Path(screenshot)
    dst = img_dir / f"cluster_{ci}.png"
    if src.suffix.lower() == ".webp":
        Image.open(src).convert("RGBA").save(dst, "PNG")
    else:
        dst.write_bytes(src.read_bytes())
    cluster_images[ci] = f"images/{dst.name}"


# ---------- summarize actions ----------
def summarize_action(action):
    if not action:
        return "?"
    variant = next(iter(action.keys()))
    data = action[variant]
    if variant == "Click":
        name = data.get("name", "?")
        content = data.get("content")
        return f"Click({name}:{content})" if content else f"Click({name})"
    if variant == "TypeText":
        return f'Type("{data.get("text","")}")'
    if variant == "PressKey":
        return f"Key({data.get('code')})"
    return variant


# ---------- edges ----------
edges = set()
last_hash = None
for t in trace:
    prev_hash = t["prev"] or last_hash
    curr_hash = t["curr"]
    if prev_hash is None or curr_hash is None:
        last_hash = curr_hash or prev_hash
        continue
    edges.add(
        (
            hash_to_cluster[prev_hash],
            hash_to_cluster[curr_hash],
            summarize_action(t.get("action")),
        )
    )
    last_hash = curr_hash

# ---------- build graph JSON ----------
nodes = [
    {
        "id": ci,
        "label": f"Cluster {ci} ({len(cluster)})",
        "image": cluster_images.get(ci),
    }
    for ci, cluster in enumerate(clusters)
]

links = [
    {"source": ci, "target": cj, "label": action}
    for ci, cj, action in edges
    if ci != cj
]

graph = {"nodes": nodes, "links": links}

# ---------- write index.html ----------
html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8" />
<title>State Transition Graph</title>
<script src="https://d3js.org/d3.v7.min.js"></script>
<style>
html, body {{
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
  font-family: sans-serif;
}}
svg {{
  width: 100vw;
  height: 100vh;
  background: #111;
}}
.node image {{
  pointer-events: none;
}}
.node text {{
  fill: white;
  font-size: 12px;
  text-anchor: middle;
}}
.link {{
  stroke: #888;
  stroke-width: 2px;
}}
.link-label {{
  fill: #ccc;
  font-size: 11px;
  pointer-events: none;
}}
</style>
</head>
<body>
<svg></svg>
<script>
const graph = {json.dumps(graph)};

const svg = d3.select("svg");
const g = svg.append("g");

svg.call(
  d3.zoom().scaleExtent([0.1, 4]).on("zoom", (event) => {{
    g.attr("transform", event.transform);
  }})
);

const simulation = d3.forceSimulation(graph.nodes)
  .force("link", d3.forceLink(graph.links).id(d => d.id).distance(250))
  .force("charge", d3.forceManyBody().strength(-600))
  .force("center", d3.forceCenter(window.innerWidth / 2, window.innerHeight / 2))
  .force("collision", d3.forceCollide(80));

const link = g.append("g")
  .selectAll(".link")
  .data(graph.links)
  .enter()
  .append("line")
  .attr("class", "link");

const linkLabel = g.append("g")
  .selectAll(".link-label")
  .data(graph.links)
  .enter()
  .append("text")
  .attr("class", "link-label")
  .text(d => d.label);

const node = g.append("g")
  .selectAll(".node")
  .data(graph.nodes)
  .enter()
  .append("g")
  .attr("class", "node")
  .call(
    d3.drag()
      .on("start", dragstarted)
      .on("drag", dragged)
      .on("end", dragended)
  );

node.append("image")
  .attr("href", d => d.image || "")
  .attr("width", 120)
  .attr("height", 80)
  .attr("x", -60)
  .attr("y", -40);

node.append("text")
  .attr("y", 55)
  .text(d => d.label);

simulation.on("tick", () => {{
  link
    .attr("x1", d => d.source.x)
    .attr("y1", d => d.source.y)
    .attr("x2", d => d.target.x)
    .attr("y2", d => d.target.y);

  linkLabel
    .attr("x", d => (d.source.x + d.target.x) / 2)
    .attr("y", d => (d.source.y + d.target.y) / 2);

  node.attr("transform", d => `translate(${{d.x}}, ${{d.y}})`);
}});

function dragstarted(event) {{
  if (!event.active) simulation.alphaTarget(0.3).restart();
  event.subject.fx = event.subject.x;
  event.subject.fy = event.subject.y;
}}

function dragged(event) {{
  event.subject.fx = event.x;
  event.subject.fy = event.y;
}}

function dragended(event) {{
  if (!event.active) simulation.alphaTarget(0);
  event.subject.fx = null;
  event.subject.fy = null;
}}
</script>
</body>
</html>
"""

(out_dir / "index.html").write_text(html, encoding="utf-8")

print(f"Output written to {out_dir}")
print("Open index.html in a browser")
