import React, { useState, useRef } from "react";
import { useTranslation } from "react-i18next";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { motion, AnimatePresence } from "framer-motion";
import {
  Plus,
  Edit2,
  Trash2,
  X,
  Loader2,
  ImagePlus,
  CheckCircle,
  AlertCircle,
  ChevronDown,
  Tractor,
  MapPin,
  Calendar,
  Zap,
} from "lucide-react";
import toast from "react-hot-toast";
import { providerMachineApi, uploadMachinePhotos } from "../../services/api";
import AddMachineForm from "./AddMachineForm";
import EditMachineModal from "./EditMachineModal";

// ─── Machine Card ─────────────────────────────────────────────────────────────

function MachineCard({ machine, onEdit, onDelete }) {
  const { t } = useTranslation();
  const firstPhoto = machine.photos?.[0];

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -16 }}
      className="relative rounded-2xl bg-white dark:bg-slate-800 shadow-sm border border-slate-100 dark:border-slate-700 overflow-hidden"
    >
      {/* Photo strip */}
      <div className="h-36 bg-gradient-to-br from-emerald-100 to-slate-200 dark:from-emerald-900/30 dark:to-slate-700 relative">
        {firstPhoto ? (
          <img
            src={firstPhoto}
            alt="Machine"
            className="w-full h-full object-cover"
          />
        ) : (
          <div className="w-full h-full flex items-center justify-center">
            <Tractor className="w-12 h-12 text-slate-300 dark:text-slate-600" />
          </div>
        )}
        {/* Verified / unverified badge */}
        <span
          className={`absolute top-2 right-2 px-2.5 py-1 rounded-full text-[10px] font-bold flex items-center gap-1 ${
            machine.verified
              ? "bg-emerald-600 text-white"
              : "bg-amber-400 text-amber-900"
          }`}
        >
          {machine.verified ? (
            <>
              <CheckCircle className="w-3 h-3" />
              {t("provider.status_verified")}
            </>
          ) : (
            <>
              <AlertCircle className="w-3 h-3" />
              {t("provider.status_unverified")}
            </>
          )}
        </span>
        {machine.photos?.length > 1 && (
          <span className="absolute bottom-2 right-2 bg-black/50 text-white text-[10px] px-1.5 py-0.5 rounded-full">
            +{machine.photos.length - 1}
          </span>
        )}
      </div>

      {/* Info */}
      <div className="p-4">
        <h3 className="font-black text-slate-800 dark:text-slate-100 text-base">
          {machine.machine_type?.name || `Machine #${machine.id}`}
        </h3>
        {machine.model_year && (
          <p className="text-xs text-slate-500 dark:text-slate-400 mt-0.5">
            {machine.model_year}
          </p>
        )}

        <div className="mt-3 grid grid-cols-2 gap-y-2 text-sm">
          <div className="flex items-center gap-1.5 text-slate-600 dark:text-slate-300">
            <Zap className="w-3.5 h-3.5 text-agri-green-600" />
            <span className="font-bold">
              ₹{machine.rate_per_acre}
              <span className="font-normal text-xs">/acre</span>
            </span>
          </div>
          <div className="flex items-center gap-1.5 text-slate-500 dark:text-slate-400 text-xs">
            <Calendar className="w-3.5 h-3.5" />
            <span>
              {machine.available_from} → {machine.available_to}
            </span>
          </div>
        </div>

        {machine.description && (
          <p className="mt-2 text-xs text-slate-500 dark:text-slate-400 line-clamp-2">
            {machine.description}
          </p>
        )}

        {/* Actions */}
        <div className="mt-4 flex gap-2">
          <button
            id={`edit-machine-${machine.id}-btn`}
            onClick={() => onEdit(machine)}
            className="flex-1 flex items-center justify-center gap-1.5 rounded-xl border border-slate-200 dark:border-slate-600 py-2 text-sm font-bold text-slate-700 dark:text-slate-300 hover:bg-slate-50 dark:hover:bg-slate-700 transition-colors"
          >
            <Edit2 className="w-3.5 h-3.5" />
            {t("provider.edit_btn")}
          </button>
          <button
            id={`delete-machine-${machine.id}-btn`}
            onClick={() => onDelete(machine)}
            className="rounded-xl border border-rose-100 dark:border-rose-900/40 p-2 text-rose-500 hover:bg-rose-50 dark:hover:bg-rose-900/20 transition-colors"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        </div>
      </div>
    </motion.div>
  );
}

// ─── Delete Confirm Modal ─────────────────────────────────────────────────────

function DeleteConfirmModal({ machine, onConfirm, onCancel, loading }) {
  const { t } = useTranslation();
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/40 backdrop-blur-sm">
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="bg-white dark:bg-slate-800 rounded-2xl p-6 max-w-sm w-full shadow-2xl"
      >
        <div className="flex items-center gap-3 mb-4">
          <div className="w-10 h-10 rounded-full bg-rose-100 dark:bg-rose-900/30 flex items-center justify-center">
            <Trash2 className="w-5 h-5 text-rose-500" />
          </div>
          <h2 className="text-lg font-black text-slate-800 dark:text-slate-100">
            {machine.machine_type?.name || `Machine #${machine.id}`}
          </h2>
        </div>
        <p className="text-sm text-slate-600 dark:text-slate-300 mb-6">
          {t("provider.delete_confirm")}
        </p>
        <div className="flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 rounded-xl border border-slate-200 dark:border-slate-600 py-2.5 text-sm font-bold text-slate-600 dark:text-slate-300"
          >
            {t("provider.cancel")}
          </button>
          <button
            id="confirm-delete-btn"
            onClick={onConfirm}
            disabled={loading}
            className="flex-1 rounded-xl bg-rose-600 text-white py-2.5 text-sm font-bold flex items-center justify-center gap-2 disabled:opacity-50"
          >
            {loading && <Loader2 className="w-4 h-4 animate-spin" />}
            {t("provider.delete_btn")}
          </button>
        </div>
      </motion.div>
    </div>
  );
}

// ─── Provider Dashboard ───────────────────────────────────────────────────────

export default function ProviderDashboard() {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const [showAddForm, setShowAddForm] = useState(false);
  const [editingMachine, setEditingMachine] = useState(null);
  const [deletingMachine, setDeletingMachine] = useState(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: ["provider-machines"],
    queryFn: async () => {
      const res = await providerMachineApi.listMine();
      return res.data;
    },
  });

  const deleteMutation = useMutation({
    mutationFn: (id) => providerMachineApi.remove(id),
    onSuccess: () => {
      toast.success(t("provider.form_success_delete"));
      queryClient.invalidateQueries({ queryKey: ["provider-machines"] });
      queryClient.invalidateQueries({ queryKey: ["machines"] });
      setDeletingMachine(null);
    },
    onError: () => toast.error(t("provider.form_error_generic")),
  });

  const machines = data?.items || [];

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 pb-24">
      {/* Header */}
      <div className="bg-gradient-to-br from-agri-green-700 to-emerald-900 text-white px-5 pt-10 pb-20">
        <h1 className="text-2xl font-black">{t("provider.dashboard_title")}</h1>
        <p className="text-emerald-200 text-sm mt-1">
          {t("provider.my_machines")}
        </p>
      </div>

      {/* Content card floated up */}
      <div className="-mt-12 mx-4 rounded-3xl bg-white dark:bg-slate-800 shadow-xl p-5 min-h-[60vh]">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-lg font-black text-slate-800 dark:text-slate-100">
            {machines.length} {t("provider.my_machines")}
          </h2>
          <motion.button
            id="add-machine-btn"
            whileTap={{ scale: 0.96 }}
            onClick={() => setShowAddForm(true)}
            className="flex items-center gap-2 rounded-2xl bg-agri-green-700 text-white px-4 py-2.5 text-sm font-bold shadow-lg shadow-agri-green-700/30"
          >
            <Plus className="w-4 h-4" />
            {t("provider.add_machine")}
          </motion.button>
        </div>

        {isLoading && (
          <div className="space-y-3">
            {[1, 2].map((i) => (
              <div
                key={i}
                className="h-56 rounded-2xl bg-slate-100 dark:bg-slate-700 animate-pulse"
              />
            ))}
          </div>
        )}

        {isError && (
          <div className="text-center py-12 text-slate-500 dark:text-slate-400">
            <AlertCircle className="w-10 h-10 mx-auto mb-3 text-rose-400" />
            <p>{t("provider.form_error_generic")}</p>
          </div>
        )}

        {!isLoading && !isError && machines.length === 0 && (
          <div className="text-center py-16">
            <div className="w-20 h-20 mx-auto mb-4 rounded-3xl bg-slate-100 dark:bg-slate-700 flex items-center justify-center">
              <Tractor className="w-10 h-10 text-slate-400 dark:text-slate-500" />
            </div>
            <p className="text-slate-500 dark:text-slate-400 text-sm max-w-xs mx-auto">
              {t("provider.no_machines")}
            </p>
            <button
              onClick={() => setShowAddForm(true)}
              className="mt-6 rounded-2xl bg-agri-green-700 text-white px-6 py-3 text-sm font-bold"
            >
              {t("provider.add_machine")}
            </button>
          </div>
        )}

        <AnimatePresence>
          {!isLoading && machines.length > 0 && (
            <div className="space-y-4">
              {machines.map((m) => (
                <MachineCard
                  key={m.id}
                  machine={m}
                  onEdit={setEditingMachine}
                  onDelete={setDeletingMachine}
                />
              ))}
            </div>
          )}
        </AnimatePresence>
      </div>

      {/* Add Machine Form slide-over */}
      <AnimatePresence>
        {showAddForm && (
          <AddMachineForm
            onClose={() => setShowAddForm(false)}
            onSuccess={() => {
              setShowAddForm(false);
              queryClient.invalidateQueries({
                queryKey: ["provider-machines"],
              });
              queryClient.invalidateQueries({ queryKey: ["machines"] });
            }}
          />
        )}
      </AnimatePresence>

      {/* Edit Machine Modal */}
      <AnimatePresence>
        {editingMachine && (
          <EditMachineModal
            machine={editingMachine}
            onClose={() => setEditingMachine(null)}
            onSuccess={() => {
              setEditingMachine(null);
              queryClient.invalidateQueries({
                queryKey: ["provider-machines"],
              });
              queryClient.invalidateQueries({ queryKey: ["machines"] });
            }}
          />
        )}
      </AnimatePresence>

      {/* Delete Confirm */}
      <AnimatePresence>
        {deletingMachine && (
          <DeleteConfirmModal
            machine={deletingMachine}
            loading={deleteMutation.isPending}
            onConfirm={() => deleteMutation.mutate(deletingMachine.id)}
            onCancel={() => setDeletingMachine(null)}
          />
        )}
      </AnimatePresence>
    </div>
  );
}
