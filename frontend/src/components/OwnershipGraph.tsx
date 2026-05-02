import { useEffect, useRef, useState } from "react";
import * as d3 from "d3";
import { api } from "../lib/api";
import type { OwnershipNetwork } from "../lib/types";

interface Props {
  imo: string;
}

interface SimNode extends d3.SimulationNodeDatum {
  id: string;
  label: string;
  kind: "vessel" | "owner" | "sanctioned_vessel";
  sanctioned: boolean;
}

interface SimEdge extends d3.SimulationLinkDatum<SimNode> {
  source: string | SimNode;
  target: string | SimNode;
  relation: string;
}

const KIND_COLOR: Record<SimNode["kind"], string> = {
  vessel: "#22d3ee",
  owner: "#94a3b8",
  sanctioned_vessel: "#ef4444",
};

const KIND_RADIUS: Record<SimNode["kind"], number> = {
  vessel: 11,
  owner: 9,
  sanctioned_vessel: 13,
};

export default function OwnershipGraph({ imo }: Props) {
  const [network, setNetwork] = useState<OwnershipNetwork | null>(null);
  const [error, setError] = useState<string | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const wrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    setNetwork(null);
    setError(null);
    api.getNetwork(imo, 3).then(setNetwork).catch((e) => setError(String(e)));
  }, [imo]);

  useEffect(() => {
    if (!network || !svgRef.current || !wrapRef.current) return;

    const width = wrapRef.current.clientWidth;
    const height = 360;

    const nodes: SimNode[] = network.nodes.map((n) => ({ ...n }));
    const edges: SimEdge[] = network.edges.map((e) => ({ ...e }));

    const svg = d3
      .select(svgRef.current)
      .attr("viewBox", `0 0 ${width} ${height}`)
      .attr("width", width)
      .attr("height", height);
    svg.selectAll("*").remove();

    const defs = svg.append("defs");
    defs
      .append("marker")
      .attr("id", "arrow")
      .attr("viewBox", "0 -4 8 8")
      .attr("refX", 14)
      .attr("refY", 0)
      .attr("markerWidth", 8)
      .attr("markerHeight", 8)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-4L8,0L0,4")
      .attr("fill", "#475569");

    const link = svg
      .append("g")
      .attr("stroke-opacity", 0.5)
      .selectAll("line")
      .data(edges)
      .join("line")
      .attr("stroke", (d) => (d.relation === "linked_to_sanctioned" ? "#ef4444" : "#475569"))
      .attr("stroke-width", (d) => (d.relation === "linked_to_sanctioned" ? 1.6 : 1))
      .attr("stroke-dasharray", (d) => (d.relation === "linked_to_sanctioned" ? "4 3" : null))
      .attr("marker-end", "url(#arrow)");

    const nodeG = svg
      .append("g")
      .selectAll<SVGGElement, SimNode>("g")
      .data(nodes)
      .join("g")
      .style("cursor", "grab");

    const drag = d3
      .drag<SVGGElement, SimNode>()
      .on("start", (event, d) => {
        if (!event.active) sim.alphaTarget(0.3).restart();
        d.fx = d.x;
        d.fy = d.y;
      })
      .on("drag", (event, d) => {
        d.fx = event.x;
        d.fy = event.y;
      })
      .on("end", (event, d) => {
        if (!event.active) sim.alphaTarget(0);
        d.fx = null;
        d.fy = null;
      });
    nodeG.call(drag);

    nodeG
      .append("circle")
      .attr("r", (d) => KIND_RADIUS[d.kind])
      .attr("fill", (d) => KIND_COLOR[d.kind])
      .attr("fill-opacity", 0.18)
      .attr("stroke", (d) => KIND_COLOR[d.kind])
      .attr("stroke-width", 1.5);

    nodeG
      .filter((d) => d.kind === "sanctioned_vessel" || d.sanctioned)
      .append("circle")
      .attr("r", (d) => KIND_RADIUS[d.kind] + 4)
      .attr("fill", "none")
      .attr("stroke", "#ef4444")
      .attr("stroke-opacity", 0.5)
      .attr("stroke-dasharray", "3 2");

    nodeG
      .append("text")
      .attr("x", 0)
      .attr("y", (d) => KIND_RADIUS[d.kind] + 14)
      .attr("text-anchor", "middle")
      .attr("fill", "#cbd5e1")
      .attr("font-size", 10)
      .attr("font-family", "ui-sans-serif, system-ui, sans-serif")
      .text((d) => (d.label.length > 22 ? d.label.slice(0, 21) + "…" : d.label));

    nodeG.append("title").text((d) => `${d.label} (${d.kind})`);

    const sim = d3
      .forceSimulation(nodes)
      .force(
        "link",
        d3
          .forceLink<SimNode, SimEdge>(edges)
          .id((d) => d.id)
          .distance(80)
          .strength(0.7),
      )
      .force("charge", d3.forceManyBody().strength(-220))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collide", d3.forceCollide<SimNode>().radius((d) => KIND_RADIUS[d.kind] + 18));

    sim.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as SimNode).x ?? 0)
        .attr("y1", (d) => (d.source as SimNode).y ?? 0)
        .attr("x2", (d) => (d.target as SimNode).x ?? 0)
        .attr("y2", (d) => (d.target as SimNode).y ?? 0);
      nodeG.attr("transform", (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

    return () => {
      sim.stop();
    };
  }, [network]);

  if (error) return <p className="text-xs text-rose-400">error: {error}</p>;
  if (!network) return <p className="text-xs text-slate-500">loading network…</p>;

  return (
    <section>
      <h2 className="mb-1 text-xs uppercase tracking-widest text-slate-500">Ownership network</h2>
      <p className="mb-3 text-[11px] text-slate-500">
        {network.nodes.length} nodes · {network.edges.length} edges. Drag nodes to rearrange.
        Red ring = sanctioned entity.
      </p>
      <div
        ref={wrapRef}
        className="rounded-md border border-ink-600/60 bg-ink-800/40 p-1"
      >
        <svg ref={svgRef} />
      </div>
      <Legend />
    </section>
  );
}

function Legend() {
  return (
    <div className="mt-3 flex flex-wrap gap-3 text-[10px] text-slate-500">
      <span className="flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full" style={{ background: KIND_COLOR.vessel, opacity: 0.6 }} />
        vessel
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full" style={{ background: KIND_COLOR.owner, opacity: 0.6 }} />
        owner
      </span>
      <span className="flex items-center gap-1.5">
        <span className="h-2.5 w-2.5 rounded-full" style={{ background: KIND_COLOR.sanctioned_vessel, opacity: 0.6 }} />
        sanctioned vessel
      </span>
    </div>
  );
}
