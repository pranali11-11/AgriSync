import React, { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import {
  ChevronLeft,
  ChevronRight,
  LocateFixed,
  Navigation,
  Phone,
  SlidersHorizontal,
  X,
} from "lucide-react";
import {
  MapContainer,
  Marker,
  Popup,
  TileLayer,
  Circle as LeafletCircle,
  useMap,
} from "react-leaflet";
import MarkerClusterGroup from "react-leaflet-cluster";
import L from "leaflet";
import { useGeolocation } from "../../hooks/useGeolocation";
import { AppBottomNav } from "../../components/AppBottomNav";
import {
  fetchInputSellers,
  fetchMachineDetail,
  fetchMachines,
  fetchProviders,
} from "../../api/resources";
import "leaflet/dist/leaflet.css";
import { useNavigate, useSearchParams } from "react-router-dom";

const CACHE_KEY = "agrisync-resource-results";
const colors = {
  machine: "#16803c",
  provider: "#2563eb",
  input_seller: "#ea580c",
  farm: "#dc2626",
};

function iconFor(type) {
  return L.divIcon({
    className: "",
    html: `<div style="width:36px;height:36px;border-radius:50%;background:${colors[type] || "#475569"};border:3px solid white;box-shadow:0 2px 8px #0005;display:flex;align-items:center;justify-content:center;color:white"><span style="font-size:19px">${type === "machine" ? "⚙" : type === "provider" ? "●" : type === "input_seller" ? "▣" : "📍"}</span></div>`,
    iconSize: [36, 36],
    iconAnchor: [18, 18],
  });
}

function MapResizer({ open }) {
  const map = useMap();
  useEffect(() => {
    const timer = setTimeout(() => map.invalidateSize(), 250);
    return () => clearTimeout(timer);
  }, [map, open]);
  return null;
}

function MapEvents({ selected }) {
  const map = useMap();
  useEffect(() => {
    if (selected?.coordinates)
      map.setView(
        [selected.coordinates.lat, selected.coordinates.lng],
        Math.max(map.getZoom(), 13),
        { animate: true },
      );
  }, [map, selected]);
  return null;
}

function ResourceMarker({ item, onSelect }) {
  if (!item.coordinates) return null;
  return (
    <Marker
      position={[item.coordinates.lat, item.coordinates.lng]}
      icon={iconFor(item.resource_type)}
      eventHandlers={{ click: () => onSelect(item) }}
    >
      <Popup>
        <strong>
          {item.machine_type?.name || item.name || item.provider?.name}
        </strong>
        <br />
        {item.distance_km} km away
        <br />
        {item.rating ? `${item.rating} / 5` : ""}
      </Popup>
    </Marker>
  );
}

function DetailCard({ item, onClose }) {
  const navigate = useNavigate();
  const { t } = useTranslation();
  const [detail, setDetail] = useState(item);
  const [photoIndex, setPhotoIndex] = useState(0);
  useEffect(() => {
    let active = true;
    setDetail(item);
    setPhotoIndex(0);
    if (item.resource_type === "machine" && item.coordinates)
      fetchMachineDetail(item.id, {
        lat: item.coordinates.lat,
        lng: item.coordinates.lng,
      })
        .then((machine) => {
          if (active) setDetail(machine);
        })
        .catch(() => {});
    return () => {
      active = false;
    };
  }, [item]);
  const photos = detail.photos || [];
  const destination = detail.coordinates
    ? `${detail.coordinates.lat},${detail.coordinates.lng}`
    : "";
  return (
    <motion.aside
      initial={{ x: "100%" }}
      animate={{ x: 0 }}
      className="absolute right-3 top-3 z-[1000] w-[min(360px,calc(100%-24px))] rounded-2xl bg-white p-5 shadow-2xl"
    >
      <button
        onClick={onClose}
        className="absolute right-3 top-3 rounded-full p-2"
        aria-label="Close detail"
      >
        <X className="h-5 w-5" />
      </button>
      {item.resource_type === "machine" && (
        <div className="relative h-44 overflow-hidden rounded-xl bg-slate-100">
          {photos.length ? (
            <img
              src={photos[photoIndex]}
              alt={detail.machine_type?.name || t("machine_detail.photos")}
              className="h-full w-full object-cover"
            />
          ) : (
            <p className="flex h-full items-center justify-center text-sm text-slate-500">
              {t("machine_detail.no_photos")}
            </p>
          )}
          {photos.length > 1 && (
            <>
              <button
                type="button"
                onClick={() =>
                  setPhotoIndex(
                    (photoIndex - 1 + photos.length) % photos.length,
                  )
                }
                className="absolute left-2 top-1/2 -translate-y-1/2 rounded-full bg-black/60 p-2 text-white"
                aria-label={t("machine_detail.previous_photo")}
              >
                <ChevronLeft className="h-5 w-5" aria-hidden="true" />
              </button>
              <button
                type="button"
                onClick={() => setPhotoIndex((photoIndex + 1) % photos.length)}
                className="absolute right-2 top-1/2 -translate-y-1/2 rounded-full bg-black/60 p-2 text-white"
                aria-label={t("machine_detail.next_photo")}
              >
                <ChevronRight className="h-5 w-5" aria-hidden="true" />
              </button>
            </>
          )}
        </div>
      )}
      <h2 className="mt-4 text-xl font-black">
        {detail.machine_type?.name || detail.name}
      </h2>
      <p className="text-sm text-slate-600">
        {detail.provider?.name} · {detail.provider?.org_type}
      </p>
      <div className="mt-3 grid grid-cols-2 gap-2 text-sm">
        <span className="font-bold">₹{detail.rate_per_acre || "—"} / acre</span>
        <span>{detail.distance_km} km</span>
        <span>★ {detail.rating || "—"}</span>
        <span
          className={
            detail.verified ? "text-emerald-700" : "font-bold text-amber-800"
          }
        >
          {detail.verified
            ? t("machine_detail.verified_notice")
            : t("provider.unverified_badge")}
        </span>
      </div>
      {!detail.verified && (
        <p className="mt-3 rounded-lg bg-amber-50 p-2 text-xs font-semibold text-amber-900">
          {t("machine_detail.unverified_notice")}
        </p>
      )}
      {detail.description && (
        <p className="mt-3 text-sm text-slate-700">{detail.description}</p>
      )}
      {detail.model_year && (
        <p className="mt-2 text-sm">
          <strong>{t("machine_detail.model_year")}:</strong> {detail.model_year}
        </p>
      )}
      {detail.specifications &&
        Object.keys(detail.specifications).length > 0 && (
          <div className="mt-3 border-t pt-3 text-sm">
            <h3 className="font-bold">{t("machine_detail.specs")}</h3>
            {detail.specifications.horsepower && (
              <p>
                {t("machine_detail.horsepower")}:{" "}
                {detail.specifications.horsepower} HP
              </p>
            )}
            {detail.specifications.attachments?.length > 0 && (
              <p>
                {t("machine_detail.attachments")}:{" "}
                {detail.specifications.attachments.join(", ")}
              </p>
            )}
          </div>
        )}
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          onClick={() =>
            navigate(
              `/groups/new?machine_id=${detail.id}&date=${new Date()
                .toISOString()
                .slice(0, 10)}`,
            )
          }
          className="rounded-xl bg-emerald-700 px-3 py-2 text-sm font-bold text-white"
        >
          {t("resources.book_solo")}
        </button>
        <button
          onClick={() => navigate(`/groups/nearby?machine_id=${detail.id}`)}
          className="rounded-xl border px-3 py-2 text-sm font-bold"
        >
          {t("resources.start_join_group")}
        </button>
        <a
          href={`tel:${detail.provider?.phone || ""}`}
          className="rounded-xl border p-2"
          aria-label="Call provider"
        >
          <Phone className="h-5 w-5" />
        </a>
        <a
          href={`https://www.google.com/maps/dir/?api=1&destination=${destination}`}
          target="_blank"
          rel="noreferrer"
          className="rounded-xl border p-2"
          aria-label="Open in Google Maps"
        >
          <Navigation className="h-5 w-5" />
        </a>
      </div>
    </motion.aside>
  );
}

export default function ResourceMapPage() {
  const { t } = useTranslation();
  const [params] = useSearchParams();
  const [radius, setRadius] = useState(10);
  const [debouncedRadius, setDebouncedRadius] = useState(10);
  const [selected, setSelected] = useState(null);
  const [visible, setVisible] = useState({
    machines: true,
    providers: true,
    sellers: true,
  });
  const [sheet, setSheet] = useState("half");
  const [lastUpdated, setLastUpdated] = useState(null);
  const [type, setType] = useState(params.get("type") || "");
  const [filterDate, setFilterDate] = useState(params.get("date") || "");
  const [maxPrice, setMaxPrice] = useState("");
  const [verifiedOnly, setVerifiedOnly] = useState(false);
  const [sort, setSort] = useState("distance");
  const listRefs = useRef({});
  const { location, error: geoError } = useGeolocation({
    enableHighAccuracy: true,
    timeout: 5000,
  });
  const hasGps = location.latitude != null && location.longitude != null;
  const lat = hasGps ? location.latitude : 18.5204;
  const lng = hasGps ? location.longitude : 73.8567;
  const filters = {
    ...(hasGps ? { lat, lng } : {}),
    radius_km: debouncedRadius,
    type: type || undefined,
    date: filterDate || undefined,
    max_price: maxPrice || undefined,
    verified_only: verifiedOnly,
    sort,
  };
  useEffect(() => {
    const timer = setTimeout(() => setDebouncedRadius(radius), 400);
    return () => clearTimeout(timer);
  }, [radius]);
  const machines = useQuery({
    queryKey: ["machines", filters],
    queryFn: () => fetchMachines(filters),
    placeholderData: (previous) => previous,
    initialData: () => {
      try {
        return JSON.parse(localStorage.getItem(CACHE_KEY));
      } catch {
        return undefined;
      }
    },
  });
  const providers = useQuery({
    queryKey: ["providers", lat, lng, debouncedRadius],
    queryFn: () =>
      fetchProviders({
        ...(hasGps ? { lat, lng } : {}),
        radius_km: debouncedRadius,
      }),
    placeholderData: (previous) => previous,
  });
  const sellers = useQuery({
    queryKey: ["sellers", lat, lng, debouncedRadius],
    queryFn: () =>
      fetchInputSellers({
        ...(hasGps ? { lat, lng } : {}),
        radius_km: debouncedRadius,
      }),
    placeholderData: (previous) => previous,
  });
  useEffect(() => {
    if (machines.data) {
      localStorage.setItem(CACHE_KEY, JSON.stringify(machines.data));
      setLastUpdated(new Date());
    }
  }, [machines.data]);
  const items = useMemo(
    () => [
      ...(visible.machines ? machines.data?.items || [] : []),
      ...(visible.providers ? providers.data?.items || [] : []),
      ...(visible.sellers ? sellers.data?.items || [] : []),
    ],
    [machines.data, providers.data, sellers.data, visible],
  );
  const selectItem = (item) => {
    setSelected(item);
    listRefs.current[item.id]?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    });
  };
  return (
    <main className="relative h-screen overflow-hidden bg-slate-100">
      <MapContainer
        center={[lat, lng]}
        zoom={11}
        className="absolute inset-0 z-0"
      >
        <TileLayer
          attribution="&copy; OpenStreetMap contributors"
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <LeafletCircle
          center={[lat, lng]}
          radius={debouncedRadius * 1000}
          pathOptions={{ color: "#15803d", fillOpacity: 0.06 }}
        />
        <Marker position={[lat, lng]} icon={iconFor("farm")} />
        <MapEvents selected={selected} />
        <MapResizer open={sheet} />
        {visible.machines && (
          <MarkerClusterGroup>
            {(machines.data?.items || []).map((item) => (
              <ResourceMarker
                key={`m-${item.id}`}
                item={item}
                onSelect={selectItem}
              />
            ))}
          </MarkerClusterGroup>
        )}
        {visible.providers && (
          <MarkerClusterGroup>
            {(providers.data?.items || []).map((item) => (
              <ResourceMarker
                key={`p-${item.id}`}
                item={item}
                onSelect={selectItem}
              />
            ))}
          </MarkerClusterGroup>
        )}
        {visible.sellers && (
          <MarkerClusterGroup>
            {(sellers.data?.items || []).map((item) => (
              <ResourceMarker
                key={`s-${item.id}`}
                item={item}
                onSelect={selectItem}
              />
            ))}
          </MarkerClusterGroup>
        )}
      </MapContainer>
      <div className="absolute left-3 right-3 top-3 z-[1000] flex flex-wrap items-center gap-2 rounded-2xl bg-white/95 p-3 shadow-lg">
        <button
          className="rounded-xl border p-2"
          aria-label="Locate me"
          onClick={() =>
            navigator.geolocation?.getCurrentPosition(() =>
              window.location.reload(),
            )
          }
        >
          <LocateFixed className="h-5 w-5" />
        </button>
        <label className="flex min-w-[190px] flex-1 items-center gap-2 text-sm font-bold">
          <SlidersHorizontal className="h-4 w-4" /> {radius} km
          <input
            type="range"
            min="1"
            max="50"
            value={radius}
            onChange={(event) => setRadius(Number(event.target.value))}
            className="w-full"
          />
        </label>
        <select
          value={type}
          onChange={(event) => setType(event.target.value)}
          className="rounded-lg border p-2 text-sm"
        >
          <option value="">{t("resources.all_machine_types")}</option>
          <option value="sprayer">{t("resources.sprayer")}</option>
          <option value="tractor">{t("resources.tractor")}</option>
          <option value="harvester">{t("resources.harvester")}</option>
        </select>
        <input
          type="date"
          value={filterDate}
          onChange={(event) => setFilterDate(event.target.value)}
          className="rounded-lg border p-2 text-sm"
        />
        <input
          type="number"
          min="0"
          placeholder={t("resources.max_price_placeholder")}
          value={maxPrice}
          onChange={(event) => setMaxPrice(event.target.value)}
          className="w-24 rounded-lg border p-2 text-sm"
        />
        <select
          value={sort}
          onChange={(event) => setSort(event.target.value)}
          className="rounded-lg border p-2 text-sm"
        >
          <option value="distance">{t("resources.distance")}</option>
          <option value="rating">{t("resources.rating")}</option>
          <option value="price">{t("resources.price")}</option>
          <option value="availability">{t("resources.availability")}</option>
        </select>
        <label className="text-xs font-bold">
          <input
            type="checkbox"
            checked={verifiedOnly}
            onChange={(event) => setVerifiedOnly(event.target.checked)}
          />{" "}
          {t("resources.verified_only_label")}
        </label>
        <label className="text-xs font-bold">
          <input
            type="checkbox"
            checked={visible.machines}
            onChange={() =>
              setVisible((state) => ({ ...state, machines: !state.machines }))
            }
          />{" "}
          {t("resources.machines")}
        </label>
        <label className="text-xs font-bold">
          <input
            type="checkbox"
            checked={visible.providers}
            onChange={() =>
              setVisible((state) => ({ ...state, providers: !state.providers }))
            }
          />{" "}
          {t("resources.providers")}
        </label>
        <label className="text-xs font-bold">
          <input
            type="checkbox"
            checked={visible.sellers}
            onChange={() =>
              setVisible((state) => ({ ...state, sellers: !state.sellers }))
            }
          />{" "}
          {t("resources.sellers")}
        </label>
      </div>
      {geoError && (
        <div className="absolute left-3 top-24 z-[1000] rounded-xl bg-white px-3 py-2 text-xs font-bold shadow">
          {t("resources.using_saved_location")}
        </div>
      )}
      {lastUpdated && !navigator.onLine && (
        <div className="absolute right-3 top-24 z-[1000] rounded-xl bg-slate-800 px-3 py-2 text-xs font-bold text-white">
          {t("resources.offline")} {lastUpdated.toLocaleDateString()}
        </div>
      )}
      {selected && (
        <DetailCard item={selected} onClose={() => setSelected(null)} />
      )}
      <motion.section
        animate={{
          height: sheet === "peek" ? 105 : sheet === "full" ? "82vh" : "42vh",
        }}
        className="absolute bottom-0 left-0 right-0 z-[1000] overflow-hidden rounded-t-3xl bg-white shadow-2xl"
      >
        <div
          className="mx-auto mt-3 h-1.5 w-12 rounded-full bg-slate-300"
          onClick={() =>
            setSheet(
              sheet === "peek" ? "half" : sheet === "half" ? "full" : "peek",
            )
          }
        />
        <div className="flex items-center justify-between px-5 py-3">
          <h1 className="text-lg font-black">{t("resources.title")}</h1>
          <span className="text-sm font-bold text-slate-500">
            {items.length} {t("resources.results")}
          </span>
        </div>
        <div className="h-[calc(100%-58px)] overflow-y-auto px-4 pb-6">
          {machines.isLoading ? (
            <div className="animate-pulse space-y-3">
              <div className="h-16 rounded-xl bg-slate-100" />
              <div className="h-16 rounded-xl bg-slate-100" />
            </div>
          ) : items.length ? (
            items.map((item) => (
              <button
                key={`${item.resource_type}-${item.id}`}
                ref={(node) => {
                  listRefs.current[item.id] = node;
                }}
                onClick={() => selectItem(item)}
                className={`mb-2 flex w-full items-center justify-between rounded-xl border p-3 text-left ${
                  selected?.id === item.id
                    ? "border-emerald-600 bg-emerald-50"
                    : "border-slate-200"
                }`}
              >
                <span>
                  <strong>{item.machine_type?.name || item.name}</strong>
                  <br />
                  <small>
                    {item.distance_km} km ·{" "}
                    {item.verified
                      ? t("resources.verified")
                      : t("resources.unverified")}
                  </small>
                </span>
                <span className="font-bold">
                  {item.rate_per_acre
                    ? `₹${item.rate_per_acre}`
                    : item.org_type || t("resources.shop")}
                </span>
              </button>
            ))
          ) : (
            <div className="py-10 text-center text-sm text-slate-600">
              <div className="mb-3 text-4xl">🧭</div>
              {t("resources.no_resources_found")}
            </div>
          )}
        </div>
      </motion.section>
      <AppBottomNav />
    </main>
  );
}
