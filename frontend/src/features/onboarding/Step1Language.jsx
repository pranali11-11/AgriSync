import React from 'react';
import PropTypes from 'prop-types';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import i18n from 'i18next';
import { useOnboardingStore } from '../../store/useOnboardingStore';

const LANGUAGES = [
  { code: 'en', label: 'English', nativeLabel: 'English', flag: '🇬🇧' },
  { code: 'hi', label: 'Hindi', nativeLabel: 'हिंदी', flag: '🇮🇳' },
  { code: 'mr', label: 'Marathi', nativeLabel: 'मराठी', flag: '🌿' },
];

const container = {
  hidden: { opacity: 0 },
  show: { opacity: 1, transition: { staggerChildren: 0.1 } },
};

const item = {
  hidden: { opacity: 0, y: 20 },
  show: { opacity: 1, y: 0 },
};

export const Step1Language = ({ onNext }) => {
  const { t } = useTranslation();
  const { language, setLanguage } = useOnboardingStore();

  const selectLang = (code) => {
    setLanguage(code);
    i18n.changeLanguage(code);
    setTimeout(onNext, 300);
  };

  return (
    <div className="flex flex-col justify-center min-h-[70vh]">
      <div className="text-center mb-10">
        <motion.div
          initial={{ scale: 0, rotate: -10 }}
          animate={{ scale: 1, rotate: 0 }}
          transition={{ type: 'spring', stiffness: 180 }}
          className="text-6xl mb-4"
        >
          🌐
        </motion.div>
        <h2 className="text-2xl font-black text-slate-800 dark:text-slate-100">{t('language.select_title')}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-2">{t('language.select_subtitle')}</p>
      </div>

      <motion.div
        variants={container}
        initial="hidden"
        animate="show"
        className="space-y-4"
      >
        {LANGUAGES.map((lang) => (
          <motion.button
            key={lang.code}
            variants={item}
            onClick={() => selectLang(lang.code)}
            id={`lang-${lang.code}`}
            whileTap={{ scale: 0.97 }}
            className={`
              w-full flex items-center space-x-4 p-5 rounded-2xl border-2 transition-all
              ${
                language === lang.code
                  ? 'border-agri-green-500 bg-agri-green-50 dark:bg-agri-green-900/20 shadow-agri-green-100 shadow-md'
                  : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-agri-green-300 dark:hover:border-agri-green-600'
              }
            `}
          >
            <span className="text-3xl">{lang.flag}</span>
            <div className="text-left">
              <p className="text-lg font-bold text-slate-800 dark:text-slate-100">{lang.nativeLabel}</p>
              <p className="text-sm text-slate-500 dark:text-slate-400">{lang.label}</p>
            </div>
            {language === lang.code && (
              <motion.div
                layoutId="lang-check"
                className="ml-auto w-6 h-6 rounded-full bg-agri-green-500 flex items-center justify-center"
              >
                <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={3}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </motion.div>
            )}
          </motion.button>
        ))}
      </motion.div>
    </div>
  );
};

Step1Language.propTypes = { onNext: PropTypes.func.isRequired };
