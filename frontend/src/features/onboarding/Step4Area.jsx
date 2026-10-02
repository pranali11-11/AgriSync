import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { ChevronRight, Minus, Plus } from 'lucide-react';
import { useOnboardingStore } from '../../store/useOnboardingStore';
import toast from 'react-hot-toast';

const PRESETS = [0.5, 1, 2, 3, 5];

export const Step4Area = ({ onNext }) => {
  const { t } = useTranslation();
  const { areaAcres, setArea } = useOnboardingStore();
  const [value, setValue] = useState(areaAcres ? parseFloat(areaAcres) : '');

  const adjust = (delta) => {
    const cur = parseFloat(value) || 0;
    const next = Math.max(0.1, Math.min(500, parseFloat((cur + delta).toFixed(1))));
    setValue(next);
  };

  const handleNext = () => {
    const num = parseFloat(value);
    if (!value || isNaN(num) || num <= 0) {
      toast.error(t('area.required'));
      return;
    }
    if (num > 500) {
      toast.error(t('area.too_large'));
      return;
    }
    setArea(num.toString());
    onNext();
  };

  return (
    <div className="flex flex-col min-h-[70vh] justify-center">
      <div className="text-center mb-10">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 200 }}
          className="text-6xl mb-4"
        >
          🗺️
        </motion.div>
        <h2 className="text-2xl font-black text-slate-800 dark:text-slate-100">{t('area.title')}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('area.subtitle')}</p>
      </div>

      <div className="space-y-6">
        {/* Stepper */}
        <div className="bg-white dark:bg-slate-800 rounded-3xl border-2 border-slate-200 dark:border-slate-700 p-6 shadow-sm">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => adjust(-0.5)}
              className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-700 flex items-center justify-center hover:bg-agri-green-100 dark:hover:bg-agri-green-900/30 transition-all"
            >
              <Minus className="w-5 h-5 text-slate-600 dark:text-slate-300" />
            </button>

            <div className="flex-1 text-center">
              <input
                id="area-input"
                type="number"
                min="0.1"
                max="500"
                step="0.5"
                className="w-full text-center text-4xl font-black text-slate-800 dark:text-slate-100 bg-transparent border-none focus:outline-none"
                value={value}
                onChange={(e) => setValue(e.target.value)}
              />
              <p className="text-sm text-slate-400 dark:text-slate-500 font-semibold">{t('area.unit')}</p>
            </div>

            <button
              onClick={() => adjust(0.5)}
              className="w-12 h-12 rounded-2xl bg-slate-100 dark:bg-slate-700 flex items-center justify-center hover:bg-agri-green-100 dark:hover:bg-agri-green-900/30 transition-all"
            >
              <Plus className="w-5 h-5 text-slate-600 dark:text-slate-300" />
            </button>
          </div>
        </div>

        {/* Quick preset chips */}
        <div>
          <p className="text-xs font-semibold text-slate-400 dark:text-slate-500 mb-2">{t('area.quick_select')}</p>
          <div className="flex flex-wrap gap-2">
            {PRESETS.map((p) => (
              <button
                key={p}
                onClick={() => setValue(p)}
                className={`px-4 py-2 rounded-xl border-2 text-sm font-bold transition-all ${
                  parseFloat(value) === p
                    ? 'border-agri-green-500 bg-agri-green-50 dark:bg-agri-green-900/30 text-agri-green-700 dark:text-agri-green-300'
                    : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 text-slate-600 dark:text-slate-300'
                }`}
              >
                {p} ac
              </button>
            ))}
          </div>
        </div>

        <button
          id="area-next-btn"
          onClick={handleNext}
          disabled={!value || parseFloat(value) <= 0}
          className="w-full py-4 rounded-2xl bg-agri-green-700 hover:bg-agri-green-800 text-white font-bold text-lg shadow-lg shadow-agri-green-700/30 transition-all disabled:opacity-50 active:scale-[0.98] flex items-center justify-center space-x-2"
        >
          <span>{t('common.next')}</span>
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};

Step4Area.propTypes = { onNext: PropTypes.func.isRequired };
