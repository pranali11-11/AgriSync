import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { CalendarDays, ChevronRight } from 'lucide-react';
import { useOnboardingStore } from '../../store/useOnboardingStore';
import toast from 'react-hot-toast';

const MONTHS = [
  'Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'
];

export const Step3SowingDate = ({ onNext }) => {
  const { t } = useTranslation();
  const { sowingDate, setSowingDate, selectedCropName } = useOnboardingStore();
  const [value, setValue] = useState(sowingDate || '');

  // Max = today, min = 2 years ago
  const today = new Date().toISOString().split('T')[0];
  const minDate = new Date(Date.now() - 2 * 365 * 24 * 3600000).toISOString().split('T')[0];

  const handleNext = () => {
    if (!value) {
      toast.error(t('sowing.required'));
      return;
    }
    setSowingDate(value);
    onNext();
  };

  const formatted = value
    ? (() => {
        const d = new Date(value + 'T00:00:00');
        return `${d.getDate()} ${MONTHS[d.getMonth()]} ${d.getFullYear()}`;
      })()
    : null;

  return (
    <div className="flex flex-col min-h-[70vh] justify-center">
      <div className="text-center mb-10">
        <motion.div
          initial={{ scale: 0, rotate: -15 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: 'spring', stiffness: 200 }}
          className="text-6xl mb-4"
        >
          📅
        </motion.div>
        <h2 className="text-2xl font-black text-slate-800 dark:text-slate-100">{t('sowing.title')}</h2>
        {selectedCropName && (
          <p className="text-sm text-agri-green-700 dark:text-agri-green-400 font-semibold mt-1">
            {selectedCropName}
          </p>
        )}
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('sowing.subtitle')}</p>
      </div>

      <div className="space-y-6">
        <div className="bg-white dark:bg-slate-800 rounded-3xl border-2 border-slate-200 dark:border-slate-700 p-6 shadow-sm">
          <label className="block text-sm font-semibold text-slate-600 dark:text-slate-300 mb-3">
            {t('sowing.date_label')}
          </label>
          <input
            id="sowing-date-input"
            type="date"
            className="block w-full rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-slate-50 dark:bg-slate-900 px-4 py-4 text-lg font-semibold text-slate-800 dark:text-slate-100 focus:outline-none focus:border-agri-green-500 transition-colors"
            value={value}
            min={minDate}
            max={today}
            onChange={(e) => setValue(e.target.value)}
          />

          {formatted && (
            <motion.div
              initial={{ opacity: 0, y: 8 }}
              animate={{ opacity: 1, y: 0 }}
              className="mt-4 flex items-center space-x-3 bg-agri-green-50 dark:bg-agri-green-900/20 rounded-xl p-3"
            >
              <CalendarDays className="w-5 h-5 text-agri-green-600 flex-shrink-0" />
              <div>
                <p className="text-xs text-agri-green-700 dark:text-agri-green-300 font-semibold">
                  {t('sowing.selected')}
                </p>
                <p className="text-sm font-bold text-agri-green-800 dark:text-agri-green-200">{formatted}</p>
              </div>
            </motion.div>
          )}
        </div>

        <button
          id="sowing-next-btn"
          onClick={handleNext}
          disabled={!value}
          className="w-full py-4 rounded-2xl bg-agri-green-700 hover:bg-agri-green-800 text-white font-bold text-lg shadow-lg shadow-agri-green-700/30 transition-all disabled:opacity-50 active:scale-[0.98] flex items-center justify-center space-x-2"
        >
          <span>{t('common.next')}</span>
          <ChevronRight className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};

Step3SowingDate.propTypes = { onNext: PropTypes.func.isRequired };
