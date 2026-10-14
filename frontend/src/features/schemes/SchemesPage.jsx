import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Search,
  Filter,
  Building2,
  Calendar,
  ExternalLink,
  Check,
  ChevronRight,
  Bell,
} from "lucide-react";
import toast from "react-hot-toast";
import { motion } from "framer-motion";
import { AppBottomNav } from "../../components/AppBottomNav";
import api from "../../api/axios";

const fetchSchemes = async (params) => {
  const queryParams = new URLSearchParams();
  if (params.crop) queryParams.append("crop", params.crop);
  if (params.state) queryParams.append("state", params.state);
  if (params.status) queryParams.append("status", params.status);
  if (params.search) queryParams.append("search", params.search);
  if (params.showAll) queryParams.append("show_all", "true");
  if (params.deadlineSoon) queryParams.append("deadline_soon", "true");

  const response = await api.get(`/schemes?${queryParams}`);
  return response.data;
};

const fetchSchemeDetail = async (id) => {
  const response = await api.get(`/schemes/${id}`);
  return response.data;
};

const updateSchemeNotification = async ({ id, enabled }) => {
  const response = await api.put(`/schemes/${id}/notify`, { enabled });
  return response.data;
};

export default function SchemesPage() {
  const { t, i18n } = useTranslation();
  const queryClient = useQueryClient();
  const [selectedScheme, setSelectedScheme] = useState(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [statusFilter, setStatusFilter] = useState("");
  const [levelFilter, setLevelFilter] = useState("");
  const [showAll, setShowAll] = useState(false);
  const [deadlineSoon, setDeadlineSoon] = useState(false);
  const [checkedDocs, setCheckedDocs] = useState({});

  const {
    data: schemes,
    isLoading,
    error,
    refetch,
  } = useQuery({
    queryKey: [
      "schemes",
      searchQuery,
      statusFilter,
      levelFilter,
      showAll,
      deadlineSoon,
    ],
    queryFn: () =>
      fetchSchemes({
        status: statusFilter || undefined,
        search: searchQuery || undefined,
        showAll,
        deadlineSoon,
      }),
  });

  const { data: schemeDetail, isLoading: detailLoading } = useQuery({
    queryKey: ["scheme-detail", selectedScheme?.id],
    queryFn: () => fetchSchemeDetail(selectedScheme.id),
    enabled: !!selectedScheme,
  });

  const notificationMutation = useMutation({
    mutationFn: updateSchemeNotification,
    onSuccess: (_, variables) => {
      queryClient.invalidateQueries({ queryKey: ["schemes"] });
      queryClient.invalidateQueries({
        queryKey: ["scheme-detail", variables.id],
      });
      toast.success(
        t(
          variables.enabled
            ? "schemes.notify_enabled"
            : "schemes.notify_disabled",
        ),
      );
    },
    onError: () => toast.error(t("schemes.notify_error")),
  });

  const handleSearch = (e) => {
    e.preventDefault();
    refetch();
  };

  const handleSchemeClick = (scheme) => {
    setSelectedScheme(scheme);
    setCheckedDocs({});
  };

  const toggleDocCheck = (doc) => {
    setCheckedDocs((prev) => ({
      ...prev,
      [doc]: !prev[doc],
    }));
  };

  const localizedName = (scheme) =>
    i18n.language.startsWith("hi")
      ? scheme.name_hi || scheme.name
      : i18n.language.startsWith("mr")
        ? scheme.name_mr || scheme.name
        : scheme.name;
  const localizedSummary = (scheme) =>
    i18n.language.startsWith("hi")
      ? scheme.short_description_hi || scheme.short_description
      : i18n.language.startsWith("mr")
        ? scheme.short_description_mr || scheme.short_description
        : scheme.short_description;
  const formatDate = (value) =>
    new Date(`${value.slice(0, 10)}T00:00:00`).toLocaleDateString(
      i18n.language,
    );
  const statusLabel = (value) => t(`schemes.status_${value}`);

  const groupedSchemes = React.useMemo(() => {
    if (!schemes) return { central: [], state: [] };
    const filtered = levelFilter
      ? schemes.filter((s) => s.level === levelFilter)
      : schemes;
    return {
      central: filtered.filter((s) => s.level === "central"),
      state: filtered.filter((s) => s.level === "state"),
    };
  }, [schemes, levelFilter]);

  if (isLoading) {
    return (
      <main className="min-h-screen bg-[#f5f7f2] p-5 pb-20">
        <div className="mx-auto max-w-xl animate-pulse">
          <div className="h-20 rounded-2xl bg-slate-200" />
          <div className="mt-4 h-48 rounded-2xl bg-slate-200" />
        </div>
        <AppBottomNav />
      </main>
    );
  }

  if (error) {
    return (
      <main className="min-h-screen bg-[#f5f7f2] p-5 pb-20">
        <div className="mx-auto max-w-xl rounded-3xl bg-white p-6 text-center shadow-sm">
          <h1 className="text-xl font-black">{t("schemes.load_error")}</h1>
          <p className="mt-2 text-sm text-slate-600">
            {t("schemes.connection_error")}
          </p>
          <button
            onClick={() => refetch()}
            className="mt-5 rounded-xl bg-emerald-700 px-5 py-3 font-bold text-white"
          >
            {t("common.try_again")}
          </button>
        </div>
        <AppBottomNav />
      </main>
    );
  }

  if (selectedScheme) {
    return (
      <main className="min-h-screen bg-[#f5f7f2] p-5 pb-20">
        <div className="mx-auto max-w-xl">
          <button
            onClick={() => setSelectedScheme(null)}
            className="mb-4 flex items-center gap-2 font-bold text-emerald-700"
          >
            <ChevronRight className="h-5 w-5 rotate-180" />
            {t("schemes.back_to_list")}
          </button>

          {detailLoading ? (
            <div className="h-64 animate-pulse rounded-2xl bg-slate-200" />
          ) : schemeDetail ? (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-4"
            >
              <div className="rounded-2xl bg-white p-5 shadow-sm">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <span className="rounded-full bg-emerald-100 px-3 py-1 text-xs font-black text-emerald-800">
                      {schemeDetail.level === "central"
                        ? t("schemes.central")
                        : t("schemes.state")}
                    </span>
                    <h1 className="mt-3 text-2xl font-black">
                      {localizedName(schemeDetail)}
                    </h1>
                    <p className="mt-2 text-sm text-slate-600">
                      {schemeDetail.department}
                    </p>
                  </div>
                </div>
                <p className="mt-4 text-sm font-medium text-slate-700">
                  {localizedSummary(schemeDetail)}
                </p>

                {schemeDetail.deadline && (
                  <div className="mt-4 flex items-center gap-2 rounded-xl bg-amber-50 p-3 text-sm font-bold text-amber-900">
                    <Calendar className="h-4 w-4" />
                    {t("schemes.deadline")}: {formatDate(schemeDetail.deadline)}
                  </div>
                )}

                {schemeDetail.deadline &&
                  new Date(`${schemeDetail.deadline}T00:00:00`) >=
                    new Date(new Date().toDateString()) &&
                  schemeDetail.status !== "closed" && (
                    <label className="mt-3 flex cursor-pointer items-center gap-3 rounded-xl border p-3 text-sm font-bold">
                      <input
                        type="checkbox"
                        checked={schemeDetail.notify_enabled}
                        disabled={notificationMutation.isPending}
                        onChange={(event) =>
                          notificationMutation.mutate({
                            id: schemeDetail.id,
                            enabled: event.target.checked,
                          })
                        }
                        className="h-5 w-5 accent-emerald-700"
                      />
                      <Bell className="h-4 w-4 text-emerald-700" />
                      {t("schemes.notify_me")}
                    </label>
                  )}

                <a
                  href={schemeDetail.official_link}
                  target="_blank"
                  rel="noreferrer"
                  className="mt-4 flex items-center justify-center gap-2 rounded-xl bg-emerald-700 px-4 py-3 font-bold text-white"
                >
                  {t("schemes.official_link")}{" "}
                  <ExternalLink className="h-4 w-4" />
                </a>
              </div>

              <div className="rounded-2xl bg-white p-5 shadow-sm">
                <h2 className="text-lg font-black">
                  {t("schemes.eligibility")}
                </h2>
                <p className="mt-2 text-sm text-slate-700">
                  {schemeDetail.eligibility_text}
                </p>
              </div>

              <div className="rounded-2xl bg-white p-5 shadow-sm">
                <h2 className="text-lg font-black">{t("schemes.benefits")}</h2>
                <p className="mt-2 text-sm text-slate-700">
                  {schemeDetail.benefits_text}
                </p>
              </div>

              <div className="rounded-2xl bg-white p-5 shadow-sm">
                <h2 className="text-lg font-black">
                  {t("schemes.required_documents")}
                </h2>
                <div className="mt-3 space-y-2">
                  {schemeDetail.required_documents.map((doc) => (
                    <label
                      key={doc}
                      className="flex cursor-pointer items-center gap-3 rounded-xl border p-3 hover:bg-slate-50"
                    >
                      <input
                        type="checkbox"
                        checked={checkedDocs[doc] || false}
                        onChange={() => toggleDocCheck(doc)}
                        className="h-5 w-5 accent-emerald-700"
                      />
                      <span className="text-sm font-medium">{doc}</span>
                      {checkedDocs[doc] && (
                        <Check className="ml-auto h-4 w-4 text-emerald-700" />
                      )}
                    </label>
                  ))}
                </div>
              </div>

              <div className="rounded-2xl bg-white p-5 shadow-sm">
                <h2 className="text-lg font-black">
                  {t("schemes.how_to_apply")}
                </h2>
                <p className="mt-2 text-sm text-slate-700">
                  {schemeDetail.application_process_text}
                </p>
              </div>

              <div className="rounded-2xl bg-amber-50 p-4 text-sm">
                <p className="font-bold text-amber-900">
                  {t("schemes.last_verified")}:{" "}
                  {new Date(schemeDetail.last_verified_on).toLocaleDateString(
                    i18n.language,
                  )}
                </p>
                <p className="mt-1 text-amber-800">
                  {t("schemes.verify_official")}
                </p>
              </div>
            </motion.div>
          ) : null}
        </div>
        <AppBottomNav />
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#f5f7f2] p-5 pb-20">
      <div className="mx-auto max-w-xl space-y-4">
        <header>
          <h1 className="text-3xl font-black">{t("schemes.title")}</h1>
        </header>

        <form onSubmit={handleSearch} className="flex gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 h-5 w-5 -translate-y-1/2 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={t("schemes.search_placeholder")}
              className="w-full rounded-xl border px-10 py-3"
            />
          </div>
          <button
            type="submit"
            aria-label={t("schemes.search")}
            className="rounded-xl bg-emerald-700 px-4 font-bold text-white"
          >
            <Filter className="h-5 w-5" />
          </button>
        </form>

        <div className="flex flex-wrap gap-2">
          <select
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
            className="rounded-xl border px-3 py-2 text-sm font-bold"
          >
            <option value="">{t("schemes.all_status")}</option>
            <option value="active">{t("schemes.status_active")}</option>
            <option value="upcoming">{t("schemes.status_upcoming")}</option>
            <option value="closed">{t("schemes.status_closed")}</option>
          </select>
          <select
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
            className="rounded-xl border px-3 py-2 text-sm font-bold"
          >
            <option value="">{t("schemes.all_levels")}</option>
            <option value="central">{t("schemes.central")}</option>
            <option value="state">{t("schemes.state")}</option>
          </select>
          <label className="flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-bold">
            <input
              type="checkbox"
              checked={showAll}
              onChange={(e) => setShowAll(e.target.checked)}
              className="h-4 w-4 accent-emerald-700"
            />
            {t("schemes.show_all")}
          </label>
          <label className="flex items-center gap-2 rounded-xl border px-3 py-2 text-sm font-bold">
            <input
              type="checkbox"
              checked={deadlineSoon}
              onChange={(e) => setDeadlineSoon(e.target.checked)}
              className="h-4 w-4 accent-emerald-700"
            />
            {t("schemes.deadline_soon")}
          </label>
        </div>

        {groupedSchemes.central.length > 0 && (
          <section>
            <h2 className="mb-3 text-lg font-black">
              {t("schemes.central_schemes")}
            </h2>
            <div className="space-y-3">
              {groupedSchemes.central.map((scheme) => (
                <motion.button
                  key={scheme.id}
                  onClick={() => handleSchemeClick(scheme)}
                  className="w-full rounded-2xl bg-white p-4 text-left shadow-sm transition-all hover:shadow-md"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className="flex items-start gap-3">
                    <div className="rounded-xl bg-emerald-100 p-2">
                      <Building2 className="h-5 w-5 text-emerald-700" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-black">{localizedName(scheme)}</h3>
                      <p className="mt-1 text-sm text-slate-600 line-clamp-2">
                        {localizedSummary(scheme)}
                      </p>
                      <div className="mt-2 flex items-center gap-2">
                        <span className="rounded-full bg-emerald-100 px-2 py-0.5 text-xs font-bold text-emerald-800">
                          {statusLabel(scheme.status)}
                        </span>
                        {scheme.deadline && (
                          <span className="flex items-center gap-1 text-xs text-slate-500">
                            <Calendar className="h-3 w-3" />
                            {formatDate(scheme.deadline)}
                          </span>
                        )}
                      </div>
                    </div>
                    <ChevronRight className="h-5 w-5 text-slate-400" />
                  </div>
                </motion.button>
              ))}
            </div>
          </section>
        )}

        {groupedSchemes.state.length > 0 && (
          <section>
            <h2 className="mb-3 text-lg font-black">
              {t("schemes.state_schemes")}
            </h2>
            <div className="space-y-3">
              {groupedSchemes.state.map((scheme) => (
                <motion.button
                  key={scheme.id}
                  onClick={() => handleSchemeClick(scheme)}
                  className="w-full rounded-2xl bg-white p-4 text-left shadow-sm transition-all hover:shadow-md"
                  whileHover={{ scale: 1.02 }}
                  whileTap={{ scale: 0.98 }}
                >
                  <div className="flex items-start gap-3">
                    <div className="rounded-xl bg-blue-100 p-2">
                      <Building2 className="h-5 w-5 text-blue-700" />
                    </div>
                    <div className="flex-1">
                      <h3 className="font-black">{localizedName(scheme)}</h3>
                      <p className="mt-1 text-sm text-slate-600 line-clamp-2">
                        {localizedSummary(scheme)}
                      </p>
                      <div className="mt-2 flex items-center gap-2">
                        <span className="rounded-full bg-blue-100 px-2 py-0.5 text-xs font-bold text-blue-800">
                          {statusLabel(scheme.status)}
                        </span>
                        {scheme.deadline && (
                          <span className="flex items-center gap-1 text-xs text-slate-500">
                            <Calendar className="h-3 w-3" />
                            {formatDate(scheme.deadline)}
                          </span>
                        )}
                      </div>
                    </div>
                    <ChevronRight className="h-5 w-5 text-slate-400" />
                  </div>
                </motion.button>
              ))}
            </div>
          </section>
        )}

        {groupedSchemes.central.length === 0 &&
          groupedSchemes.state.length === 0 && (
            <div className="rounded-2xl bg-white p-8 text-center font-bold">
              {t("schemes.no_schemes_found")}
            </div>
          )}
      </div>
      <AppBottomNav />
    </main>
  );
}
