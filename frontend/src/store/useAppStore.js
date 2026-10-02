import { create } from 'zustand';
import i18n from '../i18n/i18n';
import { meApi } from '../services/api';

export const useAppStore = create((set, get) => ({
  user: null,
  language: (() => {
    const explicit = localStorage.getItem('agrisync_lang');
    if (explicit) return explicit;
    try {
      const stored = JSON.parse(localStorage.getItem('agrisync-onboarding') || '{}');
      return stored?.state?.language || 'en';
    } catch {
      return 'en';
    }
  })(),
  theme: localStorage.getItem('agrisync_theme') || 'light',

  setUser: (userData) => set({ user: userData }),

  /**
   * Change the active language.
   * 1. Updates i18next so all `t()` calls re-render immediately.
   * 2. Persists in localStorage (agrisync_lang) for page reloads.
   * 3. Syncs to the onboarding Zustand persist store so the wizard also
   *    picks it up on next mount.
   * 4. Fire-and-forget PUT /me so the server remembers the preference.
   */
  setLanguage: (lang) => {
    // Update i18next (triggers re-render of all useTranslation hooks)
    i18n.changeLanguage(lang);

    // Persist in the simple localStorage key
    localStorage.setItem('agrisync_lang', lang);

    // Also sync to the Zustand persist store's language field
    try {
      const raw = JSON.parse(localStorage.getItem('agrisync-onboarding') || '{}');
      if (raw?.state) {
        raw.state.language = lang;
        localStorage.setItem('agrisync-onboarding', JSON.stringify(raw));
      }
    } catch {
      // non-critical, ignore
    }

    set({ language: lang });

    // Sync to backend profile (fire-and-forget)
    meApi.update({ language: lang }).catch(() => {/* non-critical */});
  },

  setTheme: (themeMode) => {
    localStorage.setItem('agrisync_theme', themeMode);
    if (themeMode === 'dark') {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
    set({ theme: themeMode });
  },

  toggleTheme: () => {
    const nextTheme = get().theme === 'dark' ? 'light' : 'dark';
    get().setTheme(nextTheme);
  },
}));
