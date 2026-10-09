# RouteViz

**Interactive Computer Networks Routing Simulator** built with Flask (Python) and a lightweight HTML/CSS/JavaScript front end.

Build a network of routers and weighted links, run a routing algorithm, read the routing table, send a packet along the computed route and fail a link to watch the route being recalculated.

## Features

- Create routers and links with costs, drag routers to rearrange the topology
- **Dijkstra (link state)** with the order in which routers are finalized
- **Distance Vector** with the vector of the source router shown for every round until it converges
- Routing table with next hop and cost, and the selected destination highlighted
- **Send packet:** an animated packet follows the calculated route hop by hop
- **Link failure:** mark a link as failed, and the route and routing table are recomputed without it
- Packet status and network status panels

## How it works

The browser sends the topology (routers, links, failed links) to the Flask API, which builds a graph that skips failed links and runs the selected algorithm. The returned path, routing table and algorithm steps drive the visualization and the packet animation, so every result comes from the real algorithm.

## Project structure

```
routeviz/
├── app.py              # Flask app, Dijkstra and Distance Vector
├── requirements.txt
├── templates/
│   └── index.html      # Page and JavaScript
└── static/
    └── style.css       # Styling
```

## Run locally

```bash
git clone https://github.com/your-username/routeviz.git
cd routeviz
pip install -r requirements.txt
python app.py
```

Then open http://127.0.0.1:5000 in your browser.

## Usage

1. Click **Load sample** (or add routers and links yourself).
2. Choose the algorithm, source and destination, then click **Find shortest path**.
3. Click **Send packet** to watch it travel along the route.
4. Pick a link and click **Simulate link failure** to see the route recalculated.

## Tech stack

Python, Flask, HTML, CSS, JavaScript (SVG)

## Author

Vanshika, Computer Networks course project
