/**
 * Single source of truth for i18next initialisation.
 *
 * Language priority (highest → lowest):
 *   1. `agrisync_lang` localStorage key  (set by useAppStore.setLanguage)
 *   2. `agrisync-onboarding` Zustand state (set during onboarding wizard)
 *   3. Browser navigator.language prefix  (e.g. "hi-IN" → "hi")
 *   4. "en" hard fallback
 *
 * Supported locales: en | hi | mr
 */
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';

import en from './locales/en.json';
import hi from './locales/hi.json';
import mr from './locales/mr.json';

const SUPPORTED = ['en', 'hi', 'mr'];

function detectLanguage() {
  // 1. Explicit per-session language selection
  const explicit = localStorage.getItem('agrisync_lang');
  if (explicit && SUPPORTED.includes(explicit)) return explicit;

  // 2. Language persisted inside the onboarding Zustand store
  try {
    const stored = JSON.parse(localStorage.getItem('agrisync-onboarding') || '{}');
    const zustandLang = stored?.state?.language;
    if (zustandLang && SUPPORTED.includes(zustandLang)) return zustandLang;
  } catch {
    // ignore parse errors
  }

  // 3. Browser locale prefix
  const browserLang = (navigator.language || '').split('-')[0];
  if (SUPPORTED.includes(browserLang)) return browserLang;

  return 'en';
}

if (!i18n.isInitialized) {
  i18n.use(initReactI18next).init({
    resources: {
      en: { translation: en },
      hi: { translation: hi },
      mr: { translation: mr },
    },
    lng: detectLanguage(),
    fallbackLng: 'en',
    supportedLngs: SUPPORTED,
    interpolation: {
      escapeValue: false, // React already escapes
    },
    // Log missing keys only in development
    ...(import.meta.env.DEV
      ? {
          missingKeyHandler: (lngs, ns, key) => {
            // eslint-disable-next-line no-console
            console.warn(`[i18n] Missing key: "${key}" for lang(s): ${lngs.join(', ')}`);
          },
          saveMissing: true,
        }
      : {}),
  });
}

export default i18n;
