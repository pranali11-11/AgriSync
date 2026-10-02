import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { AnimatePresence, motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { ChevronRight } from 'lucide-react';
import { useOnboardingStore } from '../../store/useOnboardingStore';
import toast from 'react-hot-toast';

const SOIL_TYPES = [
  { id: 'clay', emoji: '🪨', labelKey: 'soil.type_clay' },
  { id: 'loamy', emoji: '🌿', labelKey: 'soil.type_loamy' },
  { id: 'sandy', emoji: '🏖️', labelKey: 'soil.type_sandy' },
  { id: 'black', emoji: '⚫', labelKey: 'soil.type_black' },
  { id: 'red', emoji: '🔴', labelKey: 'soil.type_red' },
  { id: 'alluvial', emoji: '💧', labelKey: 'soil.type_alluvial' },
];

const IRRIGATION_TYPES = [
  { id: 'rainfed', emoji: '🌧️', labelKey: 'soil.irr_rainfed' },
  { id: 'canal', emoji: '🌊', labelKey: 'soil.irr_canal' },
  { id: 'borewell', emoji: '⛽', labelKey: 'soil.irr_borewell' },
  { id: 'well', emoji: '🪣', labelKey: 'soil.irr_well' },
  { id: 'drip', emoji: '💧', labelKey: 'soil.irr_drip' },
  { id: 'sprinkler', emoji: '🚿', labelKey: 'soil.irr_sprinkler' },
  { id: 'pond_tank', emoji: '🏞️', labelKey: 'soil.irr_pond_tank' },
  { id: 'other', emoji: '📝', labelKey: 'soil.irr_other' },
];

const ChipGroup = ({ items, value, onChange, label }) => {
  const { t } = useTranslation();
  return (
    <div className="mb-5 last:mb-0">
      <p className="text-sm font-semibold text-slate-600 dark:text-slate-300 mb-3">{label}</p>
      <div className="grid grid-cols-2 gap-2.5">
        {items.map((item) => {
          const isSelected = value === item.id;
          return (
            <button
              key={item.id}
              type="button"
              id={`irrigation-btn-${item.id}`}
              onClick={() => onChange(item.id)}
              className={`flex items-center space-x-3 px-4 py-3.5 rounded-2xl border-2 transition-all text-left ${
                isSelected
                  ? 'border-agri-green-500 bg-agri-green-50 dark:bg-agri-green-900/25 ring-2 ring-agri-green-500/20'
                  : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-agri-green-300'
              }`}
            >
              <span className="text-2xl flex-shrink-0">{item.emoji}</span>
              <span
                className={`text-sm font-bold flex-1 truncate ${
                  isSelected
                    ? 'text-agri-green-700 dark:text-agri-green-300'
                    : 'text-slate-700 dark:text-slate-200'
                }`}
              >
                {t(item.labelKey)}
              </span>
              {isSelected && (
                <span className="w-2 h-2 rounded-full bg-agri-green-600 dark:bg-agri-green-400 flex-shrink-0" />
              )}
            </button>
          );
        })}
      </div>
    </div>
  );
};

ChipGroup.propTypes = {
  items: PropTypes.array.isRequired,
  value: PropTypes.string,
  onChange: PropTypes.func.isRequired,
  label: PropTypes.string.isRequired,
};

export const Step5SoilInfo = ({ onNext }) => {
  const { t } = useTranslation();
  const { soilType, irrigationType, irrigationTypeNote, setSoil } = useOnboardingStore();
  const [soil, setSoilLocal] = useState(soilType || '');
  const [irrigation, setIrrigationLocal] = useState(irrigationType || '');
  const [irrigationNote, setIrrigationNote] = useState(irrigationTypeNote || '');

  const isOtherSelected = irrigation === 'other';
  const isOtherEmpty = isOtherSelected && !irrigationNote.trim();

  const handleNext = () => {
    if (!soil) {
      toast.error(t('soil.select_soil'));
      return;
    }
    if (!irrigation) {
      toast.error(t('soil.select_irrigation'));
      return;
    }
    if (isOtherSelected && !irrigationNote.trim()) {
      toast.error(t('soil.irr_other_required'));
      return;
    }
    setSoil(soil, irrigation, isOtherSelected ? irrigationNote.trim() : '');
    onNext();
  };

  return (
    <div className="flex flex-col">
      <div className="text-center mb-8">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 200 }}
          className="text-6xl mb-4"
        >
          🪴
        </motion.div>
        <h2 className="text-2xl font-black text-slate-800 dark:text-slate-100">{t('soil.title')}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('soil.subtitle')}</p>
      </div>

      <div className="bg-white dark:bg-slate-800 rounded-3xl border-2 border-slate-200 dark:border-slate-700 p-5 shadow-sm mb-6">
        <ChipGroup
          items={SOIL_TYPES}
          value={soil}
          onChange={setSoilLocal}
          label={t('soil.soil_type_label')}
        />
        <div className="my-5 border-t border-slate-100 dark:border-slate-700/50" />
        <ChipGroup
          items={IRRIGATION_TYPES}
          value={irrigation}
          onChange={setIrrigationLocal}
          label={t('soil.irrigation_label')}
        />

        <AnimatePresence>
          {isOtherSelected && (
            <motion.div
              initial={{ opacity: 0, height: 0, marginTop: 0 }}
              animate={{ opacity: 1, height: 'auto', marginTop: 16 }}
              exit={{ opacity: 0, height: 0, marginTop: 0 }}
              transition={{ duration: 0.25, ease: 'easeOut' }}
              className="overflow-hidden pt-1 border-t border-dashed border-slate-200 dark:border-slate-700"
            >
              <label
                htmlFor="irrigation-other-input"
                className="block text-xs font-bold text-slate-700 dark:text-slate-300 mb-1.5"
              >
                {t('soil.irr_other_label')} <span className="text-rose-500">*</span>
              </label>
              <input
                id="irrigation-other-input"
                type="text"
                value={irrigationNote}
                onChange={(e) => setIrrigationNote(e.target.value)}
                placeholder={t('soil.irr_other_placeholder')}
                maxLength={100}
                className="w-full px-4 py-3 text-sm rounded-2xl border-2 border-agri-green-400 dark:border-agri-green-600 bg-agri-green-50/40 dark:bg-agri-green-950/30 text-slate-900 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-agri-green-500/25 transition-all"
                autoFocus
              />
              {isOtherEmpty && (
                <p className="text-xs text-rose-500 dark:text-rose-400 mt-1.5 font-semibold">
                  {t('soil.irr_other_required')}
                </p>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      <button
        id="soil-next-btn"
        type="button"
        onClick={handleNext}
        disabled={!soil || !irrigation || isOtherEmpty}
        className="w-full py-4 rounded-2xl bg-agri-green-700 hover:bg-agri-green-800 text-white font-bold text-lg shadow-lg shadow-agri-green-700/30 transition-all disabled:opacity-50 active:scale-[0.98] flex items-center justify-center space-x-2"
      >
        <span>{t('common.next')}</span>
        <ChevronRight className="w-5 h-5" />
      </button>
    </div>
  );
};

Step5SoilInfo.propTypes = { onNext: PropTypes.func.isRequired };
