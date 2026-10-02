import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { Copy, MapPin, Plus, Users } from "lucide-react";
import confetti from "canvas-confetti";
import toast from "react-hot-toast";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import {
  createGroup,
  fetchGroup,
  fetchMyGroups,
  fetchNearbyGroups,
  joinGroup,
  previewGroup,
} from "../../api/groups";
import { fetchCrops } from "../../api/crops";
import { fetchFarms } from "../../api/farmer";
import { fetchMachines } from "../../api/resources";
import { useGroupWebSocket } from "../../hooks/useGroupWebSocket";
import { useOnboardingStore } from "../../store/useOnboardingStore";
import { AppBottomNav } from "../../components/AppBottomNav";

const rupees = (amount) =>
  new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 }).format(
    amount || 0,
  );

function ProgressRing({ count, min }) {
  const progress = Math.min(100, (count / Math.max(1, min)) * 100);
  return (
    <div className="relative h-20 w-20">
      <svg viewBox="0 0 40 40" className="h-full w-full -rotate-90">
        <circle
          cx="20"
          cy="20"
          r="16"
          fill="none"
          stroke="#e2e8f0"
          strokeWidth="4"
        />
        <motion.circle
          initial={{ pathLength: 0 }}
          animate={{ pathLength: progress / 100 }}
          cx="20"
          cy="20"
          r="16"
          fill="none"
          stroke="#15803d"
          strokeWidth="4"
          strokeLinecap="round"
          pathLength="1"
        />
      </svg>
      <span className="absolute inset-0 flex items-center justify-center text-xs font-black">
        {count}/{min}
      </span>
    </div>
  );
}

function GroupCard({ group, onOpen }) {
  return (
    <motion.button
      type="button"
      whileTap={{ scale: 0.98 }}
      onClick={() => onOpen(group.id)}
      className="w-full rounded-2xl border border-slate-200 bg-white p-4 text-left shadow-sm transition hover:-translate-y-0.5 hover:shadow-md"
    >
      <div className="flex items-center gap-4">
        <ProgressRing count={group.member_count} min={group.min_farmers} />
        <div className="min-w-0 flex-1">
          <h3 className="font-black">
            {group.name ||
              group.machine?.type ||
              `Machine #${group.machine_id}`}
          </h3>
          {group.crop_focus && (
            <p className="text-xs font-bold text-emerald-700">
              {group.crop_focus} growers
            </p>
          )}
          <p className="text-sm text-slate-600">
            {group.scheduled_date} ·{" "}
            {group.distance_km
              ? `${group.distance_km} km`
              : `${group.total_acres}/${group.max_acres} acres`}
          </p>
          <div className="mt-2 h-1.5 rounded-full bg-slate-100">
            <div
              className="h-full rounded-full bg-emerald-500"
              style={{
                width: `${Math.min(100, (group.total_acres / group.max_acres) * 100)}%`,
              }}
            />
          </div>
        </div>
      </div>
    </motion.button>
  );
}

export function NearbyGroups() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { selectedCropName, village, district, state } = useOnboardingStore();
  const query = useQuery({
    queryKey: ["nearby-groups"],
    queryFn: () => fetchNearbyGroups({ radius_km: 10 }),
  });
  return (
    <main className="min-h-screen bg-[#f5f7f2] p-5 pb-24">
      <div className="mx-auto max-w-xl space-y-5">
        <header>
          <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">
            {t('app.name')}
          </p>
          <h1 className="text-3xl font-black">{t('groups.nearby')}</h1>
        </header>
        {query.isLoading ? (
          <div className="animate-pulse space-y-3">
            <div className="h-24 rounded-2xl bg-slate-200" />
            <div className="h-24 rounded-2xl bg-slate-200" />
          </div>
        ) : query.isError ? (
          <div className="rounded-3xl bg-rose-50 p-6 text-rose-800">
            {t('groups.load_error')}{" "}
            <button
              type="button"
              onClick={() => query.refetch()}
              className="font-black underline"
            >
              {t('common.try_again')}
            </button>
          </div>
        ) : query.data?.length ? (
          query.data.map((group) => (
            <GroupCard
              key={group.id}
              group={group}
              onOpen={(id) => navigate(`/groups/${id}`)}
            />
          ))
        ) : (
          <motion.div
            animate={{ y: [0, -5, 0], scale: [1, 1.02, 1] }}
            transition={{ duration: 3, repeat: Infinity }}
            className="relative overflow-hidden rounded-3xl border border-emerald-200 bg-gradient-to-br from-emerald-50 to-white p-8 text-center shadow-sm"
          >
            <div className="mx-auto flex h-24 w-24 items-center justify-center rounded-[2rem] bg-emerald-100 text-emerald-700 shadow-inner">
              <Users className="h-12 w-12" />
            </div>
            <div className="pointer-events-none absolute left-8 top-8 h-3 w-3 rounded-full bg-amber-300" />
            <div className="pointer-events-none absolute right-12 top-16 h-4 w-4 rounded-full bg-emerald-200" />
            <p className="mt-5 text-xl font-black">{t('groups.no_groups_heading')}</p>
            <p className="mx-auto mt-2 max-w-sm text-sm leading-6 text-slate-600">
              {t('groups.no_groups_body', { location: village || district || state || t('groups.your_farm') })}
            </p>
            <div className="mx-auto mt-5 max-w-sm rounded-2xl bg-white p-4 text-left shadow-sm">
              <p className="text-xs font-black uppercase tracking-wide text-emerald-700">
                {t('groups.suggested_community')}
              </p>
              <p className="mt-1 font-black">
                {selectedCropName ? t('groups.local_growers', { crop: selectedCropName }) : t('groups.growers')}
              </p>
              <p className="mt-1 flex items-center gap-1 text-xs text-slate-500">
                <MapPin className="h-3 w-3" /> {t('groups.within_km')}
              </p>
            </div>
            <button
              type="button"
              onClick={() => navigate("/groups/new")}
              className="mt-5 inline-flex min-h-12 items-center gap-2 rounded-xl bg-emerald-800 px-5 font-black text-white transition hover:bg-emerald-700 active:scale-[0.97]"
            >
              <Plus className="h-5 w-5" /> {t('groups.start')}
            </button>
          </motion.div>
        )}
      </div>
      <AppBottomNav />
    </main>
  );
}

function GroupDetail({ id }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [acres, setAcres] = useState(1);
  const query = useQuery({
    queryKey: ["group", id],
    queryFn: () => fetchGroup(id),
    refetchInterval: 10000,
  });
  const live = useGroupWebSocket(id);
  const group = query.data;
  const preview = useQuery({
    queryKey: ["group-preview", id, acres],
    queryFn: () => previewGroup(id, acres),
    enabled: Boolean(group),
  });
  const join = useMutation({
    mutationFn: () =>
      joinGroup(id, { farm_id: group.members[0]?.farm_id, acres }),
    onSuccess: (data) => {
      queryClient.setQueryData(["group", id], data);
      if (data.status === "confirmed") confetti({ particleCount: 100 });
      toast.success(
        data.status === "confirmed"
          ? "Group confirmed!"
          : "You joined the group",
      );
    },
    onError: (error) =>
      toast.error(error.response?.data?.detail || "Could not join group"),
  });
  if (query.isLoading)
    return (
      <main className="mx-auto max-w-xl animate-pulse p-5">
        <div className="h-32 rounded-2xl bg-slate-200" />
        <div className="mt-4 h-52 rounded-2xl bg-slate-200" />
      </main>
    );
  if (query.isError || !group)
    return <main className="p-6 font-bold">Could not load this group.</main>;
  const share = preview.data?.share_amount || 0;
  const message = encodeURIComponent(
    `Join my AgriSync group for ${group.machine?.type || "farm machine"} on ${group.scheduled_date}. Current share: Rs ${rupees(share)}. ${window.location.href}`,
  );
  return (
    <main className="min-h-screen bg-[#f5f7f2] p-5 pb-24">
      <div className="mx-auto max-w-xl space-y-5">
        <header className="flex items-center justify-between">
          <div>
            <p className="text-sm font-bold uppercase tracking-widest text-emerald-700">
              {t('groups.group_booking')}
            </p>
            <h1 className="text-2xl font-black">
              {group.name || group.machine?.type}
            </h1>
            <p className="text-slate-600">
              {group.scheduled_date} · {group.status}
            </p>
          </div>
          <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-black text-emerald-700">
            {live === "live" ? t('groups.live') : t('groups.reconnecting')}
          </span>
        </header>
        <section className="rounded-3xl bg-white p-5 shadow-sm">
          <div className="flex items-center gap-5">
            <ProgressRing count={group.member_count} min={group.min_farmers} />
            <div>
              <p className="text-2xl font-black">Rs {rupees(share)}</p>
              <p className="text-sm text-slate-600">{t('groups.your_share')}</p>
              <p className="font-bold text-emerald-700">
                {t('groups.you_save', { amount: rupees(preview.data?.savings) })}
              </p>
            </div>
          </div>
          <label className="mt-6 block text-sm font-bold">
            {t('groups.your_acres', { count: acres })}
            <input
              type="range"
              min="0.1"
              max={Math.max(0.1, group.acres_left)}
              step="0.1"
              value={acres}
              onChange={(event) => setAcres(Number(event.target.value))}
              className="mt-2 w-full"
            />
          </label>
          <button
            disabled={join.isPending || group.status !== "open"}
            onClick={() => join.mutate()}
            className="mt-5 min-h-12 w-full rounded-xl bg-emerald-700 font-black text-white disabled:opacity-50"
          >
            {t('groups.join_for', { amount: rupees(share) })}
          </button>
        </section>
        <section className="rounded-3xl bg-white p-5 shadow-sm">
          <h2 className="font-black">{t('groups.members')}</h2>
          <div className="mt-3 space-y-3">
            {group.members.map((member) => (
              <div key={member.id} className="flex items-center gap-3">
                <span className="flex h-9 w-9 items-center justify-center rounded-full bg-emerald-100 font-black text-emerald-800">
                  {member.first_name?.slice(0, 2).toUpperCase()}
                </span>
                <div className="flex-1">
                  <p className="font-bold">{member.first_name}</p>
                  <p className="text-xs text-slate-500">
                    {member.village || t('groups.village_fallback')} · {member.acres} acres
                  </p>
                </div>
                <span className="font-bold">
                  Rs {rupees(member.share_amount)}
                </span>
              </div>
            ))}
          </div>
        </section>
        <div className="flex gap-2">
          <a
            href={`https://wa.me/?text=${message}`}
            target="_blank"
            rel="noreferrer"
            className="flex flex-1 items-center justify-center rounded-xl bg-green-600 p-3 font-bold text-white"
          >
            {t('groups.share_whatsapp')}
          </a>
          <button
            type="button"
            onClick={() => navigator.clipboard.writeText(window.location.href)}
            className="rounded-xl border p-3"
            aria-label="Copy link"
          >
            <Copy className="h-5 w-5" />
          </button>
        </div>
        <button
          type="button"
          onClick={() => navigate("/groups/nearby")}
          className="w-full p-3 text-sm font-bold text-slate-600"
        >
          {t('groups.find_more')}
        </button>
      </div>
      <AppBottomNav />
    </main>
  );
}

export function GroupDetailPage() {
  const { id } = useParams();
  return <GroupDetail id={id} />;
}

export function MineGroups() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const query = useQuery({ queryKey: ["my-groups"], queryFn: fetchMyGroups });
  return (
    <main className="min-h-screen bg-[#f5f7f2] p-5 pb-24">
      <div className="mx-auto max-w-xl space-y-4">
        <header>
          <p className="text-xs font-black uppercase tracking-widest text-emerald-700">
            {t('app.name')}
          </p>
          <h1 className="mt-1 text-3xl font-black">{t('groups.mine')}</h1>
        </header>
        {query.isLoading ? (
          <div className="h-32 animate-pulse rounded-2xl bg-slate-200" />
        ) : query.data?.length ? (
          query.data.map((group) => (
            <GroupCard
              key={group.id}
              group={group}
              onOpen={(id) => navigate(`/groups/${id}`)}
            />
          ))
        ) : (
          <div className="rounded-3xl bg-white p-8 text-center shadow-sm">
            <Users className="mx-auto h-10 w-10 text-emerald-600" />
            <p className="mt-3 font-bold">{t('groups.not_joined')}</p>
            <button
              type="button"
              onClick={() => navigate("/groups/nearby")}
              className="mt-4 rounded-xl bg-emerald-700 px-4 py-3 font-bold text-white"
            >
              {t('groups.find_nearby')}
            </button>
          </div>
        )}
      </div>
      <AppBottomNav />
    </main>
  );
}

export function NewGroup() {
  const { t } = useTranslation();
  const [search] = useSearchParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { farmId, selectedCropName } = useOnboardingStore();
  const [form, setForm] = useState({
    name: "",
    description: "",
    crop_focus: selectedCropName || "",
    radius_km: "10",
    scheduled_date: search.get("date") || "",
    machine_id: search.get("machine_id") || "",
    acres: "1",
  });
  const farms = useQuery({ queryKey: ["farms"], queryFn: fetchFarms });
  const machines = useQuery({
    queryKey: ["machines", "group-form"],
    queryFn: () => fetchMachines({ radius_km: 50, verified_only: true }),
  });
  const crops = useQuery({ queryKey: ["crops"], queryFn: fetchCrops });
  const create = useMutation({
    mutationFn: createGroup,
    onSuccess: (group) => {
      queryClient.invalidateQueries({ queryKey: ["nearby-groups"] });
      queryClient.invalidateQueries({ queryKey: ["my-groups"] });
      toast.success("Group created. Farmers nearby can now join.");
      navigate(`/groups/${group.id}`);
    },
    onError: (error) =>
      toast.error(error.response?.data?.detail || "Could not create group"),
  });
  const update = (event) =>
    setForm((current) => ({
      ...current,
      [event.target.name]: event.target.value,
    }));
  const submit = (event) => {
    event.preventDefault();
    create.mutate({
      ...form,
      farm_id: farmId || farms.data?.[0]?.id,
      machine_id: Number(form.machine_id),
      acres: Number(form.acres),
      min_farmers: 2,
      max_acres: Number(form.acres) * 10,
      radius_km: Number(form.radius_km),
    });
  };
  return (
    <main className="min-h-screen bg-[#f5f7f2] p-5 pb-24">
      <motion.form
        initial={{ y: 20, opacity: 0 }}
        animate={{ y: 0, opacity: 1 }}
        onSubmit={submit}
        className="mx-auto max-w-xl space-y-5 rounded-3xl bg-white p-5 shadow-xl"
      >
        <header className="flex items-start justify-between">
          <div>
            <p className="text-xs font-black uppercase tracking-widest text-emerald-700">
              {t('groups.community')}
            </p>
            <h1 className="mt-1 text-2xl font-black">{t('groups.new_title')}</h1>
            <p className="mt-1 text-sm text-slate-500">
              {t('groups.new_subtitle')}
            </p>
          </div>
          <button
            type="button"
            onClick={() => navigate(-1)}
            aria-label="Close"
            className="text-2xl"
          >
            x
          </button>
        </header>
        <div className="space-y-3">
          <label className="block text-sm font-bold">
            {t('groups.group_name_label')}
            <input
              required
              name="name"
              value={form.name}
              onChange={update}
              placeholder={`${selectedCropName || t('groups.any_crop')} ${t('groups.growers')} - local group`}
              className="mt-1 min-h-11 w-full rounded-xl border px-3"
            />
          </label>
          <label className="block text-sm font-bold">
            {t('groups.description_label')}
            <textarea
              name="description"
              value={form.description}
              onChange={update}
              rows="3"
              placeholder={t('groups.description_placeholder')}
              className="mt-1 w-full rounded-xl border px-3 py-2"
            />
          </label>
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="text-sm font-bold">
              {t('groups.crop_focus_label')}
              <select
                name="crop_focus"
                value={form.crop_focus}
                onChange={update}
                className="mt-1 min-h-11 w-full rounded-xl border px-3"
              >
                <option value="">{t('groups.any_crop')}</option>
                {crops.data?.map((crop) => (
                  <option key={crop.id} value={crop.name}>
                    {crop.name}
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-bold">
              {t('groups.radius_label')}
              <input
                required
                type="number"
                min="1"
                max="100"
                name="radius_km"
                value={form.radius_km}
                onChange={update}
                className="mt-1 min-h-11 w-full rounded-xl border px-3"
              />
            </label>
            <label className="text-sm font-bold">
              {t('groups.machine_label')}
              <select
                required
                name="machine_id"
                value={form.machine_id}
                onChange={update}
                className="mt-1 min-h-11 w-full rounded-xl border px-3"
              >
                <option value="">{t('groups.choose_machine')}</option>
                {machines.data?.items?.map((machine) => (
                  <option key={machine.id} value={machine.id}>
                    {machine.machine_type.name} - {machine.distance_km} km
                  </option>
                ))}
              </select>
            </label>
            <label className="text-sm font-bold">
              {t('groups.date_label')}
              <input
                required
                type="date"
                name="scheduled_date"
                value={form.scheduled_date}
                onChange={update}
                className="mt-1 min-h-11 w-full rounded-xl border px-3"
              />
            </label>
            <label className="text-sm font-bold">
              {t('groups.acres_label')}
              <input
                required
                type="number"
                min="0.1"
                name="acres"
                value={form.acres}
                onChange={update}
                className="mt-1 min-h-11 w-full rounded-xl border px-3"
              />
            </label>
          </div>
        </div>
        <button
          type="submit"
          disabled={create.isPending || machines.isLoading}
          className="min-h-12 w-full rounded-xl bg-emerald-800 font-black text-white transition hover:bg-emerald-700 active:scale-[0.97] disabled:opacity-50"
        >
          {create.isPending ? t('groups.creating') : t('groups.create_group')}
        </button>
      </motion.form>
      <AppBottomNav />
    </main>
  );
}
