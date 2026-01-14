#!/usr/bin/env python3
import json
import os
import sys
from pathlib import Path
from PIL import Image

# usage: python3 trace_to_graphviz_clusters.py trace.jsonl /path/to/output_dir
trace_file = sys.argv[1]
out_dir = Path(sys.argv[2])
out_dir.mkdir(parents=True, exist_ok=True)

# --- load traces ---
trace = []
with open(trace_file) as f:
    for line in f:
        t = json.loads(line)
        trace.append(
            {
                "prev": t.get("hash_previous"),
                "curr": t.get("hash_current"),
                "screenshot": t.get("screenshot_path"),
                "action": t.get("action", None),
            }
        )


# --- Hamming clustering ---
def hamming(a, b):
    return bin(a ^ b).count("1")


THRESHOLD = 8
all_hashes = {t["prev"] for t in trace if t["prev"] is not None} | {
    t["curr"] for t in trace if t["curr"] is not None
}

clusters = []
hash_to_cluster = {}

for h in all_hashes:
    assigned = False
    for ci, cluster in enumerate(clusters):
        if hamming(h, cluster[0]) <= THRESHOLD:
            cluster.append(h)
            hash_to_cluster[h] = ci
            assigned = True
            break
    if not assigned:
        clusters.append([h])
        hash_to_cluster[h] = len(clusters) - 1

# --- track earliest screenshot occurrence per hash ---
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

# --- choose earliest screenshot per cluster ---
cluster_screenshots = {}
for ci, cluster in enumerate(clusters):
    earliest = None
    for h in cluster:
        info = hash_screenshot_info.get(h)
        if not info:
            continue
        if earliest is None or info["idx"] < earliest["idx"]:
            earliest = info
    cluster_screenshots[ci] = earliest["screenshot"] if earliest else None

# --- convert WebP screenshots to PNG ---
for ci, screenshot in cluster_screenshots.items():
    if screenshot is None:
        cluster_screenshots[ci] = None
        continue
    img_path = Path(screenshot)
    out_png = out_dir / f"cluster_{ci}.png"
    if img_path.suffix.lower() == ".webp":
        Image.open(img_path).convert("RGBA").save(out_png, "PNG")
    else:
        out_png.write_bytes(img_path.read_bytes())
    cluster_screenshots[ci] = str(out_png.resolve()).replace("\\", "/")


def summarize_action(action: dict) -> str:
    """
    Convert a Rust-style BrowserAction dict to a short string.
    """
    if not action:
        return "?"

    variant = next(iter(action.keys()))
    data = action[variant]

    if variant == "Back":
        return "Back"
    elif variant == "Click":
        name = data.get("name", "?")
        content = data.get("content")
        return f"Click({name}:{content})" if content else f"Click({name})"
    elif variant == "TypeText":
        text = data.get("text", "")
        return f'Type("{text}")'
    elif variant == "PressKey":
        return f"Key({data.get('code')})"
    elif variant == "ScrollUp":
        return "ScrollUp"
    elif variant == "ScrollDown":
        return "ScrollDown"
    elif variant == "Reload":
        return "Reload"
    else:
        return variant


# --- deduplicate edges at cluster level ---
edge_set = set()
last_hash = None
for t in trace:
    prev_hash = t["prev"] or last_hash
    curr_hash = t["curr"]
    if prev_hash is None or curr_hash is None:
        last_hash = curr_hash or prev_hash
        continue
    action = summarize_action(t.get("action"))
    ci = hash_to_cluster[prev_hash]
    cj = hash_to_cluster[curr_hash]
    edge_set.add((ci, cj, action))
    last_hash = curr_hash

# --- generate DOT file ---
dot_path = out_dir / "graph.dot"
with open(dot_path, "w") as f:
    f.write("digraph G {\n")
    f.write("  node [shape=none, labelloc=b, fontsize=48];\n")
    f.write("  edge [splines=curved, fontsize=32];\n")

    for ci, cluster in enumerate(clusters):
        cluster_size = len(cluster)
        label = f"Cluster {ci} ({cluster_size})"
        png = cluster_screenshots.get(ci)
        if png:
            f.write(f'  "{ci}" [label="{label}", image="{png}"];\n')
        else:
            f.write(f'  "{ci}" [label="{label}"];\n')

    for ci, cj, action in edge_set:
        if ci == cj:
            continue
        label = action.replace('"', '\\"') if action else ""
        f.write(f'  "{ci}" -> "{cj}" [label="{label}"];\n')

    f.write("}\n")

print(f"DOT graph written to {dot_path}")

# --- render SVG ---
svg_path = out_dir / "graph.svg"
os.system(f'fdp -Tsvg "{dot_path}" -Gsize="20,20!" -Gdpi=100 -o "{svg_path}"')
print(f"SVG graph written to {svg_path}")
