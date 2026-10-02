import React, { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { motion } from "framer-motion";
import {
  AlertTriangle,
  Bug,
  Droplets,
  Loader2,
  MessageCircle,
  Pause,
  Play,
  Send,
  Square,
  Sprout,
  X,
} from "lucide-react";
import toast from "react-hot-toast";
import { useTranslation } from "react-i18next";
import { askAdvisoryAssistant, fetchAdvisory } from "../../api/advisory";
import { fetchFarms, saveSoilTest } from "../../api/farmer";
import { useOnboardingStore } from "../../store/useOnboardingStore";
import { useVoice } from "../../hooks/useVoice";
import { useNavigate } from "react-router-dom";
import { AppBottomNav } from "../../components/AppBottomNav";

const CACHE_KEY = "agrisync-last-advisory";
function getCachedAdvisory() {
  try {
    const cached = JSON.parse(localStorage.getItem(CACHE_KEY));
    return cached && Array.isArray(cached.timeline) ? cached : undefined;
  } catch {
    return undefined;
  }
}

function Skeleton() {
  return (
    <div className="animate-pulse space-y-5">
      <div className="h-28 rounded-3xl bg-slate-200" />
      <div className="h-24 rounded-2xl bg-slate-200" />
      <div className="grid gap-4 md:grid-cols-2">
        <div className="h-48 rounded-2xl bg-slate-200" />
        <div className="h-48 rounded-2xl bg-slate-200" />
      </div>
    </div>
  );
}

function QueryMessage({ title, detail, onRetry, actionLabel, onAction }) {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl items-center justify-center p-5">
      <section className="w-full max-w-lg rounded-3xl bg-white p-8 text-center shadow-sm">
        <AlertTriangle className="mx-auto h-10 w-10 text-amber-500" />
        <h1 className="mt-4 text-xl font-black text-slate-900">{title}</h1>
        <p className="mt-2 text-sm leading-6 text-slate-600">{detail}</p>
        {onRetry && (
          <button
            type="button"
            onClick={onRetry}
            className="mt-6 min-h-11 rounded-xl bg-emerald-700 px-5 font-bold text-white"
          >
            Try again
          </button>
        )}
        {onAction && (
          <button
            type="button"
            onClick={onAction}
            className="mt-6 min-h-11 rounded-xl border border-emerald-700 px-5 font-bold text-emerald-800"
          >
            {actionLabel}
          </button>
        )}
      </section>
    </main>
  );
}

function ListenButton({ text, lang, label, onRead }) {
  const { speak, speaking, paused, pause, resume, stop, error } =
    useVoice(lang);
  const handleSpeak = () => {
    if (speaking && !paused) {
      pause();
      return;
    }
    if (paused) {
      resume();
      return;
    }
    speak(text);
    onRead();
  };

  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        onClick={handleSpeak}
        className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-200 px-3 text-sm font-bold text-slate-700 hover:border-emerald-500"
        aria-label={label}
      >
        {speaking && !paused ? (
          <Pause className="h-4 w-4 text-emerald-600" />
        ) : (
          <Play className="h-4 w-4 text-emerald-600" />
        )}
        {speaking ? (paused ? "Resume" : "Pause") : label}
      </button>
      {speaking && (
        <button
          type="button"
          onClick={stop}
          className="inline-flex min-h-11 items-center gap-2 rounded-xl border border-slate-200 px-3 text-sm font-bold text-slate-700"
          aria-label="Stop audio"
        >
          <Square className="h-4 w-4" /> Stop
        </button>
      )}
      {error && (
        <span className="text-xs font-bold text-rose-700">{error}</span>
      )}
    </div>
  );
}

function SoilTestModal({ onClose, onSubmit, isSaving }) {
  const [form, setForm] = useState({
    ph: "",
    nitrogen: "",
    phosphorus: "",
    potassium: "",
    organic_carbon: "",
    tested_on: new Date().toISOString().slice(0, 10),
  });
  const update = (event) =>
    setForm((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
  const submit = (event) => {
    event.preventDefault();
    onSubmit({
      ...form,
      ph: Number(form.ph),
      nitrogen: form.nitrogen ? Number(form.nitrogen) : null,
      phosphorus: form.phosphorus ? Number(form.phosphorus) : null,
      potassium: form.potassium ? Number(form.potassium) : null,
      organic_carbon: form.organic_carbon ? Number(form.organic_carbon) : null,
    });
  };
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center bg-slate-950/50 p-4">
      <section className="max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-3xl bg-white p-5 shadow-2xl">
        <div className="flex items-center justify-between gap-4">
          <div>
            <h2 className="text-xl font-black">Add soil test</h2>
            <p className="mt-1 text-sm text-slate-500">
              These values are sent to the advisory engine and affect
              recommendations.
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            aria-label="Close soil test form"
          >
            <X className="h-5 w-5" />
          </button>
        </div>
        <form onSubmit={submit} className="mt-5 space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            {[
              ["ph", "pH", "0", "14", "0.1"],
              ["nitrogen", "Nitrogen", "0", "", "0.1"],
              ["phosphorus", "Phosphorus", "0", "", "0.1"],
              ["potassium", "Potassium", "0", "", "0.1"],
              ["organic_carbon", "Organic carbon", "0", "", "0.01"],
            ].map(([name, label, min, max, step]) => (
              <label key={name} className="text-sm font-bold">
                {label}
                {name === "ph" ? " *" : ""}
                <input
                  required={name === "ph"}
                  type="number"
                  name={name}
                  min={min}
                  max={max || undefined}
                  step={step}
                  value={form[name]}
                  onChange={update}
                  className="mt-1 min-h-11 w-full rounded-xl border border-slate-300 px-3"
                />
              </label>
            ))}
            <label className="text-sm font-bold">
              Tested on
              <input
                required
                type="date"
                name="tested_on"
                value={form.tested_on}
                onChange={update}
                className="mt-1 min-h-11 w-full rounded-xl border border-slate-300 px-3"
              />
            </label>
          </div>
          <p className="text-xs text-slate-500">
            Moisture and report upload are not supported by the current backend
            contract; the supported laboratory values are saved above.
          </p>
          <button
            type="submit"
            disabled={isSaving}
            className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl bg-emerald-800 px-4 font-black text-white disabled:opacity-60"
          >
            {isSaving && <Loader2 className="h-5 w-5 animate-spin" />}
            {isSaving ? "Saving soil test..." : "Save soil test"}
          </button>
        </form>
      </section>
    </div>
  );
}

const soilInfo = {
  ph: {
    label: "pH",
    unit: "",
    explanation: "pH controls how easily the crop can absorb nutrients.",
  },
  nitrogen: {
    label: "Nitrogen",
    unit: "mg/kg",
    explanation:
      "Low nitrogen can cause pale leaves and slow vegetative growth.",
  },
  phosphorus: {
    label: "Phosphorus",
    unit: "mg/kg",
    explanation: "Low phosphorus can reduce root development and flowering.",
  },
  potassium: {
    label: "Potassium",
    unit: "mg/kg",
    explanation: "Low potassium can weaken stems and reduce stress tolerance.",
  },
  organic_carbon: {
    label: "Organic carbon",
    unit: "%",
    explanation:
      "Low organic carbon can reduce soil structure and nutrient retention.",
  },
};

function SoilMetricCard({ nutrient, rating, expanded, onToggle }) {
  const info = soilInfo[nutrient] || {
    label: nutrient.replace("_", " "),
    unit: "",
    explanation: "This soil measurement helps tailor crop guidance.",
  };
  const percentage =
    rating.level === "low" ? 28 : rating.level === "high" ? 82 : 62;
  const barColor =
    rating.level === "low"
      ? "bg-rose-500"
      : rating.level === "high"
        ? "bg-amber-500"
        : "bg-emerald-500";
  return (
    <button
      type="button"
      onClick={onToggle}
      className="w-full rounded-2xl bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <div className="flex items-center justify-between gap-3">
        <span className="font-black capitalize">{info.label}</span>
        <span
          className={`text-sm font-bold ${rating.level === "low" ? "text-rose-600" : rating.level === "high" ? "text-amber-600" : "text-emerald-600"}`}
        >
          {rating.level === "low"
            ? "Low"
            : rating.level === "high"
              ? "High"
              : "Adequate"}
        </span>
      </div>
      <div className="mt-3 h-2 overflow-hidden rounded-full bg-slate-100">
        <motion.div
          initial={{ width: 0 }}
          animate={{ width: `${percentage}%` }}
          transition={{ duration: 0.6 }}
          className={`h-full rounded-full ${barColor}`}
        />
      </div>
      <p className="mt-2 text-sm text-slate-500">
        {rating.value} {rating.unit || info.unit}
      </p>
      {expanded && (
        <p className="mt-2 border-t border-slate-100 pt-2 text-xs leading-5 text-slate-600">
          {info.explanation}
        </p>
      )}
    </button>
  );
}

function AssistantSteps({ steps, completed, onToggle }) {
  const iconFor = (task) =>
    /water|irrigat|moisture/i.test(task)
      ? Droplets
      : /pest|inspect|scout/i.test(task)
        ? Bug
        : Sprout;
  return (
    <div className="space-y-3">
      {steps.map((step, index) => {
        const Icon = iconFor(step.task);
        const isDone = completed[index];
        return (
          <motion.article
            key={`${step.task}-${index}`}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: index * 0.08 }}
            className={`rounded-2xl border p-4 transition ${isDone ? "border-emerald-200 bg-emerald-50" : "border-slate-200 bg-white"}`}
          >
            <div className="flex items-start gap-3">
              <div
                className={`flex h-10 w-10 shrink-0 items-center justify-center rounded-xl ${isDone ? "bg-emerald-700 text-white" : "bg-emerald-100 text-emerald-800"}`}
              >
                <Icon className="h-5 w-5" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex flex-wrap items-start justify-between gap-2">
                  <h3
                    className={`font-black ${isDone ? "text-emerald-900 line-through" : "text-slate-900"}`}
                  >
                    {step.task}
                  </h3>
                  <label className="flex items-center gap-2 text-xs font-bold text-slate-600">
                    <input
                      type="checkbox"
                      checked={Boolean(isDone)}
                      onChange={() => onToggle(index)}
                      className="h-4 w-4 accent-emerald-700"
                    />{" "}
                    {isDone ? "Done" : "Mark as done"}
                  </label>
                </div>
                <p className="mt-1 text-xs font-bold uppercase tracking-wide text-emerald-700">
                  {step.timing}
                </p>
                <p className="mt-2 text-sm leading-5 text-slate-600">
                  {step.reason}
                </p>
                <p className="mt-2 text-xs font-bold text-slate-500">
                  {step.quantity}
                </p>
              </div>
            </div>
          </motion.article>
        );
      })}
    </div>
  );
}

export default function AdvisoryPage() {
  const navigate = useNavigate();
  const { t, i18n } = useTranslation();
  const { farmId, setFarmId } = useOnboardingStore();
  const queryClient = useQueryClient();
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  const [previewDay, setPreviewDay] = useState(null);
  const [expandedSoil, setExpandedSoil] = useState(null);
  const [completedSteps, setCompletedSteps] = useState({});
  const [question, setQuestion] = useState("");
  const [chat, setChat] = useState([]);
  const [showSoilTest, setShowSoilTest] = useState(false);
  const timelineRef = useRef(null);
  const farmsQuery = useQuery({
    queryKey: ["farms"],
    queryFn: fetchFarms,
    refetchOnWindowFocus: true,
  });
  const selectedFarmId = farmId || farmsQuery.data?.[0]?.id;
  const selectedFarm = farmsQuery.data?.find(
    (farm) => Number(farm.id) === Number(selectedFarmId),
  );
  useEffect(() => {
    if (!farmId && selectedFarmId) setFarmId(selectedFarmId);
  }, [farmId, selectedFarmId, setFarmId]);
  useEffect(() => {
    const online = () => setIsOnline(true);
    const offline = () => setIsOnline(false);
    window.addEventListener("online", online);
    window.addEventListener("offline", offline);
    return () => {
      window.removeEventListener("online", online);
      window.removeEventListener("offline", offline);
    };
  }, []);
  const advisoryQuery = useQuery({
    queryKey: ["advisory", selectedFarmId, i18n.language],
    queryFn: () => fetchAdvisory(selectedFarmId, i18n.language),
    enabled: Boolean(selectedFarmId),
    initialData: getCachedAdvisory,
    refetchInterval: 24 * 60 * 60 * 1000,
    refetchOnWindowFocus: true,
  });
  const assistantQuery = useQuery({
    queryKey: [
      "advisory-assistant",
      selectedFarmId,
      i18n.language,
      advisoryQuery.data?.days_since_sowing,
      advisoryQuery.data?.soil_test_missing,
    ],
    queryFn: () => askAdvisoryAssistant(selectedFarmId),
    enabled: Boolean(selectedFarmId && advisoryQuery.data),
    retry: 1,
  });
  const soilMutation = useMutation({
    mutationFn: (payload) => saveSoilTest(selectedFarmId, payload),
    onSuccess: () => {
      setShowSoilTest(false);
      toast.success("Soil test saved. Advisory refreshed.");
      queryClient.invalidateQueries({ queryKey: ["advisory", selectedFarmId] });
      queryClient.invalidateQueries({
        queryKey: ["advisory-assistant", selectedFarmId],
      });
    },
    onError: (error) => {
      toast.error(error.response?.data?.detail || "Could not save soil test.");
    },
  });
  useEffect(() => {
    if (advisoryQuery.data && isOnline)
      localStorage.setItem(CACHE_KEY, JSON.stringify(advisoryQuery.data));
  }, [advisoryQuery.data, isOnline]);

  const data = advisoryQuery.data;
  const previewStage = useMemo(() => {
    if (!data || !Array.isArray(data.timeline) || !data.timeline.length)
      return null;
    const day = previewDay ?? data.days_since_sowing;
    return (
      data.timeline.find(
        (item) => day >= item.start_day && day <= item.end_day,
      ) || data.timeline[data.timeline.length - 1]
    );
  }, [data, previewDay]);
  const fullText = [
    assistantQuery.data?.currentStageAdvice ||
      `Current crop stage: ${data?.stage?.name || previewStage?.stage || "unknown"}.`,
    data?.soil_test_missing
      ? "Soil test is missing, so this advice is general."
      : "Soil test is on file.",
    ...(assistantQuery.data?.steps || []).map((item) => item.task),
    data?.disclaimer,
  ]
    .filter(Boolean)
    .join(" ");
  const assistantSteps = assistantQuery.data?.steps || [];
  const askQuestion = async (event) => {
    event.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || !selectedFarmId) return;
    setChat((items) => [...items, { role: "user", text: trimmed }]);
    setQuestion("");
    try {
      const response = await askAdvisoryAssistant(selectedFarmId, trimmed);
      setChat((items) => [
        ...items,
        {
          role: "assistant",
          text: response.currentStageAdvice,
          steps: response.steps,
        },
      ]);
    } catch (error) {
      toast.error(
        error.response?.data?.detail || "AgriSync could not answer right now.",
      );
    }
  };

  const timeline = Array.isArray(data?.timeline) ? data.timeline : [];
  const lastTimelineStage = timeline.at(-1);
  const progressPercent = Math.min(
    100,
    Math.max(
      0,
      ((data?.days_since_sowing || 0) / (lastTimelineStage?.end_day || 1)) *
        100,
    ),
  );
  const openMachineryPlan = () => {
    const params = new URLSearchParams();
    if (selectedFarmId) params.set("farm_id", selectedFarmId);
    if (selectedFarm?.crop_id) params.set("crop_id", selectedFarm.crop_id);
    if (selectedFarm?.sowing_date)
      params.set("sowing_date", selectedFarm.sowing_date);
    if (selectedFarm?.area_acres)
      params.set("area_acres", selectedFarm.area_acres);
    if (previewStage?.stage) params.set("stage", previewStage.stage);
    navigate(`/plan?${params.toString()}`);
  };

  const movePreview = (_event, info) => {
    if (!timelineRef.current || !data) return;
    const rect = timelineRef.current.getBoundingClientRect();
    const position = Math.max(
      0,
      Math.min(rect.width, info.point.x - rect.left),
    );
    const lastTimelineStage = data.timeline?.at(-1);
    setPreviewDay(
      Math.round((position / rect.width) * (lastTimelineStage?.end_day || 1)),
    );
  };
  if (farmsQuery.isError && !farmId) {
    return (
      <QueryMessage
        title="Could not load your farm"
        detail={
          farmsQuery.error?.response?.data?.detail ||
          "Please check that the backend is running and try again."
        }
        onRetry={() => farmsQuery.refetch()}
      />
    );
  }

  if (!farmsQuery.isLoading && !selectedFarmId) {
    return (
      <QueryMessage
        title="No farm found"
        detail="Complete the farm setup before opening crop advisory."
        actionLabel="Complete farm setup"
        onAction={() => {
          window.location.href = "/onboarding";
        }}
      />
    );
  }

  if (advisoryQuery.isError) {
    return (
      <QueryMessage
        title="Could not load crop advisory"
        detail={
          advisoryQuery.error?.response?.data?.detail ||
          "Please check that the backend is running and try again."
        }
        onRetry={() => advisoryQuery.refetch()}
      />
    );
  }

  if (farmsQuery.isLoading || advisoryQuery.isLoading || !data)
    return (
      <main className="mx-auto max-w-5xl p-5">
        <Skeleton />
      </main>
    );

  return (
    <main className="min-h-screen bg-[#f5f7f2] pb-12 text-slate-900">
      <div className="mx-auto max-w-5xl space-y-6 p-5 md:p-8">
        {!isOnline && (
          <div className="rounded-xl bg-slate-800 px-4 py-3 text-sm font-bold text-white">
            Offline - last updated {new Date().toLocaleDateString()}
          </div>
        )}
        <header className="flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-bold uppercase tracking-[0.18em] text-emerald-700">
              AgriSync
            </p>
            <h1 className="mt-1 text-3xl font-black">Crop advisory</h1>
            <p className="mt-1 text-slate-600">
              {previewDay !== null
                ? "Preview"
                : `${data.stage.name} · day ${data.days_since_sowing}`}
            </p>
          </div>
          <ListenButton
            text={fullText || data.disclaimer}
            lang={i18n.language}
            label="Listen to advisory"
            onRead={() => {}}
          />
          <button
            onClick={openMachineryPlan}
            className="rounded-xl border border-emerald-700 px-3 py-3 text-sm font-bold text-emerald-800"
          >
            Machinery Calendar
          </button>
        </header>

        {/* Irrigation and Fertigation Status */}
        {(data?.irrigation_type || selectedFarm?.irrigation_type) && (
          <div className="flex flex-wrap items-center gap-2 text-xs font-bold">
            <span className="inline-flex items-center gap-1.5 rounded-xl border border-sky-200 bg-sky-50 px-3 py-1.5 text-sky-900 shadow-sm">
              <Droplets className="h-3.5 w-3.5 text-sky-600" />
              <span>
                {t('summary.irrigation')}:{" "}
                {(data?.irrigation_type || selectedFarm?.irrigation_type) === "other"
                  ? `${t('soil.irr_other')}${data?.irrigation_type_note || selectedFarm?.irrigation_type_note ? ` (${data?.irrigation_type_note || selectedFarm?.irrigation_type_note})` : ""}`
                  : t(`soil.irr_${data?.irrigation_type || selectedFarm?.irrigation_type}`, {
                      defaultValue: data?.irrigation_type || selectedFarm?.irrigation_type,
                    })}
              </span>
            </span>
            {(data?.irrigation_type === "drip" || selectedFarm?.irrigation_type === "drip") && (
              <span className="inline-flex items-center gap-1.5 rounded-xl border border-emerald-200 bg-emerald-50 px-3 py-1.5 text-emerald-800 shadow-sm">
                <Sprout className="h-3.5 w-3.5 text-emerald-600" />
                <span>Drip Fertigation Active</span>
              </span>
            )}
          </div>
        )}
        {data.soil_test_missing && (
          <div className="flex flex-wrap items-center justify-between gap-4 rounded-2xl border border-amber-200 bg-amber-50 p-4 text-amber-950">
            <div>
              <p className="font-black">
                Add your soil test for personalised advice
              </p>
              <p className="text-sm">Get a soil test for accurate advice.</p>
            </div>
            <button
              onClick={() => setShowSoilTest(true)}
              className="min-h-11 rounded-xl bg-amber-900 px-4 font-bold text-white"
            >
              Add soil test
            </button>
          </div>
        )}
        {!data.soil_test_missing && (
          <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-4 py-3 text-sm font-bold text-emerald-900">
            Soil test on file. Recommendations use your latest submitted values.
          </div>
        )}
        <section className="rounded-3xl bg-white p-5 shadow-sm">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-black">Crop timeline</h2>
              <p className="text-sm text-slate-500">
                {previewStage?.stage || data.stage?.name}{" "}
                {previewDay !== null && "(Preview)"}
              </p>
            </div>
            <span className="text-sm font-bold text-emerald-700">
              {data.next_stage
                ? `${data.next_stage.name} in ${data.next_stage.days_until} days`
                : "Harvest stage"}
            </span>
          </div>
          <div ref={timelineRef} className="relative mt-10 h-16">
            <div className="absolute left-0 right-0 top-5 h-2 rounded-full bg-slate-200" />
            <div
              className="absolute left-0 top-5 h-2 rounded-full bg-emerald-500"
              style={{
                width: `${progressPercent}%`,
              }}
            />
            <motion.div
              drag="x"
              dragConstraints={timelineRef}
              dragElastic={0}
              onDrag={movePreview}
              onDragEnd={movePreview}
              className="absolute top-0 h-12 w-12 -translate-x-1/2 cursor-grab rounded-full border-4 border-white bg-emerald-700 shadow-lg active:cursor-grabbing"
              style={{
                left: `${progressPercent}%`,
              }}
              aria-label="Drag to preview a crop stage"
            />
            <div className="absolute inset-x-0 top-12 flex justify-between text-[11px] font-bold text-slate-500">
              <span>{timeline[0]?.stage || "Sowing"}</span>
              <span>{lastTimelineStage?.stage || "Harvest"}</span>
            </div>
          </div>
        </section>
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xl font-black">Soil health</h2>
            <span className="text-xs font-bold text-slate-500">
              Tap a value to learn more
            </span>
          </div>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            {Object.entries(data.soil_ratings || {}).map(
              ([nutrient, rating]) => (
                <SoilMetricCard
                  key={nutrient}
                  nutrient={nutrient}
                  rating={rating}
                  expanded={expandedSoil === nutrient}
                  onToggle={() =>
                    setExpandedSoil(expandedSoil === nutrient ? null : nutrient)
                  }
                />
              ),
            )}
          </div>
          {!Object.keys(data.soil_ratings || {}).length && (
            <div className="rounded-2xl bg-white p-5 text-sm text-slate-600">
              No soil measurements are available yet. Add a soil test to unlock
              nutrient-specific guidance.
            </div>
          )}
        </section>
        <section>
          <div className="mb-3 flex items-center justify-between">
            <div>
              <h2 className="text-xl font-black">AgriSync guidance</h2>
              <p className="mt-1 text-sm text-slate-500">
                {assistantQuery.data?.source === "claude"
                  ? "AI-assisted advice from your current farm context"
                  : "Rule-engine guidance using your current farm context"}
              </p>
            </div>
            {previewDay !== null && (
              <button
                className="text-sm font-bold text-emerald-700"
                onClick={() => setPreviewDay(null)}
              >
                Reset preview
              </button>
            )}
          </div>
          {assistantQuery.isLoading ? (
            <div className="rounded-2xl bg-white p-6">
              <div className="flex items-center gap-3 text-sm font-bold text-emerald-800">
                <Loader2 className="h-5 w-5 animate-spin" /> Preparing your farm
                guidance...
              </div>
              <div className="mt-4 h-3 w-2/3 animate-pulse rounded-full bg-slate-200" />
            </div>
          ) : assistantQuery.isError ? (
            <div className="rounded-2xl border border-rose-200 bg-rose-50 p-5 text-sm text-rose-800">
              Guidance could not be loaded. Your basic crop advisory remains
              available above.
              <button
                type="button"
                onClick={() => assistantQuery.refetch()}
                className="mt-3 block font-black underline"
              >
                Try again
              </button>
            </div>
          ) : (
            <>
              <div className="rounded-2xl border border-emerald-200 bg-emerald-50 p-5">
                <p className="text-xs font-black uppercase tracking-wide text-emerald-800">
                  What to do now
                </p>
                <p className="mt-2 text-lg font-black text-emerald-950">
                  {assistantQuery.data?.currentStageAdvice}
                </p>
              </div>
              <div className="mt-4">
                <AssistantSteps
                  steps={assistantSteps}
                  completed={completedSteps}
                  onToggle={(index) =>
                    setCompletedSteps((items) => ({
                      ...items,
                      [index]: !items[index],
                    }))
                  }
                />
              </div>
              {!!assistantQuery.data?.upcomingMilestones?.length && (
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  {assistantQuery.data.upcomingMilestones.map((milestone) => (
                    <div
                      key={milestone.stage}
                      className="rounded-2xl bg-white p-4 shadow-sm"
                    >
                      <p className="font-black">
                        {milestone.stage} · {milestone.daysAway} days
                      </p>
                      <p className="mt-1 text-sm text-slate-600">
                        {milestone.prep}
                      </p>
                    </div>
                  ))}
                </div>
              )}
              {!!assistantQuery.data?.warnings?.length && (
                <div className="mt-4 rounded-2xl border border-amber-200 bg-amber-50 p-4">
                  <p className="font-black text-amber-950">Watch for</p>
                  {assistantQuery.data.warnings.map((warning) => (
                    <p key={warning} className="mt-1 text-sm text-amber-900">
                      {warning}
                    </p>
                  ))}
                </div>
              )}
            </>
          )}
        </section>
        <section className="rounded-3xl bg-[#173f2b] p-5 text-white shadow-lg shadow-emerald-950/10">
          <div className="flex items-center gap-2">
            <MessageCircle className="h-5 w-5 text-emerald-200" />
            <h2 className="font-black">Ask AgriSync</h2>
          </div>
          <p className="mt-1 text-sm text-emerald-100">
            Ask a follow-up about irrigation, nutrients, pests, or timing.
          </p>
          <form onSubmit={askQuestion} className="mt-4 flex gap-2">
            <input
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              placeholder="When should I irrigate?"
              className="min-h-12 min-w-0 flex-1 rounded-xl border-0 px-4 text-slate-900 outline-none ring-2 ring-transparent focus:ring-emerald-300"
            />
            <button
              type="submit"
              disabled={!question.trim()}
              className="flex min-h-12 items-center justify-center rounded-xl bg-emerald-400 px-4 font-black text-emerald-950 disabled:opacity-50"
              aria-label="Ask AgriSync"
            >
              <Send className="h-5 w-5" />
            </button>
          </form>
          {!!chat.length && (
            <div className="mt-4 space-y-3">
              {chat.slice(-4).map((message, index) => (
                <div
                  key={`${message.role}-${index}`}
                  className={`rounded-2xl p-3 text-sm ${message.role === "user" ? "ml-8 bg-white/10" : "mr-4 bg-emerald-950/30"}`}
                >
                  <p className="font-black">
                    {message.role === "user" ? "You" : "AgriSync"}
                  </p>
                  <p className="mt-1 text-emerald-50">{message.text}</p>
                  {message.steps?.slice(0, 2).map((step) => (
                    <p
                      key={step.task}
                      className="mt-2 text-xs text-emerald-200"
                    >
                      • {step.task}
                    </p>
                  ))}
                </div>
              ))}
            </div>
          )}
        </section>
        <footer className="rounded-2xl border border-slate-200 bg-white p-4 text-center text-sm font-bold text-slate-600">
          Guidance only. Confirm with your local agriculture officer.
        </footer>
      </div>
      <AppBottomNav />
      {showSoilTest && (
        <SoilTestModal
          onClose={() => setShowSoilTest(false)}
          onSubmit={(payload) => soilMutation.mutate(payload)}
          isSaving={soilMutation.isPending}
        />
      )}
    </main>
  );
}
