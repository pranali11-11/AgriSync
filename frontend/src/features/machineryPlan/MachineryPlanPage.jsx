import React, { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import toast from "react-hot-toast";
import {
  ChevronDown,
  CheckCircle2,
  Download,
  Filter,
  Map,
  RotateCcw,
  Search,
  ShieldCheck,
  Users,
  Volume2,
  X,
} from "lucide-react";
import { useSearchParams, useNavigate } from "react-router-dom";
import { fetchFarms, fetchMe } from "../../api/farmer";
import { fetchMachineryPlan } from "../../api/machineryPlan";
import { fetchCrops } from "../../api/crops";
import {
  createMachineListing,
  fetchMachines,
  fetchMachineDetail,
} from "../../api/resources";
import { createGroup, fetchMyGroups } from "../../api/groups";
import { useOnboardingStore } from "../../store/useOnboardingStore";
import { useVoice } from "../../hooks/useVoice";
import { AppBottomNav } from "../../components/AppBottomNav";
import "./machineryPlan.css";

const machineIcons = {
  tractor: "🚜",
  "seed drill": "🌱",
  sprayer: "💧",
  harvester: "🌾",
  rotavator: "⚙",
  thresher: "🌀",
};
const colors = {
  in_window: "border-red-200 bg-red-50 text-red-800",
  due_soon: "border-amber-200 bg-amber-50 text-amber-900",
  upcoming: "border-blue-200 bg-blue-50 text-blue-900",
  passed: "border-slate-200 bg-slate-100 text-slate-500",
};
const labels = {
  in_window: "Needed now",
  due_soon: "Due soon",
  upcoming: "Upcoming",
  passed: "Passed",
};
const iconFor = (name) => machineIcons[name?.toLowerCase()] || "🛠";
const money = (value) =>
  new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(
    value || 0,
  );

function downloadCalendar(items) {
  const events = items
    .map(
      (item) =>
        `BEGIN:VEVENT\r\nSUMMARY:${item.machine_type.name} needed for ${item.stage}\r\nDTSTART;VALUE=DATE:${item.needed_between[0].replaceAll("-", "")}\r\nDTEND;VALUE=DATE:${item.needed_between[1].replaceAll("-", "")}\r\nDESCRIPTION:Estimated solo cost Rs ${money(item.estimated_cost_solo.rupees)}\r\nEND:VEVENT`,
    )
    .join("\r\n");
  const blob = new Blob(
    [
      `BEGIN:VCALENDAR\r\nVERSION:2.0\r\nPRODID:-//AgriSync//Machinery Plan//EN\r\n${events}\r\nEND:VCALENDAR\r\n`,
    ],
    { type: "text/calendar" },
  );
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = "agrisync-machinery-plan.ics";
  link.click();
  URL.revokeObjectURL(link.href);
}

function StatusBadge({ item }) {
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full border px-2 py-1 text-xs font-black ${colors[item.status]}`}
    >
      <span>
        {item.status === "in_window"
          ? "!"
          : item.status === "passed"
            ? "✓"
            : "→"}
      </span>
      {labels[item.status]}
      {item.status === "due_soon" && ` · ${Math.max(0, item.days_until)}d`}
    </span>
  );
}

function PlanItem({ item, onOpen }) {
  const durationDays = Math.max(
    1,
    Math.round(
      (new Date(item.needed_between[1]).getTime() -
        new Date(item.needed_between[0]).getTime()) /
        86400000,
    ) + 1,
  );
  return (
    <button
      onClick={() => onOpen(item)}
      className={`w-full rounded-2xl border p-4 text-left shadow-sm transition hover:shadow-md ${colors[item.status]}`}
    >
      <div className="flex items-start gap-3">
        <span className="text-3xl" aria-hidden="true">
          {iconFor(item.machine_type.name)}
        </span>
        <span className="min-w-0 flex-1">
          <span className="flex flex-wrap items-center justify-between gap-2">
            <strong>{item.machine_type.name}</strong>
            <StatusBadge item={item} />
          </span>
          <span className="mt-1 block text-sm">
            {item.stage} · {item.needed_between[0]} to {item.needed_between[1]}
          </span>
          <span className="mt-2 block text-xs font-bold text-slate-600">
            Use window: {durationDays} day{durationDays === 1 ? "" : "s"} · Not
            booked
          </span>
          <span className="mt-2 block text-xs font-bold">
            Estimate: solo Rs {money(item.estimated_cost_solo.rupees)} · group
            of 5 Rs {money(item.estimated_cost_if_group_of_5.rupees)}
          </span>
        </span>
      </div>
    </button>
  );
}

function DetailSheet({ item, onClose }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { speak } = useVoice("en");
  const text = `${item.machine_type.name} needed for ${item.stage} from ${item.needed_between[0]} to ${item.needed_between[1]}. Estimated solo cost ${money(item.estimated_cost_solo.rupees)} rupees.`;
  return (
    <div className="fixed inset-x-0 bottom-0 z-30 mx-auto max-w-xl rounded-t-3xl bg-white p-5 shadow-2xl">
      <button onClick={onClose} className="float-right p-2" aria-label="Close">
        ×
      </button>
      <div className="text-4xl">{iconFor(item.machine_type.name)}</div>
      <h2 className="mt-2 text-xl font-black">{item.machine_type.name}</h2>
      <p className="text-sm text-slate-600">
        {item.stage} · {item.needed_between[0]} to {item.needed_between[1]}
      </p>
      <StatusBadge item={item} />
      <div className="mt-4 grid grid-cols-2 gap-3 text-sm">
        <p>
          Solo estimate
          <br />
          <strong>Rs {money(item.estimated_cost_solo.rupees)}</strong>
        </p>
        <p>
          Group of 5 estimate
          <br />
          <strong>Rs {money(item.estimated_cost_if_group_of_5.rupees)}</strong>
        </p>
        <p>
          Estimated saving
          <br />
          <strong className="text-emerald-700">
            Rs {money(item.estimated_saving.rupees)}
          </strong>
        </p>
        <p>
          <strong>{item.nearby_demand_count}</strong> farmers near you need this
          too
          <br />
          <strong>{item.open_groups_count}</strong> open groups nearby
        </p>
      </div>
      <div className="mt-4 flex flex-wrap gap-2">
        <button
          onClick={() =>
            navigate(
              `/map?type=${encodeURIComponent(item.machine_type.name)}&date=${item.needed_between[0]}`,
            )
          }
          className="flex items-center gap-2 rounded-xl bg-emerald-700 px-3 py-3 text-sm font-bold text-white"
        >
          <Map className="h-4 w-4" />
          {t("plan.find_machines")}
        </button>
        <button
          onClick={() =>
            navigate(
              `/groups/nearby?machine_type=${encodeURIComponent(item.machine_type.name)}&date_from=${item.needed_between[0]}&date_to=${item.needed_between[1]}`,
            )
          }
          className="flex items-center gap-2 rounded-xl border px-3 py-3 text-sm font-bold"
        >
          <Users className="h-4 w-4" />
          {t("plan.find_group")}
        </button>
        <button
          onClick={() => speak(text)}
          className="rounded-xl border p-3"
          aria-label="Read item aloud"
        >
          <Volume2 className="h-5 w-5" />
        </button>
      </div>
    </div>
  );
}

function MarketplaceCard({ machine, onBook }) {
  const { t } = useTranslation();
  return (
    <motion.article
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <div className="flex h-28 items-center justify-center bg-gradient-to-br from-emerald-100 to-slate-100 text-6xl">
        {iconFor(machine.machine_type?.name)}
      </div>
      <div className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div>
            <h3 className="font-black">
              {machine.machine_type?.name || "Farm machine"}
            </h3>
            <p className="mt-1 text-sm text-slate-500">
              {machine.provider?.name || "Verified provider"}
            </p>
          </div>
          {machine.verified && (
            <ShieldCheck
              className="h-5 w-5 shrink-0 text-emerald-700"
              aria-label="Verified"
            />
          )}
        </div>
        <div className="mt-3 grid grid-cols-2 gap-2 text-xs text-slate-600">
          <span>{machine.distance_km} km away</span>
          <span>★ {machine.rating || "—"}</span>
          <span>Rs {money(machine.rate_per_acre)} / acre</span>
          <span>Available {machine.available_from}</span>
        </div>
        <button
          type="button"
          onClick={() => onBook(machine)}
          className="mt-4 flex min-h-11 w-full items-center justify-center gap-2 rounded-xl bg-emerald-800 px-4 font-black text-white"
        >
          <CheckCircle2 className="h-4 w-4" /> {t("plan.book_machine")}
        </button>
      </div>
    </motion.article>
  );
}

function BookingModal({ machine, farm, onClose, onConfirm, isSaving }) {
  const [date, setDate] = useState(machine.available_from || "");
  const [acres, setAcres] = useState(
    String(Math.min(1, farm?.area_acres || 1)),
  );
  const details = useQuery({
    queryKey: ["machine-detail", machine.id],
    queryFn: () => fetchMachineDetail(machine.id),
    enabled: Boolean(machine.id),
  });
  const provider = details.data?.provider || machine.provider;
  return (
    <div className="fixed inset-0 z-[60] flex items-end justify-center bg-slate-950/50 p-0 sm:items-center sm:p-4">
      <motion.section
        initial={{ y: "100%" }}
        animate={{ y: 0 }}
        className="w-full max-w-lg rounded-t-3xl bg-white p-5 shadow-2xl sm:rounded-3xl"
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-xs font-black uppercase tracking-wide text-emerald-700">
              Book machine
            </p>
            <h2 className="mt-1 text-xl font-black">
              {machine.machine_type?.name}
            </h2>
            <p className="text-sm text-slate-500">
              {provider?.name || "Verified provider"}
            </p>
          </div>
          <button type="button" onClick={onClose} aria-label="Close booking">
            <X className="h-5 w-5" />
          </button>
        </div>
        {provider?.phone && (
          <div className="mt-4 flex gap-2">
            <a
              href={`tel:${provider.phone}`}
              className="flex-1 rounded-xl border px-3 py-2 text-center text-sm font-bold"
            >
              Call owner
            </a>
            <a
              href={`https://wa.me/${provider.phone.replace(/\D/g, "")}`}
              target="_blank"
              rel="noreferrer"
              className="flex-1 rounded-xl border px-3 py-2 text-center text-sm font-bold"
            >
              WhatsApp
            </a>
          </div>
        )}
        <div className="mt-5 grid gap-3 sm:grid-cols-2">
          <label className="text-sm font-bold">
            Booking date
            <input
              type="date"
              min={machine.available_from}
              max={machine.available_to}
              value={date}
              onChange={(event) => setDate(event.target.value)}
              className="mt-1 min-h-11 w-full rounded-xl border px-3"
            />
          </label>
          <label className="text-sm font-bold">
            Farm acres
            <input
              type="number"
              min="0.1"
              max={farm?.area_acres || undefined}
              step="0.1"
              value={acres}
              onChange={(event) => setAcres(event.target.value)}
              className="mt-1 min-h-11 w-full rounded-xl border px-3"
            />
          </label>
        </div>
        <p className="mt-4 rounded-xl bg-emerald-50 p-3 text-sm text-emerald-900">
          Rs {money(machine.rate_per_acre)} per acre. This creates a solo
          confirmed booking through the existing group-booking system.
        </p>
        <div className="mt-5 flex gap-2">
          <button
            type="button"
            onClick={onClose}
            className="min-h-12 flex-1 rounded-xl border font-bold"
          >
            Cancel
          </button>
          <button
            type="button"
            disabled={!date || isSaving}
            onClick={() =>
              onConfirm({
                machine_id: machine.id,
                scheduled_date: date,
                acres: Number(acres),
                min_farmers: 1,
                max_acres: Number(acres),
              })
            }
            className="min-h-12 flex-1 rounded-xl bg-emerald-800 font-black text-white disabled:opacity-50"
          >
            {isSaving ? "Booking..." : "Confirm booking"}
          </button>
        </div>
      </motion.section>
    </div>
  );
}

export default function MachineryPlanPage() {
  const [searchParams] = useSearchParams();
  const { farmId: onboardingFarmId } = useOnboardingStore();
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [farmId, setFarmId] = useState(
    searchParams.get("farm_id") || onboardingFarmId,
  );
  const [view, setView] = useState(
    window.innerWidth < 768 ? "list" : "timeline",
  );
  const [selectedItem, setSelectedItem] = useState(null);
  const [showWhatIf, setShowWhatIf] = useState(false);
  const [sowingDate, setSowingDate] = useState(
    searchParams.get("sowing_date") || "",
  );
  const [cropId, setCropId] = useState(searchParams.get("crop_id") || "");
  const [areaAcres, setAreaAcres] = useState(
    searchParams.get("area_acres") || "",
  );
  const [planFilters, setPlanFilters] = useState({});
  const [machineType, setMachineType] = useState(
    searchParams.get("type") || "",
  );
  const [sortBy, setSortBy] = useState("distance");
  const [maxPrice, setMaxPrice] = useState("");
  const [availableDate, setAvailableDate] = useState(
    searchParams.get("date") || "",
  );
  const [bookingMachine, setBookingMachine] = useState(null);
  const [activeSection, setActiveSection] = useState("marketplace");
  const [showListingForm, setShowListingForm] = useState(false);
  const [listing, setListing] = useState({
    machine_type: "",
    rate_per_acre: "",
    available_from: "",
    available_to: "",
    latitude: "",
    longitude: "",
  });
  const timelineRef = useRef(null);

  const farmsQuery = useQuery({
    queryKey: ["farms"],
    queryFn: fetchFarms,
  });
  const cropsQuery = useQuery({
    queryKey: ["crops"],
    queryFn: fetchCrops,
  });
  const meQuery = useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
  });
  const marketplaceQuery = useQuery({
    queryKey: [
      "machinery-marketplace",
      machineType,
      sortBy,
      maxPrice,
      availableDate,
    ],
    queryFn: () =>
      fetchMachines({
        type: machineType || undefined,
        sort: sortBy,
        max_price: maxPrice || undefined,
        date: availableDate || undefined,
        radius_km: 50,
      }),
    retry: 1,
  });
  const bookingsQuery = useQuery({
    queryKey: ["my-machinery-bookings"],
    queryFn: fetchMyGroups,
  });

  const bookingMutation = useMutation({
    mutationFn: (payload) => createGroup({ ...payload, farm_id: farmId }),
    onSuccess: () => {
      setBookingMachine(null);
      queryClient.invalidateQueries({
        queryKey: ["my-machinery-bookings"],
      });
      queryClient.invalidateQueries({
        queryKey: ["machinery-marketplace"],
      });
    },
    onError: (error) =>
      toast.error(
        error.response?.data?.detail || "Could not create this booking.",
      ),
  });
  const listingMutation = useMutation({
    mutationFn: createMachineListing,
    onSuccess: (result) => {
      toast.success(result.message || "Listing submitted for verification.");
      setShowListingForm(false);
      setListing({
        machine_type: "",
        rate_per_acre: "",
        available_from: "",
        available_to: "",
        latitude: "",
        longitude: "",
      });
      queryClient.invalidateQueries({
        queryKey: ["machinery-marketplace"],
      });
    },
    onError: (error) =>
      toast.error(error.response?.data?.detail || "Could not submit listing."),
  });

  useEffect(() => {
    if (!farmId && farmsQuery.data?.[0]) {
      setFarmId(farmsQuery.data[0].id);
    }
  }, [farmsQuery.data, farmId]);

  useEffect(() => {
    const timeout = setTimeout(() => {
      setPlanFilters({
        sowing_date: sowingDate || undefined,
        crop_id: cropId || undefined,
        area_acres: areaAcres || undefined,
      });
    }, 400);
    return () => clearTimeout(timeout);
  }, [sowingDate, cropId, areaAcres]);

  const selectedFarm = farmsQuery.data?.find(
    (farm) => farm.id === Number(farmId),
  );
  const planQuery = useQuery({
    queryKey: ["machinery-plan", farmId, planFilters],
    queryFn: () => fetchMachineryPlan(farmId, planFilters),
    enabled: Boolean(farmId),
    placeholderData: (previousData) => previousData,
    initialData: () => {
      try {
        return JSON.parse(localStorage.getItem(`agrisync-plan-${farmId}`));
      } catch {
        return undefined;
      }
    },
  });

  useEffect(() => {
    if (farmId && planQuery.data) {
      localStorage.setItem(
        `agrisync-plan-${farmId}`,
        JSON.stringify(planQuery.data),
      );
    }
  }, [planQuery.data, farmId]);

  const { speak } = useVoice("en");
  const items = planQuery.data?.items || [];
  const stage = searchParams.get("stage");
  const today = new Date().toISOString().slice(0, 10);
  const timelineStart = items[0]?.needed_between[0] || today;
  const timelineEnd = items.at(-1)?.needed_between[1] || today;
  const timelineStartTime = new Date(timelineStart).getTime();
  const timelineEndTime = new Date(timelineEnd).getTime();
  const timelinePosition = (date) =>
    `${Math.max(
      0,
      Math.min(
        100,
        ((new Date(date).getTime() - timelineStartTime) /
          Math.max(1, timelineEndTime - timelineStartTime)) *
          100,
      ),
    )}%`;

  if (planQuery.isLoading || farmsQuery.isLoading) {
    return (
      <main className="mx-auto max-w-xl animate-pulse p-5">
        <div className="h-20 rounded-2xl bg-slate-200" />
        <div className="mt-4 h-48 rounded-2xl bg-slate-200" />
      </main>
    );
  }

  if (planQuery.isError || farmsQuery.isError) {
    return (
      <main className="mx-auto flex min-h-screen max-w-xl items-center p-5">
        <section className="w-full rounded-3xl bg-white p-6 text-center shadow-sm">
          <h1 className="text-xl font-black">Could not load machinery plan</h1>
          <p className="mt-2 text-sm text-slate-600">
            {planQuery.error?.response?.data?.detail ||
              farmsQuery.error?.response?.data?.detail ||
              "Please check your farm setup and try again."}
          </p>
          <button
            type="button"
            onClick={() => {
              farmsQuery.refetch();
              planQuery.refetch();
            }}
            className="mt-5 rounded-xl bg-emerald-700 px-5 py-3 font-bold text-white"
          >
            Try again
          </button>
        </section>
      </main>
    );
  }

  return (
    <main className="min-h-screen overflow-x-hidden bg-[#f5f7f2] p-5 pb-20">
      <div className="mx-auto max-w-5xl space-y-5">
        <header className="flex flex-wrap items-end justify-between gap-3">
          <div>
            <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">
              {t("app.name")}
            </p>
            <h1 className="text-3xl font-black">Machinery Calendar</h1>
            {stage && (
              <p className="mt-1 text-sm font-bold text-emerald-700">
                Opened from crop stage: {stage}
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() =>
              speak(
                items
                  .map(
                    (item) =>
                      `${item.machine_type.name} needed ${item.needed_between[0]} to ${item.needed_between[1]}. ${labels[item.status]}.`,
                  )
                  .join(" "),
              )
            }
            className="flex items-center gap-2 rounded-xl border bg-white px-3 py-3 text-sm font-bold"
          >
            <Volume2 className="h-4 w-4" /> Read my plan aloud
          </button>
        </header>

        {farmsQuery.data?.length > 1 && (
          <select
            value={farmId}
            onChange={(event) => setFarmId(event.target.value)}
            className="rounded-xl border p-3 font-bold"
          >
            {farmsQuery.data.map((farm) => (
              <option key={farm.id} value={farm.id}>
                {farm.id} · {farm.crop_id}
              </option>
            ))}
          </select>
        )}

        <div className="flex flex-wrap gap-2 rounded-2xl bg-white p-3">
          <button
            type="button"
            onClick={() => setView("list")}
            className={`rounded-xl px-4 py-2 font-bold ${view === "list" ? "bg-emerald-700 text-white" : "border"}`}
          >
            List
          </button>
          <button
            type="button"
            onClick={() => setView("timeline")}
            className={`rounded-xl px-4 py-2 font-bold ${view === "timeline" ? "bg-emerald-700 text-white" : "border"}`}
          >
            Timeline
          </button>
          <button
            type="button"
            onClick={() => setShowWhatIf((visible) => !visible)}
            className="rounded-xl border px-4 py-2 font-bold"
          >
            What-if <ChevronDown className="inline h-4 w-4" />
          </button>
          <button
            type="button"
            onClick={() => downloadCalendar(items)}
            className="rounded-xl border p-2"
            aria-label="Add all to phone calendar"
          >
            <Download className="h-5 w-5" />
          </button>
        </div>

        {view === "list" && (
          <div className="flex flex-wrap gap-2 rounded-2xl border border-emerald-950/10 bg-[#173f2b] p-2 text-sm font-black text-white">
            {[
              ["needs", "Machinery needs"],
              ["marketplace", "Marketplace"],
              ["bookings", "My bookings"],
            ].map(([section, title]) => (
              <button
                key={section}
                type="button"
                onClick={() => setActiveSection(section)}
                className={`rounded-xl px-4 py-3 ${activeSection === section ? "bg-emerald-400 text-emerald-950" : "text-emerald-100"}`}
              >
                {title}
              </button>
            ))}
          </div>
        )}

        {meQuery.data?.role === "provider" && (
          <section className="rounded-2xl border border-emerald-200 bg-emerald-50 p-4">
            <label className="flex cursor-pointer items-center gap-3 font-black text-emerald-950">
              <input
                type="checkbox"
                checked={showListingForm}
                onChange={(event) => setShowListingForm(event.target.checked)}
                className="h-5 w-5 accent-emerald-700"
              />
              I want to rent out my machine
            </label>
            {showListingForm && (
              <form
                onSubmit={(event) => {
                  event.preventDefault();
                  listingMutation.mutate({
                    ...listing,
                    rate_per_acre: Number(listing.rate_per_acre),
                    latitude: Number(listing.latitude),
                    longitude: Number(listing.longitude),
                  });
                }}
                className="mt-4 grid gap-3 sm:grid-cols-3"
              >
                <input
                  required
                  placeholder="Machine type"
                  value={listing.machine_type}
                  onChange={(event) =>
                    setListing({ ...listing, machine_type: event.target.value })
                  }
                  className="min-h-11 rounded-xl border px-3"
                />
                <input
                  required
                  type="number"
                  min="0.01"
                  step="0.01"
                  placeholder="Rs / acre"
                  value={listing.rate_per_acre}
                  onChange={(event) =>
                    setListing({
                      ...listing,
                      rate_per_acre: event.target.value,
                    })
                  }
                  className="min-h-11 rounded-xl border px-3"
                />
                <input
                  required
                  type="date"
                  value={listing.available_from}
                  onChange={(event) =>
                    setListing({
                      ...listing,
                      available_from: event.target.value,
                    })
                  }
                  className="min-h-11 rounded-xl border px-3"
                />
                <input
                  required
                  type="date"
                  value={listing.available_to}
                  onChange={(event) =>
                    setListing({ ...listing, available_to: event.target.value })
                  }
                  className="min-h-11 rounded-xl border px-3"
                />
                <input
                  required
                  type="number"
                  step="any"
                  placeholder="Latitude"
                  value={listing.latitude}
                  onChange={(event) =>
                    setListing({ ...listing, latitude: event.target.value })
                  }
                  className="min-h-11 rounded-xl border px-3"
                />
                <input
                  required
                  type="number"
                  step="any"
                  placeholder="Longitude"
                  value={listing.longitude}
                  onChange={(event) =>
                    setListing({ ...listing, longitude: event.target.value })
                  }
                  className="min-h-11 rounded-xl border px-3"
                />
                <button
                  type="submit"
                  disabled={listingMutation.isPending}
                  className="min-h-11 rounded-xl bg-emerald-800 px-4 font-black text-white sm:col-span-3"
                >
                  {listingMutation.isPending
                    ? "Submitting..."
                    : "Submit machine listing"}
                </button>
              </form>
            )}
          </section>
        )}

        {showWhatIf && (
          <section className="rounded-2xl border border-amber-200 bg-amber-50 p-4">
            <div className="flex items-center justify-between">
              <strong>Preview, not saved</strong>
              <button
                type="button"
                onClick={() => {
                  setSowingDate("");
                  setCropId("");
                  setAreaAcres("");
                }}
                className="flex items-center gap-1 text-sm font-bold"
              >
                <RotateCcw className="h-4 w-4" /> Reset
              </button>
            </div>
            <div className="mt-3 grid gap-3 sm:grid-cols-3">
              <label className="text-sm font-bold">
                Sowing date
                <input
                  type="date"
                  value={sowingDate || selectedFarm?.sowing_date || ""}
                  onChange={(event) => setSowingDate(event.target.value)}
                  className="mt-1 w-full rounded-lg border p-2"
                />
              </label>
              <label className="text-sm font-bold">
                Crop
                <select
                  value={cropId || selectedFarm?.crop_id || ""}
                  onChange={(event) => setCropId(event.target.value)}
                  className="mt-1 w-full rounded-lg border p-2"
                >
                  <option value="">Current crop</option>
                  {cropsQuery.data?.map((crop) => (
                    <option key={crop.id} value={crop.id}>
                      {crop.name}
                    </option>
                  ))}
                </select>
              </label>
              <label className="text-sm font-bold">
                Area
                <input
                  type="number"
                  min="0.1"
                  value={areaAcres || selectedFarm?.area_acres || ""}
                  onChange={(event) => setAreaAcres(event.target.value)}
                  className="mt-1 w-full rounded-lg border p-2"
                />
              </label>
            </div>
          </section>
        )}

        {view === "list" && activeSection === "needs" && (
          <section>
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-black">Machinery needs</h2>
                <p className="text-sm text-slate-500">
                  Planned from your crop, stage, and sowing date
                </p>
              </div>
              <span className="text-xs font-bold text-slate-500">
                {items.length} needs
              </span>
            </div>
            {items.length ? (
              <div className="grid gap-3 md:grid-cols-2">
                {items.map((item) => (
                  <PlanItem
                    key={`${item.machine_type_id}-${item.needed_between[0]}`}
                    item={item}
                    onOpen={setSelectedItem}
                  />
                ))}
              </div>
            ) : (
              <div className="rounded-2xl bg-white p-8 text-center font-bold">
                No machinery mapping is available for this crop yet.
              </div>
            )}
          </section>
        )}

        {view === "list" && activeSection === "marketplace" && (
          <section>
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-black">Marketplace</h2>
                <p className="text-sm text-slate-500">
                  Verified machines near your farm
                </p>
              </div>
              <Filter className="h-5 w-5 text-emerald-700" />
            </div>
            <div className="grid gap-2 rounded-2xl bg-white p-3 sm:grid-cols-4">
              <label className="text-xs font-bold">
                Machine type
                <input
                  value={machineType}
                  onChange={(event) => setMachineType(event.target.value)}
                  placeholder="Any type"
                  className="mt-1 min-h-10 w-full rounded-lg border px-2"
                />
              </label>
              <label className="text-xs font-bold">
                Max Rs/acre
                <input
                  type="number"
                  value={maxPrice}
                  onChange={(event) => setMaxPrice(event.target.value)}
                  className="mt-1 min-h-10 w-full rounded-lg border px-2"
                />
              </label>
              <label className="text-xs font-bold">
                Available date
                <input
                  type="date"
                  value={availableDate}
                  onChange={(event) => setAvailableDate(event.target.value)}
                  className="mt-1 min-h-10 w-full rounded-lg border px-2"
                />
              </label>
              <label className="text-xs font-bold">
                Sort
                <select
                  value={sortBy}
                  onChange={(event) => setSortBy(event.target.value)}
                  className="mt-1 min-h-10 w-full rounded-lg border px-2"
                >
                  <option value="distance">Distance</option>
                  <option value="price">Price</option>
                  <option value="rating">Rating</option>
                  <option value="availability">Availability</option>
                </select>
              </label>
            </div>
            {marketplaceQuery.isLoading ? (
              <div className="mt-4 grid gap-3 md:grid-cols-3">
                {[1, 2, 3].map((index) => (
                  <div
                    key={index}
                    className="h-64 animate-pulse rounded-2xl bg-slate-200"
                  />
                ))}
              </div>
            ) : marketplaceQuery.isError ? (
              <div className="mt-4 rounded-2xl bg-rose-50 p-5 text-rose-800">
                Marketplace could not load.{" "}
                <button
                  type="button"
                  onClick={() => marketplaceQuery.refetch()}
                  className="font-black underline"
                >
                  Try again
                </button>
              </div>
            ) : marketplaceQuery.data?.items?.length ? (
              <div className="mt-4 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
                {marketplaceQuery.data.items.map((machine) => (
                  <MarketplaceCard
                    key={machine.id}
                    machine={machine}
                    onBook={setBookingMachine}
                  />
                ))}
              </div>
            ) : (
              <div className="mt-4 rounded-2xl bg-white p-8 text-center font-bold">
                No verified machines match these filters.
              </div>
            )}
          </section>
        )}

        {view === "list" && activeSection === "bookings" && (
          <section>
            <div className="mb-3 flex items-center justify-between">
              <div>
                <h2 className="text-xl font-black">My bookings</h2>
                <p className="text-sm text-slate-500">
                  Your solo and group machinery reservations
                </p>
              </div>
              <Users className="h-5 w-5 text-emerald-700" />
            </div>
            {bookingsQuery.isLoading ? (
              <div className="h-32 animate-pulse rounded-2xl bg-slate-200" />
            ) : bookingsQuery.data?.length ? (
              <div className="space-y-3">
                {bookingsQuery.data.map((booking) => (
                  <article
                    key={booking.id}
                    className="rounded-2xl bg-white p-4 shadow-sm"
                  >
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <h3 className="font-black">
                          {booking.machine?.type ||
                            `Machine #${booking.machine_id}`}
                        </h3>
                        <p className="mt-1 text-sm text-slate-500">
                          {booking.scheduled_date}
                        </p>
                      </div>
                      <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-black text-emerald-800">
                        {booking.status}
                      </span>
                    </div>
                    <p className="mt-3 text-sm text-slate-600">
                      {booking.member_count || 1} farmer(s) ·{" "}
                      {booking.total_acres || 0} acres
                    </p>
                  </article>
                ))}
              </div>
            ) : (
              <div className="rounded-2xl bg-white p-8 text-center font-bold">
                No bookings yet. Open Marketplace to reserve a machine.
              </div>
            )}
          </section>
        )}

        {view === "timeline" && (
          <section
            ref={timelineRef}
            className="plan-timeline overflow-x-auto rounded-2xl bg-white p-5"
          >
            <div className="relative min-w-[760px] space-y-4">
              <div
                className="absolute bottom-0 top-0 w-px bg-red-500"
                style={{ left: timelinePosition(today) }}
              />
              <span
                className="absolute -top-1 text-xs font-black text-red-700"
                style={{ left: timelinePosition(today) }}
              >
                Today
              </span>
              {items.map((item) => (
                <motion.button
                  key={`${item.machine_type_id}-${item.needed_between[0]}`}
                  layout="position"
                  type="button"
                  onClick={() => setSelectedItem(item)}
                  className="relative flex h-14 w-full items-center border-b border-slate-100 text-left"
                >
                  <span className="w-32 shrink-0 font-bold">
                    {iconFor(item.machine_type.name)} {item.machine_type.name}
                  </span>
                  <span className="relative h-7 flex-1 rounded-lg bg-slate-100">
                    <motion.span
                      layout
                      className={`absolute h-7 rounded-lg px-2 text-xs font-bold ${colors[item.status]}`}
                      style={{
                        left: timelinePosition(item.needed_between[0]),
                        width: `${Math.max(
                          4,
                          parseFloat(timelinePosition(item.needed_between[1])) -
                            parseFloat(
                              timelinePosition(item.needed_between[0]),
                            ),
                        )}%`,
                      }}
                    >
                      {item.stage}
                    </motion.span>
                  </span>
                </motion.button>
              ))}
            </div>
          </section>
        )}

        {selectedItem && (
          <DetailSheet
            item={selectedItem}
            onClose={() => setSelectedItem(null)}
          />
        )}
        {bookingMachine && (
          <BookingModal
            machine={bookingMachine}
            farm={selectedFarm}
            onClose={() => setBookingMachine(null)}
            onConfirm={(payload) => bookingMutation.mutate(payload)}
            isSaving={bookingMutation.isPending}
          />
        )}
      </div>
      <AppBottomNav />
    </main>
  );
}
