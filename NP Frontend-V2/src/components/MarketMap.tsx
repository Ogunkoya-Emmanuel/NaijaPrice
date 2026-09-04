import "leaflet/dist/leaflet.css";
import { MapContainer, TileLayer, Marker, Popup } from "react-leaflet";
import L from "leaflet";
import type { MapMarket } from "@/lib/api";
import { formatNaira } from "@/lib/utils";
import { CheckCircle2 } from "lucide-react";

// Custom amber pin, built as an inline SVG string divIcon so we never depend
// on leaflet's default marker image paths (which break under most bundlers).
function pinIcon(hasPrice: boolean) {
  const color = hasPrice ? "#F59E0B" : "#6B7280";
  const svg = `<svg width="26" height="34" viewBox="0 0 26 34" xmlns="http://www.w3.org/2000/svg">
    <path d="M13 0C5.82 0 0 5.82 0 13c0 9.75 13 21 13 21s13-11.25 13-21c0-7.18-5.82-13-13-13z"
      fill="${color}" stroke="#0A0F1E" stroke-width="1.5" />
    <circle cx="13" cy="13" r="5" fill="#0A0F1E" />
  </svg>`;
  return L.divIcon({
    html: svg,
    className: "",
    iconSize: [26, 34],
    iconAnchor: [13, 34],
    popupAnchor: [0, -30],
  });
}

export default function MarketMap({ markets }: { markets: MapMarket[] }) {
  const withCoords = markets.filter((m) => m.latitude != null && m.longitude != null);

  return (
    <div className="h-[520px] w-full rounded-xl overflow-hidden border border-border">
      <MapContainer center={[9.0, 8.0]} zoom={6} style={{ height: "100%", width: "100%" }}>
        {/*
          Esri's Dark Gray Canvas — a genuinely keyless dark basemap.
          (Previously used CARTO's free raster tiles, but CARTO started
          requiring an API key for anonymous requests on Aug 28 2026 and
          now stamps an "API KEY REQUIRED" watermark on unauthenticated
          tiles. This tile set needs no key or signup at all.)
        */}
        <TileLayer
          url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}"
          attribution='Tiles &copy; Esri &mdash; Esri, DeLorme, NAVTEQ'
        />
        <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Dark_Gray_Reference/MapServer/tile/{z}/{y}/{x}" />
        {withCoords.map((m) => (
          <Marker key={m.market_id} position={[m.latitude!, m.longitude!]} icon={pinIcon(!!m.median_price)}>
            <Popup>
              <div className="text-sm">
                <p className="font-semibold text-bg">{m.name}</p>
                <p className="text-bg/70 text-xs mb-1.5">
                  {m.city}
                  {m.state ? `, ${m.state}` : ""}
                </p>
                {m.median_price ? (
                  <>
                    <p className="text-bg font-bold">{formatNaira(m.median_price)}</p>
                    <p className="text-bg/70 text-xs flex items-center gap-1">
                      {m.is_verified && <CheckCircle2 size={12} />}
                      {m.submission_count} submission{m.submission_count === 1 ? "" : "s"}
                    </p>
                  </>
                ) : (
                  <p className="text-bg/70 text-xs">No price data yet for this selection</p>
                )}
              </div>
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  );
}
