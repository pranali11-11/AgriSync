import React, { useState } from "react";
import PropTypes from "prop-types";
import { motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { Loader2, Sparkles, Edit3 } from "lucide-react";
import confetti from "canvas-confetti";
import toast from "react-hot-toast";
import { farmerApi, farmsApi } from "../../services/api";
import { useOnboardingStore } from "../../store/useOnboardingStore";

const SummaryRow = ({ label, value, emoji }) => (
  <div className="flex items-start space-x-3 py-3 border-b border-slate-100 dark:border-slate-700/50 last:border-0">
    <span className="text-xl flex-shrink-0 mt-0.5">{emoji}</span>
    <div className="flex-1 min-w-0">
      <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 uppercase tracking-wide">
        {label}
      </p>
      <p className="text-sm font-bold text-slate-800 dark:text-slate-100 mt-0.5 truncate">
        {value || "—"}
      </p>
    </div>
  </div>
);

SummaryRow.propTypes = {
  label: PropTypes.string,
  value: PropTypes.string,
  emoji: PropTypes.string,
};

export const Step7Summary = ({ onFinish }) => {
  const { t } = useTranslation();
  const store = useOnboardingStore();
  const [saving, setSaving] = useState(false);

  const handleFinish = async () => {
    setSaving(true);
    try {
      // 1. Create / update farmer profile
      await farmerApi
        .createProfile({
          village: store.village,
          district: store.district,
          state: store.state,
          latitude: store.lat,
          longitude: store.lng,
          total_area_acres: parseFloat(store.areaAcres) || 0,
        })
        .catch(() => {
          // May already exist – try update
          return farmerApi.updateProfile({
            village: store.village,
            district: store.district,
            state: store.state,
            latitude: store.lat,
            longitude: store.lng,
            total_area_acres: parseFloat(store.areaAcres) || 0,
          });
        });

      // 2. Create the farm record
      const farmResponse = await farmsApi.create({
        crop_id: store.selectedCropId,
        sowing_date: store.sowingDate,
        area_acres: parseFloat(store.areaAcres),
        soil_type: store.soilType,
        irrigation_type: store.irrigationType,
        irrigation_type_note:
          store.irrigationType === "other" ? store.irrigationTypeNote : null,
      });
      useOnboardingStore.getState().setFarmId(farmResponse.data.id);

      // Celebrate!
      confetti({ particleCount: 120, spread: 70, origin: { y: 0.6 } });
      toast.success(t("summary.saved_ok"), { duration: 3000 });

      setTimeout(() => {
        onFinish();
      }, 1200);
    } catch (e) {
      const msg = e.response?.data?.detail || t("summary.save_error");
      toast.error(msg);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="flex flex-col">
      <div className="text-center mb-8">
        <motion.div
          initial={{ scale: 0, rotate: -10 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: "spring", stiffness: 200, delay: 0.1 }}
          className="text-6xl mb-4"
        >
          🎉
        </motion.div>
        <h2 className="text-2xl font-black text-slate-800 dark:text-slate-100">
          {t("summary.title")}
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          {t("summary.subtitle")}
        </p>
      </div>

      {/* Summary Card */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="bg-white dark:bg-slate-800 rounded-3xl border-2 border-slate-200 dark:border-slate-700 p-5 shadow-sm mb-6"
      >
        <SummaryRow
          label={t("summary.crop")}
          value={store.selectedCropName}
          emoji="🌾"
        />
        <SummaryRow
          label={t("summary.sowing_date")}
          value={store.sowingDate}
          emoji="📅"
        />
        <SummaryRow
          label={t("summary.area")}
          value={store.areaAcres ? `${store.areaAcres} ${t("area.unit")}` : ""}
          emoji="🗺️"
        />
        <SummaryRow
          label={t("summary.soil")}
          value={
            store.soilType
              ? t(`soil.type_${store.soilType}`, { defaultValue: store.soilType })
              : "—"
          }
          emoji="🪨"
        />
        <SummaryRow
          label={t("summary.irrigation")}
          value={
            store.irrigationType === "other"
              ? `${t("soil.irr_other")}${store.irrigationTypeNote ? ` (${store.irrigationTypeNote})` : ""}`
              : store.irrigationType
              ? t(`soil.irr_${store.irrigationType}`, { defaultValue: store.irrigationType })
              : "—"
          }
          emoji="💧"
        />
        <SummaryRow
          label={t("summary.village")}
          value={[store.village, store.district, store.state]
            .filter(Boolean)
            .join(", ")}
          emoji="📍"
        />
      </motion.div>

      {/* Actions */}
      <div className="space-y-3">
        <button
          id="finish-btn"
          onClick={handleFinish}
          disabled={saving}
          className="w-full py-4 rounded-2xl bg-agri-green-700 hover:bg-agri-green-800 text-white font-bold text-lg shadow-lg shadow-agri-green-700/30 transition-all disabled:opacity-60 active:scale-[0.98] flex items-center justify-center space-x-2"
        >
          {saving ? (
            <Loader2 className="w-5 h-5 animate-spin" />
          ) : (
            <Sparkles className="w-5 h-5" />
          )}
          <span>{saving ? t("summary.saving") : t("summary.finish")}</span>
        </button>

        <button
          onClick={() => useOnboardingStore.getState().goToStep(2)}
          className="w-full py-3 text-sm font-semibold text-slate-400 hover:text-agri-green-600 transition-colors flex items-center justify-center space-x-1.5"
        >
          <Edit3 className="w-4 h-4" />
          <span>{t("summary.edit")}</span>
        </button>
      </div>
    </div>
  );
};

Step7Summary.propTypes = { onFinish: PropTypes.func.isRequired };
