import { useEffect, useRef, useState } from "react";
import L from "leaflet";
import { api } from "../lib/api";
import type { SAROverlay } from "../lib/types";

interface Props {
  imo: string;
}

const TILE_URL = "https://{s}.basemaps.cartocdn.com/dark_all/{z}/{x}/{y}{r}.png";

export default function SARViewer({ imo }: Props) {
  const [overlay, setOverlay] = useState<SAROverlay | null>(null);
  const [error, setError] = useState<string | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);

  useEffect(() => {
    setOverlay(null);
    setError(null);
    api.getSAR(imo).then(setOverlay).catch((e) => setError(String(e)));
  }, [imo]);

  useEffect(() => {
    if (!overlay || !ref.current) return;

    if (!mapRef.current) {
      mapRef.current = L.map(ref.current, { zoomControl: false, attributionControl: false });
      L.tileLayer(TILE_URL, { maxZoom: 12 }).addTo(mapRef.current);
    }
    const map = mapRef.current;
    map.eachLayer((l) => {
      if (l instanceof L.CircleMarker || l instanceof L.Polyline) map.removeLayer(l);
    });

    if (overlay.ais_position && overlay.sar_position) {
      const [aLat, aLon] = overlay.ais_position;
      const [sLat, sLon] = overlay.sar_position;
      L.circleMarker([aLat, aLon], {
        radius: 8,
        color: "#22d3ee",
        weight: 2,
        fillColor: "#22d3ee",
        fillOpacity: 0.4,
      })
        .bindTooltip("AIS-reported position", { permanent: true, direction: "right", offset: [10, 0] })
        .addTo(map);
      L.circleMarker([sLat, sLon], {
        radius: 10,
        color: "#ef4444",
        weight: 2,
        fillColor: "#ef4444",
        fillOpacity: 0.5,
      })
        .bindTooltip("SAR-detected position", { permanent: true, direction: "right", offset: [10, 0] })
        .addTo(map);
      L.polyline(
        [
          [aLat, aLon],
          [sLat, sLon],
        ],
        { color: "#ef4444", weight: 1, dashArray: "4 4", opacity: 0.6 },
      ).addTo(map);

      const bounds = L.latLngBounds([aLat, aLon], [sLat, sLon]).pad(0.5);
      map.fitBounds(bounds);
    } else if (overlay.bbox) {
      const [w, s, e, n] = overlay.bbox;
      map.fitBounds([
        [s, w],
        [n, e],
      ]);
    } else {
      map.setView([0, 0], 2);
    }
  }, [overlay]);

  useEffect(() => {
    return () => {
      mapRef.current?.remove();
      mapRef.current = null;
    };
  }, []);

  if (error) return <p className="text-xs text-rose-400">error: {error}</p>;
  if (!overlay) return <p className="text-xs text-slate-500">loading SAR overlay…</p>;
  if (!overlay.ais_position || !overlay.sar_position) {
    return (
      <section>
        <h2 className="mb-2 text-xs uppercase tracking-widest text-slate-500">SAR cross-check</h2>
        <p className="text-xs text-slate-500">
          {overlay.note ?? "No recent dark window for this vessel — nothing to cross-check."}
        </p>
      </section>
    );
  }

  return (
    <section>
      <h2 className="mb-2 text-xs uppercase tracking-widest text-slate-500">SAR vs AIS</h2>
      <p className="mb-2 text-[11px] leading-relaxed text-slate-400">
        Sentinel-1 detection during the most recent dark window vs the position the
        vessel's AIS implied. Mismatch = vessel is lying about location.
      </p>
      <div ref={ref} className="h-72 rounded-md border border-ink-600/60 bg-ink-800/40" />
      {overlay.note && <p className="mt-2 text-[10px] text-slate-600">{overlay.note}</p>}
    </section>
  );
}
