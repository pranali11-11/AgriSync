import React, { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Plus, Pencil, Trash2, X, Check } from "lucide-react";
import toast from "react-hot-toast";
import { motion, AnimatePresence } from "framer-motion";
import api from "../../api/axios";

const fetchSchemes = async () => {
  const response = await api.get("/schemes?show_all=true");
  return response.data;
};

const createScheme = async (data) => {
  const response = await api.post("/schemes", data);
  return response.data;
};

const updateScheme = async ({ id, data }) => {
  const response = await api.put(`/schemes/${id}`, data);
  return response.data;
};

const deleteScheme = async (id) => {
  await api.delete(`/schemes/${id}`);
};

export default function AdminSchemesPage() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [editingScheme, setEditingScheme] = useState(null);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({});

  const { data: schemes, isLoading, refetch } = useQuery({
    queryKey: ["admin-schemes"],
    queryFn: fetchSchemes,
  });

  const createMutation = useMutation({
    mutationFn: createScheme,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-schemes"] });
      setShowCreateForm(false);
      setFormData({});
      toast.success(t("schemes.create_success"));
    },
    onError: () => toast.error(t("schemes.create_error")),
  });

  const updateMutation = useMutation({
    mutationFn: updateScheme,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-schemes"] });
      setEditingScheme(null);
      setFormData({});
      toast.success(t("schemes.update_success"));
    },
    onError: () => toast.error(t("schemes.update_error")),
  });

  const deleteMutation = useMutation({
    mutationFn: deleteScheme,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["admin-schemes"] });
      toast.success(t("schemes.delete_success"));
    },
    onError: () => toast.error(t("schemes.delete_error")),
  });

  const handleCreate = (e) => {
    e.preventDefault();
    createMutation.mutate(formData);
  };

  const handleUpdate = (e) => {
    e.preventDefault();
    updateMutation.mutate({ id: editingScheme.id, data: formData });
  };

  const handleDelete = (id) => {
    if (window.confirm(t("schemes.delete_confirm"))) {
      deleteMutation.mutate(id);
    }
  };

  const startEdit = (scheme) => {
    setEditingScheme(scheme);
    setFormData({
      name: scheme.name,
      name_hi: scheme.name_hi || "",
      name_mr: scheme.name_mr || "",
      level: scheme.level,
      department: scheme.department,
      short_description: scheme.short_description,
      short_description_hi: scheme.short_description_hi || "",
      short_description_mr: scheme.short_description_mr || "",
      eligibility_text: scheme.eligibility_text,
      benefits_text: scheme.benefits_text,
      required_documents: scheme.required_documents || [],
      application_process_text: scheme.application_process_text,
      official_link: scheme.official_link,
      deadline: scheme.deadline || "",
      status: scheme.status,
      crops: scheme.crops || [],
      states: scheme.states || [],
      last_verified_on: scheme.last_verified_on,
      source: scheme.source,
    });
  };

  const handleInputChange = (field, value) => {
    setFormData((prev) => ({ ...prev, [field]: value }));
  };

  const handleArrayChange = (field, value) => {
    const array = value.split(",").map((item) => item.trim()).filter(Boolean);
    handleInputChange(field, array);
  };

  const SchemeForm = ({ onSubmit, isEdit }) => (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-6 rounded-2xl bg-white p-6 shadow-sm"
    >
      <div className="mb-4 flex items-center justify-between">
        <h2 className="text-xl font-black">
          {isEdit ? t("schemes.edit_scheme") : t("schemes.create_scheme")}
        </h2>
        <button
          onClick={() => {
            setShowCreateForm(false);
            setEditingScheme(null);
            setFormData({});
          }}
          className="rounded-lg p-2 hover:bg-slate-100"
        >
          <X className="h-5 w-5" />
        </button>
      </div>
      <form onSubmit={onSubmit} className="space-y-4">
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-bold">{t("schemes.name")} *</label>
            <input
              type="text"
              value={formData.name || ""}
              onChange={(e) => handleInputChange("name", e.target.value)}
              required
              className="w-full rounded-xl border px-3 py-2"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-bold">{t("schemes.name_hi")}</label>
            <input
              type="text"
              value={formData.name_hi || ""}
              onChange={(e) => handleInputChange("name_hi", e.target.value)}
              className="w-full rounded-xl border px-3 py-2"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-bold">{t("schemes.name_mr")}</label>
            <input
              type="text"
              value={formData.name_mr || ""}
              onChange={(e) => handleInputChange("name_mr", e.target.value)}
              className="w-full rounded-xl border px-3 py-2"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-bold">{t("schemes.level")} *</label>
            <select
              value={formData.level || "central"}
              onChange={(e) => handleInputChange("level", e.target.value)}
              required
              className="w-full rounded-xl border px-3 py-2"
            >
              <option value="central">{t("schemes.central")}</option>
              <option value="state">{t("schemes.state")}</option>
            </select>
          </div>
        </div>
        <div>
          <label className="mb-1 block text-sm font-bold">{t("schemes.department")} *</label>
          <input
            type="text"
            value={formData.department || ""}
            onChange={(e) => handleInputChange("department", e.target.value)}
            required
            className="w-full rounded-xl border px-3 py-2"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-bold">{t("schemes.short_description")} *</label>
          <textarea
            value={formData.short_description || ""}
            onChange={(e) => handleInputChange("short_description", e.target.value)}
            required
            rows={2}
            className="w-full rounded-xl border px-3 py-2"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-bold">{t("schemes.short_description_hi")}</label>
          <textarea
            value={formData.short_description_hi || ""}
            onChange={(e) => handleInputChange("short_description_hi", e.target.value)}
            rows={2}
            className="w-full rounded-xl border px-3 py-2"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-bold">{t("schemes.short_description_mr")}</label>
          <textarea
            value={formData.short_description_mr || ""}
            onChange={(e) => handleInputChange("short_description_mr", e.target.value)}
            rows={2}
            className="w-full rounded-xl border px-3 py-2"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-bold">{t("schemes.eligibility_text")} *</label>
          <textarea
            value={formData.eligibility_text || ""}
            onChange={(e) => handleInputChange("eligibility_text", e.target.value)}
            required
            rows={3}
            className="w-full rounded-xl border px-3 py-2"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-bold">{t("schemes.benefits_text")} *</label>
          <textarea
            value={formData.benefits_text || ""}
            onChange={(e) => handleInputChange("benefits_text", e.target.value)}
            required
            rows={3}
            className="w-full rounded-xl border px-3 py-2"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-bold">{t("schemes.required_documents")} (comma-separated)</label>
          <input
            type="text"
            value={(formData.required_documents || []).join(", ")}
            onChange={(e) => handleArrayChange("required_documents", e.target.value)}
            className="w-full rounded-xl border px-3 py-2"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-bold">{t("schemes.application_process_text")} *</label>
          <textarea
            value={formData.application_process_text || ""}
            onChange={(e) => handleInputChange("application_process_text", e.target.value)}
            required
            rows={3}
            className="w-full rounded-xl border px-3 py-2"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-bold">{t("schemes.official_link")} *</label>
          <input
            type="url"
            value={formData.official_link || ""}
            onChange={(e) => handleInputChange("official_link", e.target.value)}
            required
            className="w-full rounded-xl border px-3 py-2"
          />
        </div>
        <div className="grid gap-4 md:grid-cols-2">
          <div>
            <label className="mb-1 block text-sm font-bold">{t("schemes.deadline")}</label>
            <input
              type="date"
              value={formData.deadline || ""}
              onChange={(e) => handleInputChange("deadline", e.target.value)}
              className="w-full rounded-xl border px-3 py-2"
            />
          </div>
          <div>
            <label className="mb-1 block text-sm font-bold">{t("schemes.status")} *</label>
            <select
              value={formData.status || "active"}
              onChange={(e) => handleInputChange("status", e.target.value)}
              required
              className="w-full rounded-xl border px-3 py-2"
            >
              <option value="active">{t("schemes.status_active")}</option>
              <option value="upcoming">{t("schemes.status_upcoming")}</option>
              <option value="closed">{t("schemes.status_closed")}</option>
            </select>
          </div>
        </div>
        <div>
          <label className="mb-1 block text-sm font-bold">{t("schemes.crops")} (comma-separated)</label>
          <input
            type="text"
            value={(formData.crops || []).join(", ")}
            onChange={(e) => handleArrayChange("crops", e.target.value)}
            className="w-full rounded-xl border px-3 py-2"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-bold">{t("schemes.states")} (comma-separated)</label>
          <input
            type="text"
            value={(formData.states || []).join(", ")}
            onChange={(e) => handleArrayChange("states", e.target.value)}
            className="w-full rounded-xl border px-3 py-2"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-bold">{t("schemes.last_verified_on")} *</label>
          <input
            type="datetime-local"
            value={formData.last_verified_on || ""}
            onChange={(e) => handleInputChange("last_verified_on", e.target.value)}
            required
            className="w-full rounded-xl border px-3 py-2"
          />
        </div>
        <div>
          <label className="mb-1 block text-sm font-bold">{t("schemes.source")} *</label>
          <input
            type="text"
            value={formData.source || ""}
            onChange={(e) => handleInputChange("source", e.target.value)}
            required
            className="w-full rounded-xl border px-3 py-2"
          />
        </div>
        <button
          type="submit"
          disabled={createMutation.isPending || updateMutation.isPending}
          className="w-full rounded-xl bg-emerald-700 py-3 font-bold text-white disabled:opacity-50"
        >
          {isEdit ? t("schemes.update") : t("schemes.create")}
        </button>
      </form>
    </motion.div>
  );

  if (isLoading) {
    return (
      <main className="min-h-screen bg-[#f5f7f2] p-5">
        <div className="mx-auto max-w-4xl animate-pulse">
          <div className="h-20 rounded-2xl bg-slate-200" />
          <div className="mt-4 h-48 rounded-2xl bg-slate-200" />
        </div>
      </main>
    );
  }

  return (
    <main className="min-h-screen bg-[#f5f7f2] p-5">
      <div className="mx-auto max-w-6xl space-y-6">
        <header className="flex items-center justify-between">
          <h1 className="text-3xl font-black">{t("schemes.admin_title")}</h1>
          <button
            onClick={() => setShowCreateForm(true)}
            className="flex items-center gap-2 rounded-xl bg-emerald-700 px-4 py-2 font-bold text-white"
          >
            <Plus className="h-5 w-5" />
            {t("schemes.add_scheme")}
          </button>
        </header>

        <AnimatePresence>
          {showCreateForm && (
            <SchemeForm onSubmit={handleCreate} isEdit={false} />
          )}
          {editingScheme && (
            <SchemeForm onSubmit={handleUpdate} isEdit={true} />
          )}
        </AnimatePresence>

        <div className="overflow-hidden rounded-2xl bg-white shadow-sm">
          <table className="w-full">
            <thead className="bg-slate-50">
              <tr>
                <th className="px-4 py-3 text-left text-sm font-bold">{t("schemes.name")}</th>
                <th className="px-4 py-3 text-left text-sm font-bold">{t("schemes.level")}</th>
                <th className="px-4 py-3 text-left text-sm font-bold">{t("schemes.department")}</th>
                <th className="px-4 py-3 text-left text-sm font-bold">{t("schemes.status")}</th>
                <th className="px-4 py-3 text-right text-sm font-bold">{t("schemes.actions")}</th>
              </tr>
            </thead>
            <tbody>
              {schemes?.map((scheme) => (
                <tr key={scheme.id} className="border-t">
                  <td className="px-4 py-3 font-medium">{scheme.name}</td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-bold ${
                        scheme.level === "central"
                          ? "bg-emerald-100 text-emerald-800"
                          : "bg-blue-100 text-blue-800"
                      }`}
                    >
                      {scheme.level === "central"
                        ? t("schemes.central")
                        : t("schemes.state")}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-sm text-slate-600">
                    {scheme.department}
                  </td>
                  <td className="px-4 py-3">
                    <span
                      className={`rounded-full px-2 py-1 text-xs font-bold ${
                        scheme.status === "active"
                          ? "bg-green-100 text-green-800"
                          : scheme.status === "upcoming"
                            ? "bg-amber-100 text-amber-800"
                            : "bg-red-100 text-red-800"
                      }`}
                    >
                      {t(`schemes.status_${scheme.status}`)}
                    </span>
                  </td>
                  <td className="px-4 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <button
                        onClick={() => startEdit(scheme)}
                        className="rounded-lg p-2 hover:bg-slate-100"
                        title={t("schemes.edit")}
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                      <button
                        onClick={() => handleDelete(scheme.id)}
                        className="rounded-lg p-2 text-red-600 hover:bg-red-50"
                        title={t("schemes.delete")}
                      >
                        <Trash2 className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </main>
  );
}
