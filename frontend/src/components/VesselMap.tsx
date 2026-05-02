import { useEffect, useMemo, useRef } from "react";
import L from "leaflet";
import type { Band, Vessel } from "../lib/types";
import { BAND_HEX } from "../lib/score";

interface Props {
  vessels: Vessel[];
  selectedImo: string | null;
  onSelect: (imo: string) => void;
}

const TILE_URL = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";
const TILE_ATTR =
  '&copy; <a href="https://carto.com/attributions">CARTO</a> &copy; OpenStreetMap';

/**
 * Dark-tile world map with per-vessel circle markers colored by deception band.
 * Critical-band markers receive a CSS pulse animation.
 */
export default function VesselMap({ vessels, selectedImo, onSelect }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const layerRef = useRef<L.LayerGroup | null>(null);
  const onSelectRef = useRef(onSelect);
  onSelectRef.current = onSelect;

  // Init Leaflet once.
  useEffect(() => {
    if (!ref.current || mapRef.current) return;
    const map = L.map(ref.current, {
      worldCopyJump: true,
      preferCanvas: true,
      zoomControl: true,
      attributionControl: true,
    }).setView([18, 50], 3);
    L.tileLayer(TILE_URL, { attribution: TILE_ATTR, maxZoom: 12 }).addTo(map);
    layerRef.current = L.layerGroup().addTo(map);
    mapRef.current = map;

    return () => {
      map.remove();
      mapRef.current = null;
      layerRef.current = null;
    };
  }, []);

  // Render markers when vessel data changes.
  useEffect(() => {
    if (!mapRef.current || !layerRef.current) return;
    layerRef.current.clearLayers();

    vessels.forEach((v) => {
      if (v.last_seen_lat == null || v.last_seen_lon == null) return;
      const band = (v.band as Band | undefined) ?? null;
      const color = band ? BAND_HEX[band] : "#64748b";
      const radius =
        band === "critical" ? 9 : band === "high" ? 7 : band === "medium" ? 6 : 5;

      const marker = L.circleMarker([v.last_seen_lat, v.last_seen_lon], {
        radius,
        color,
        weight: 1.5,
        fillColor: color,
        fillOpacity: 0.55,
        className: band === "critical" ? "marker-critical" : undefined,
      });

      marker.bindTooltip(
        `<strong>${escapeHtml(v.name)}</strong><br/>IMO ${v.imo} · ${escapeHtml(v.flag)}` +
          (v.score != null ? `<br/>score ${v.score} · <em>${v.band}</em>` : ""),
        { direction: "top", offset: [0, -6], className: "shadowfleet-tooltip" },
      );
      marker.on("click", () => onSelectRef.current(v.imo));
      marker.addTo(layerRef.current!);
    });
  }, [vessels]);

  // When selection changes externally, recenter.
  useEffect(() => {
    if (!mapRef.current || !selectedImo) return;
    const v = vessels.find((x) => x.imo === selectedImo);
    if (v?.last_seen_lat != null && v?.last_seen_lon != null) {
      mapRef.current.flyTo([v.last_seen_lat, v.last_seen_lon], Math.max(mapRef.current.getZoom(), 5), {
        duration: 0.6,
      });
    }
  }, [selectedImo, vessels]);

  return <div ref={ref} className="absolute inset-0" />;
}

function escapeHtml(s: string): string {
  return s
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}
