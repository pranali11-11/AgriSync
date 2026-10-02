import React, { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import {
  ArrowRight,
  CalendarDays,
  CloudRain,
  Droplets,
  MapPin,
  Sprout,
  Sun,
  Tractor,
  Users,
  Wind,
} from "lucide-react";
import { useNavigate } from "react-router-dom";
import { fetchAdvisory } from "../../api/advisory";
import { fetchCrops } from "../../api/crops";
import { fetchFarms, fetchFarmerProfile } from "../../api/farmer";
import { fetchNearbyGroups } from "../../api/groups";
import { fetchWeather } from "../../api/weather";
import { useOnboardingStore } from "../../store/useOnboardingStore";
import { AppBottomNav } from "../../components/AppBottomNav";

const formatDate = (value) =>
  value
    ? new Intl.DateTimeFormat("en-IN", {
        day: "numeric",
        month: "short",
      }).format(new Date(`${value}T00:00:00`))
    : null;

function WeatherGlyph({ code }) {
  if (code >= 51) return <CloudRain className="h-8 w-8 text-emerald-200" />;
  if (code >= 1) return <Wind className="h-8 w-8 text-emerald-200" />;
  return <Sun className="h-8 w-8 text-emerald-200" />;
}

function DashboardCard({ children, className = "", delay = 0 }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
      className={`rounded-3xl border border-emerald-950/10 bg-white p-5 shadow-[0_12px_35px_rgba(20,83,45,0.08)] ${className}`}
    >
      {children}
    </motion.section>
  );
}

function QuickAction({ icon: Icon, title, status, path, onClick, delay }) {
  return (
    <motion.button
      type="button"
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, delay }}
      whileHover={{ scale: 1.02 }}
      whileTap={{ scale: 0.98 }}
      onClick={() => onClick(path)}
      className="group rounded-2xl border border-emerald-950/10 bg-white p-4 text-left shadow-[0_8px_24px_rgba(20,83,45,0.06)] transition-shadow hover:shadow-[0_14px_30px_rgba(20,83,45,0.12)]"
    >
      <div className="flex items-center justify-between">
        <span className="flex h-10 w-10 items-center justify-center rounded-xl bg-emerald-100 text-emerald-800">
          <Icon className="h-5 w-5" />
        </span>
        <ArrowRight className="h-4 w-4 text-slate-400 transition-transform group-hover:translate-x-1" />
      </div>
      <p className="mt-4 font-black text-slate-900">{title}</p>
      <p className="mt-1 text-xs font-bold text-emerald-700">{status}</p>
    </motion.button>
  );
}

export default function HomePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const [today] = useState(() => Date.now());
  const { userName, village, district, state, lat, lng, farmId } =
    useOnboardingStore();
  const farmsQuery = useQuery({ queryKey: ["farms"], queryFn: fetchFarms });
  const cropsQuery = useQuery({ queryKey: ["crops"], queryFn: fetchCrops });
  const profileQuery = useQuery({
    queryKey: ["farmer-profile"],
    queryFn: fetchFarmerProfile,
  });
  const farm =
    farmsQuery.data?.find((item) => Number(item.id) === Number(farmId)) ||
    farmsQuery.data?.[0];
  const crop = cropsQuery.data?.find(
    (item) => Number(item.id) === Number(farm?.crop_id),
  );
  const selectedFarmId = farm?.id;
  const advisoryQuery = useQuery({
    queryKey: ["advisory", selectedFarmId, "en"],
    queryFn: () => fetchAdvisory(selectedFarmId, "en"),
    enabled: Boolean(selectedFarmId),
    retry: 1,
  });
  const soilQuery = useQuery({
    queryKey: ["soil-tests", selectedFarmId],
    queryFn: async () => {
      const persisted = JSON.parse(
        localStorage.getItem("agrisync-onboarding") || "{}",
      );
      const response = await fetch(
        `${import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1"}/farms/${selectedFarmId}/soil-test`,
        {
          headers: { Authorization: `Bearer ${persisted.state?.token || ""}` },
        },
      );
      if (!response.ok) throw new Error("Soil test unavailable");
      return response.json();
    },
    enabled: Boolean(selectedFarmId),
  });
  const groupsQuery = useQuery({
    queryKey: ["nearby-groups", "home"],
    queryFn: () => fetchNearbyGroups({ radius_km: 10 }),
    retry: 1,
  });
  const weatherQuery = useQuery({
    queryKey: [
      "weather",
      profileQuery.data?.latitude,
      profileQuery.data?.longitude,
      lat,
      lng,
    ],
    queryFn: () =>
      fetchWeather(
        profileQuery.data?.latitude ?? lat,
        profileQuery.data?.longitude ?? lng,
      ),
    staleTime: 30 * 60 * 1000,
    retry: 1,
  });
  const location = [
    profileQuery.data?.village || village,
    profileQuery.data?.district || district,
    profileQuery.data?.state || state,
  ]
    .filter(Boolean)
    .join(", ");
  const daysSinceSowing = farm?.sowing_date
    ? Math.max(
        0,
        Math.floor(
          (today - new Date(`${farm.sowing_date}T00:00:00`).getTime()) /
            86400000,
        ),
      )
    : 0;
  const currentStage =
    advisoryQuery.data?.stage?.name || farm?.current_stage || t('home.setup_needed');
  const daysToHarvest = advisoryQuery.data?.timeline?.at(-1)?.end_day
    ? Math.max(0, advisoryQuery.data.timeline.at(-1).end_day - daysSinceSowing)
    : null;
  const priority = advisoryQuery.data?.recommendations?.find(
    (item) => item.status === "suggested" || item.status === "coming_up",
  );
  const soilStatus = soilQuery.data?.length
    ? t('home.soil_on_file')
    : t('home.soil_needed');
  const weather = weatherQuery.data;
  const recommendationCount = advisoryQuery.data?.recommendations?.length || 0;
  const cropName = crop?.name || farm?.crop_name || t('home.your_crop');
  const greeting = userName
    ? t('home.greeting', { name: userName })
    : t('home.greeting_generic');
  const formattedSowingDate = formatDate(farm?.sowing_date) || t('home.not_set');

  const quickActions = useMemo(
    () => [
      {
        icon: Sprout,
        title: t('home.action_advisory_title'),
        status: recommendationCount
          ? t('home.action_advisory_status', { count: recommendationCount })
          : t('home.action_advisory_status_empty'),
        path: "/advisory",
      },
      {
        icon: Tractor,
        title: t('home.action_machinery_title'),
        status: t('home.action_machinery_status'),
        path: "/plan",
      },
      {
        icon: Users,
        title: t('home.action_groups_title'),
        status: groupsQuery.data?.length
          ? t('home.action_groups_status', { count: groupsQuery.data.length })
          : t('home.action_groups_status_empty'),
        path: "/groups/nearby",
      },
      {
        icon: Droplets,
        title: t('home.action_soil_title'),
        status: soilStatus,
        path: "/advisory",
      },
    ],
    [t, groupsQuery.data?.length, recommendationCount, soilStatus],
  );

  return (
    <main className="min-h-screen bg-[#eef5ed] pb-24 text-slate-900">
      <div className="mx-auto max-w-6xl space-y-5 p-5 md:p-8">
        <motion.header
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex flex-wrap items-start justify-between gap-4"
        >
          <div>
            <p className="text-xs font-black uppercase tracking-[0.24em] text-emerald-700">
              {t('home.brand_tagline')}
            </p>
            <h1 className="mt-2 text-3xl font-black tracking-tight md:text-4xl">
              {greeting}
            </h1>
            <p className="mt-1 text-slate-600">
              {t('home.subgreeting')}
            </p>
          </div>
          <div className="flex items-center gap-3 rounded-2xl border border-emerald-950/10 bg-[#173f2b] px-4 py-3 text-white shadow-lg shadow-emerald-950/10">
            <WeatherGlyph code={weather?.weatherCode} />
            <div>
              <p className="text-2xl font-black">
                {weather ? `${weather.temperature}°C` : "--"}
              </p>
              <p className="text-xs font-bold text-emerald-100">
                {weather
                  ? t('home.rain_chance', { pct: weather.rainChance })
                  : t('home.weather_unavailable')}
              </p>
            </div>
          </div>
        </motion.header>
        <DashboardCard
          delay={0.1}
          className="overflow-hidden bg-[#173f2b] text-white"
        >
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-xs font-black uppercase tracking-[0.2em] text-emerald-200">
                {t('home.farm_glance')}
              </p>
              <h2 className="mt-2 text-2xl font-black">{cropName}</h2>
              <p className="mt-1 flex items-center gap-1 text-sm text-emerald-100">
                <MapPin className="h-4 w-4" />
                {location || t('home.location_fallback')}
              </p>
            </div>
            <Sprout className="h-10 w-10 text-emerald-200" />
          </div>
          <div className="mt-6 grid grid-cols-2 gap-3 md:grid-cols-4">
            {[
              [t('home.sowing_date'), formattedSowingDate],
              [t('home.current_stage'), currentStage],
              [t('home.days_growing'), t('home.days_label', { count: daysSinceSowing })],
              [
                t('home.days_to_harvest'),
                daysToHarvest == null
                  ? t('home.calculating')
                  : t('home.days_label', { count: daysToHarvest }),
              ],
            ].map(([label, value]) => (
              <div key={label} className="rounded-2xl bg-white/10 p-3">
                <p className="text-[11px] font-bold uppercase tracking-wide text-emerald-200">
                  {label}
                </p>
                <p className="mt-1 text-sm font-black">{value}</p>
              </div>
            ))}
          </div>
        </DashboardCard>
        <section>
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-xl font-black">{t('home.quick_actions')}</h2>
            <span className="text-xs font-bold text-slate-500">
              {t('home.live_status')}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4">
            {quickActions.map((action, index) => (
              <QuickAction
                key={action.title}
                {...action}
                delay={0.18 + index * 0.1}
                onClick={navigate}
              />
            ))}
          </div>
        </section>
        <DashboardCard delay={0.6} className="border-amber-200 bg-amber-50">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-start gap-3">
              <div className="rounded-xl bg-amber-200 p-2 text-amber-900">
                <CalendarDays className="h-5 w-5" />
              </div>
              <div>
                <p className="text-xs font-black uppercase tracking-[0.18em] text-amber-800">
                  {t('home.todays_priority')}
                </p>
                <h2 className="mt-1 text-lg font-black text-amber-950">
                  {priority?.guidance_text || t('home.priority_fallback')}
                </h2>
                <p className="mt-1 text-sm text-amber-900">
                  {priority
                    ? `${priority.input_category} · ${currentStage}`
                    : t('home.advisory_engine_note')}
                </p>
              </div>
            </div>
            <button
              type="button"
              onClick={() => navigate("/advisory")}
              className="inline-flex items-center gap-2 rounded-xl bg-amber-900 px-4 py-3 text-sm font-black text-white"
            >
              {t('home.open_advisory')} <ArrowRight className="h-4 w-4" />
            </button>
          </div>
        </DashboardCard>
      </div>
      <AppBottomNav />
    </main>
  );
}
