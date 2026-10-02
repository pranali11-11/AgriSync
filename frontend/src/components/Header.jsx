import React from 'react';
import PropTypes from 'prop-types';
import { useTranslation } from 'react-i18next';
import { useAppStore } from '../store/useAppStore';
import { Sprout, Globe, Sun, Moon, Wifi, WifiOff } from 'lucide-react';

import { useOnboardingStore } from '../store/useOnboardingStore';

/**
 * Mobile-first application Header with branding, language picker, dark mode toggle, and connectivity status.
 * @param {object} props
 * @param {boolean} props.isConnected - Whether backend is reachable.
 */
export const Header = ({ isConnected }) => {
  const { t } = useTranslation();
  const { language, setLanguage, theme, toggleTheme } = useAppStore();
  const { userName } = useOnboardingStore();

  return (
    <header className="sticky top-0 z-50 glass-card rounded-none border-x-0 border-t-0 px-4 py-3 shadow-sm bg-white/90 dark:bg-slate-900/90 backdrop-blur-md">
      <div className="max-w-md mx-auto flex items-center justify-between">
        {/* Brand logo & title */}
        <div className="flex items-center space-x-2.5">
          <div className="w-10 h-10 rounded-xl bg-agri-green-700 text-white flex items-center justify-center shadow-md">
            <Sprout className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <h1 className="font-bold text-lg leading-tight tracking-tight text-agri-green-900 dark:text-agri-green-100">
              {userName ? `Namaste, ${userName}` : t('app.name')}
            </h1>
            <p className="text-[11px] text-slate-500 dark:text-slate-400 font-medium line-clamp-1">
              {userName ? t('app.name') : t('app.tagline')}
            </p>
          </div>
        </div>

        {/* Right Controls */}
        <div className="flex items-center space-x-2">
          {/* Connection Status Badge */}
          <div className={`flex items-center space-x-1 text-[11px] px-2 py-1 rounded-full font-medium ${
            isConnected
              ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300'
              : 'bg-rose-100 text-rose-800 dark:bg-rose-950 dark:text-rose-300'
          }`}>
            {isConnected ? (
              <>
                <Wifi className="w-3.5 h-3.5 text-emerald-600 dark:text-emerald-400" />
                <span className="hidden sm:inline">{t('app.online')}</span>
              </>
            ) : (
              <>
                <WifiOff className="w-3.5 h-3.5 text-rose-600 dark:text-rose-400" />
                <span className="hidden sm:inline">{t('app.offline')}</span>
              </>
            )}
          </div>

          {/* Language Selector */}
          <div className="relative flex items-center">
            <Globe className="w-4 h-4 absolute left-2 text-slate-500 pointer-events-none" />
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              aria-label={t('language.select')}
              className="pl-7 pr-2 py-1.5 text-xs font-semibold rounded-lg bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-slate-700 focus:outline-none focus:ring-2 focus:ring-agri-green-600 touch-target cursor-pointer min-h-[38px]"
            >
              <option value="en">EN</option>
              <option value="hi">हिन्दी</option>
              <option value="mr">मराठी</option>
            </select>
          </div>

          {/* Theme Toggle Button */}
          <button
            onClick={toggleTheme}
            aria-label="Toggle dark mode"
            className="p-2 rounded-lg bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 transition-colors touch-target min-h-[38px] min-w-[38px]"
          >
            {theme === 'dark' ? (
              <Sun className="w-4 h-4 text-amber-400" />
            ) : (
              <Moon className="w-4 h-4 text-slate-600" />
            )}
          </button>
        </div>
      </div>
    </header>
  );
};

Header.propTypes = {
  isConnected: PropTypes.bool,
};

Header.defaultProps = {
  isConnected: true,
};
