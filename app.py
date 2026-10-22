"""RouteViz - Computer Networks course tool.
Run:  pip install flask  &&  python app.py   ->  http://127.0.0.1:5000
"""
import heapq
import os
from flask import Flask, jsonify, render_template, request

# Find index.html next to this file: in ./templates/ (standard) or in the same
# folder (if the templates folder was not kept when downloading).
BASE = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE, "templates")
if not os.path.exists(os.path.join(TEMPLATE_DIR, "index.html")):
    if os.path.exists(os.path.join(BASE, "index.html")):
        TEMPLATE_DIR = BASE
    else:
        raise SystemExit("index.html not found. Put it in a 'templates' folder next to app.py.")

app = Flask(__name__, template_folder=TEMPLATE_DIR)
INF = float("inf")


def num(x):
    """JSON-friendly number: None for infinity, int when whole."""
    if x is None or x == INF:
        return None
    return int(x) if float(x).is_integer() else x


def build_graph(nodes, links):
    g = {n: {} for n in nodes}
    for l in links:
        if l.get("failed"):  # failed link = removed from the graph before routing
            continue
        a, b, c = l["a"], l["b"], float(l["cost"])
        if a not in g or b not in g or a == b:
            continue
        if c <= 0:
            raise ValueError("Link costs must be positive.")
        g[a][b] = c
        g[b][a] = c
    return g


def follow(prev, dst):
    """Rebuild path from a predecessor map."""
    path, cur = [], dst
    while cur is not None:
        path.append(cur)
        cur = prev[cur]
    return path[::-1]


def dijkstra(g, src):
    dist = {n: INF for n in g}
    prev = {n: None for n in g}
    dist[src] = 0
    pq, done, order = [(0, src)], set(), []
    while pq:
        d, u = heapq.heappop(pq)
        if u in done:
            continue
        done.add(u)
        order.append({"node": u, "dist": num(d)})
        for v, w in g[u].items():
            if d + w < dist[v]:
                dist[v] = d + w
                prev[v] = u
                heapq.heappush(pq, (dist[v], v))
    return dist, prev, order


def dijkstra_table(g, src):
    dist, prev, order = dijkstra(g, src)
    rows = []
    for n in sorted(g):
        if n == src:
            continue
        if dist[n] == INF:
            rows.append({"dest": n, "next": "-", "cost": None})
        else:
            rows.append({"dest": n, "next": follow(prev, n)[1], "cost": num(dist[n])})
    return rows, dist, prev, order


def distance_vector(g):
    """Synchronous Bellman-Ford style exchange until no vector changes."""
    nodes = sorted(g)
    dv = {n: {d: (0 if d == n else INF) for d in nodes} for n in nodes}
    nh = {n: {d: None for d in nodes} for n in nodes}
    history = [{n: dict(dv[n]) for n in nodes}]
    while len(history) <= len(nodes):
        new = {n: dict(dv[n]) for n in nodes}
        new_nh = {n: dict(nh[n]) for n in nodes}
        changed = False
        for n in nodes:
            for nb, w in g[n].items():
                for d in nodes:
                    if dv[nb][d] + w < new[n][d]:
                        new[n][d] = dv[nb][d] + w
                        new_nh[n][d] = nb
                        changed = True
        if not changed:
            break
        dv, nh = new, new_nh
        history.append({n: dict(dv[n]) for n in nodes})
    return dv, nh, history


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/compute", methods=["POST"])
def compute():
    data = request.get_json(force=True)
    nodes, algo = data.get("nodes", []), data.get("algorithm")
    src, dst = data.get("source"), data.get("dest")
    if src not in nodes or dst not in nodes:
        return jsonify(error="Choose a valid source and destination."), 400
    try:
        g = build_graph(nodes, data.get("links", []))
    except (ValueError, KeyError, TypeError) as e:
        return jsonify(error=str(e)), 400

    if algo == "dijkstra":
        table, dist, prev, order = dijkstra_table(g, src)
        path = follow(prev, dst) if dist[dst] != INF else []
        return jsonify(algorithm=algo, table=table, path=path,
                       cost=num(dist[dst]), order=order)

    if algo == "dv":
        dv, nh, history = distance_vector(g)
        table = [{"dest": d, "next": nh[src][d] or "-", "cost": num(dv[src][d])}
                 for d in sorted(g) if d != src]
        path, cur = [src], src
        while cur != dst and len(path) <= len(nodes) and dv[src][dst] != INF:
            # follow each router's own next hop toward dst
            cur = nh[cur][dst]
            if cur is None:
                path = []
                break
            path.append(cur)
        if dv[src][dst] == INF or path[-1:] != [dst]:
            path = []
        rounds = [{d: num(h[src][d]) for d in sorted(g)} for h in history]
        return jsonify(algorithm=algo, table=table, path=path,
                       cost=num(dv[src][dst]), rounds=rounds,
                       exchanges=len(history) - 1)

    return jsonify(error="Unknown algorithm."), 400


@app.route("/api/compare", methods=["POST"])
def compare():
    """Run both Dijkstra and Distance Vector on the same graph snapshot."""
    data = request.get_json(force=True)
    nodes = data.get("nodes", [])
    src, dst = data.get("source"), data.get("dest")
    if src not in nodes or dst not in nodes:
        return jsonify(error="Choose a valid source and destination."), 400
    try:
        g = build_graph(nodes, data.get("links", []))
    except (ValueError, KeyError, TypeError) as e:
        return jsonify(error=str(e)), 400

    # --- Dijkstra ---
    d_table, d_dist, d_prev, d_order = dijkstra_table(g, src)
    d_path = follow(d_prev, dst) if d_dist[dst] != INF else []
    dijkstra_result = {
        "path": d_path,
        "cost": num(d_dist[dst]),
        "hops": len(d_path) - 1 if d_path else None,
        "next_hop": d_path[1] if len(d_path) > 1 else None,
        "reachable": d_dist[dst] != INF,
        "iterations": len(d_order),
    }

    # --- Distance Vector ---
    dv, nh, history = distance_vector(g)
    dv_path, cur = [src], src
    while cur != dst and len(dv_path) <= len(nodes) and dv[src][dst] != INF:
        cur = nh[cur][dst]
        if cur is None:
            dv_path = []
            break
        dv_path.append(cur)
    if dv[src][dst] == INF or dv_path[-1:] != [dst]:
        dv_path = []
    dv_result = {
        "path": dv_path,
        "cost": num(dv[src][dst]),
        "hops": len(dv_path) - 1 if dv_path else None,
        "next_hop": dv_path[1] if len(dv_path) > 1 else None,
        "reachable": dv[src][dst] != INF,
        "exchanges": len(history) - 1,
    }

    return jsonify(dijkstra=dijkstra_result, dv=dv_result)


if __name__ == "__main__":
    app.run(debug=True)