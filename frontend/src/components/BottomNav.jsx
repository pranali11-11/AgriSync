import React from 'react';
import { useTranslation } from 'react-i18next';
import { Home, Leaf, Tractor, Users, User, Building2 } from 'lucide-react';

/**
 * Mobile-first Bottom Navigation Bar with large touch targets.
 * @param {object} props
 * @param {string} props.activeTab - Currently active navigation tab.
 * @param {function} props.onSelectTab - Callback when a tab is pressed.
 */
export const BottomNav = ({ activeTab, onSelectTab }) => {
  const { t } = useTranslation();

  const navItems = [
    { id: 'home', label: t('nav.home'), icon: Home },
    { id: 'advisory', label: t('nav.advisory'), icon: Leaf },
    { id: 'machinery', label: t('nav.machinery'), icon: Tractor },
    { id: 'schemes', label: t('nav.schemes'), icon: Building2 },
    { id: 'community', label: t('nav.community'), icon: Users },
    { id: 'profile', label: t('nav.profile'), icon: User },
  ];

  return (
    <nav className="fixed bottom-0 left-0 right-0 z-50 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-t border-slate-200 dark:border-slate-800 py-1 px-2 shadow-lg">
      <div className="max-w-md mx-auto flex items-center justify-around">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activeTab === item.id;
          return (
            <button
              key={item.id}
              onClick={() => onSelectTab(item.id)}
              className={`flex flex-col items-center justify-center min-h-[48px] min-w-[48px] px-2 py-1 rounded-xl transition-all duration-200 ${
                isActive
                  ? 'text-agri-green-700 dark:text-agri-green-400 font-bold scale-105 bg-agri-green-50 dark:bg-agri-green-950/50'
                  : 'text-slate-500 dark:text-slate-400 hover:text-slate-800 dark:hover:text-slate-200'
              }`}
            >
              <Icon className={`w-5 h-5 ${isActive ? 'stroke-[2.5px]' : 'stroke-[1.75px]'}`} />
              <span className="text-[10px] mt-0.5 tracking-tight line-clamp-1">{item.label}</span>
            </button>
          );
        })}
      </div>
    </nav>
  );
};
