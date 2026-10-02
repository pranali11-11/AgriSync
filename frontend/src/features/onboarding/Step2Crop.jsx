import React, { useState, useMemo } from 'react';
import PropTypes from 'prop-types';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { Search, Loader2, Sprout, X, Check } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { cropsApi } from '../../services/api';
import { useOnboardingStore } from '../../store/useOnboardingStore';

const CROP_EMOJIS = {
  wheat: '🌾',
  rice: '🍚',
  maize: '🌽',
  bajra: '🥣',
  jowar: '🌾',
  cotton: '☁️',
  soybean: '🫘',
  sugarcane: '🎋',
  groundnut: '🥜',
  tur: '🫘',
  arhar: '🫘',
  gram: '🫘',
  chana: '🫘',
  moong: '🌱',
  urad: '🫘',
  mustard: '🌼',
  onion: '🧅',
  tomato: '🍅',
  potato: '🥔',
  turmeric: '🟡',
  chilli: '🌶️',
  chili: '🌶️',
  ginger: '🫚',
};

const CATEGORY_PLACEHOLDERS = {
  cereal: '🌾',
  pulse: '🫘',
  oilseed: '🌻',
  'cash crop': '💰',
  vegetable: '🥬',
  spice: '🌶️',
  other: '🌱',
};

const CATEGORIES_ORDER = [
  'all',
  'cereal',
  'pulse',
  'oilseed',
  'cash crop',
  'vegetable',
  'spice',
];

const CATEGORY_META = {
  all: { label: 'All', icon: '🌱' },
  cereal: { label: 'Cereals', icon: '🌾' },
  pulse: { label: 'Pulses', icon: '🫘' },
  oilseed: { label: 'Oilseeds', icon: '🌻' },
  'cash crop': { label: 'Cash Crops', icon: '💰' },
  vegetable: { label: 'Vegetables', icon: '🥬' },
  spice: { label: 'Spices', icon: '🌶️' },
  other: { label: 'Other', icon: '🌱' },
};

const getCropEmoji = (crop) => {
  if (!crop) return '🌱';
  const name = (crop.name || '').toLowerCase();
  for (const [key, emoji] of Object.entries(CROP_EMOJIS)) {
    if (name.includes(key)) return emoji;
  }
  const cat = (crop.category || '').toLowerCase();
  return CATEGORY_PLACEHOLDERS[cat] || '🌱';
};

export const Step2Crop = ({ onNext }) => {
  const { t, i18n } = useTranslation();
  const { setCrop, selectedCropId } = useOnboardingStore();
  const [search, setSearch] = useState('');
  const [activeCategory, setActiveCategory] = useState('all');

  const { data: crops = [], isLoading } = useQuery({
    queryKey: ['crops'],
    queryFn: () => cropsApi.list().then((r) => r.data),
    staleTime: 10 * 60 * 1000,
  });

  const getLangName = (crop) => {
    if (i18n.language === 'hi') return crop.name_hi || crop.name;
    if (i18n.language === 'mr') return crop.name_mr || crop.name;
    return crop.name;
  };

  const getCategoryLabel = (catKey) => {
    const i18nLabel = t(`crop.categories.${catKey}`, { defaultValue: '' });
    if (i18nLabel) return i18nLabel;
    return CATEGORY_META[catKey]?.label || catKey;
  };

  // Live filter: search text matches English name, localized names, or category
  const filteredCrops = useMemo(() => {
    const q = search.trim().toLowerCase();
    return crops.filter((c) => {
      const cat = (c.category || 'other').toLowerCase();
      const catLabel = (CATEGORY_META[cat]?.label || '').toLowerCase();
      const matchesSearch = !q || [c.name, c.name_hi, c.name_mr, cat, catLabel]
        .filter(Boolean)
        .some((n) => n.toLowerCase().includes(q));

      const matchesCat = activeCategory === 'all' || cat === activeCategory;
      return matchesSearch && matchesCat;
    });
  }, [crops, search, activeCategory]);

  // Group filtered crops by category
  const groupedCategories = useMemo(() => {
    const map = new Map();
    for (const crop of filteredCrops) {
      const cat = (crop.category || 'other').toLowerCase();
      if (!map.has(cat)) {
        map.set(cat, []);
      }
      map.get(cat).push(crop);
    }

    // Preserve order: cereal, pulse, oilseed, cash crop, vegetable, spice, other
    const ordered = [];
    for (const key of CATEGORIES_ORDER.slice(1)) {
      if (map.has(key)) {
        ordered.push({ key, crops: map.get(key) });
      }
    }
    // Any remaining categories not explicitly in CATEGORIES_ORDER
    for (const [key, cropList] of map.entries()) {
      if (!CATEGORIES_ORDER.includes(key)) {
        ordered.push({ key, crops: cropList });
      }
    }
    return ordered;
  }, [filteredCrops]);

  // Total counts per category from all crops (for badge indicators on tabs)
  const categoryCounts = useMemo(() => {
    const counts = { all: crops.length };
    for (const c of crops) {
      const cat = (c.category || 'other').toLowerCase();
      counts[cat] = (counts[cat] || 0) + 1;
    }
    return counts;
  }, [crops]);

  const handleSelect = (crop) => {
    setCrop(crop.id, getLangName(crop));
    setTimeout(onNext, 250);
  };

  const renderCropCard = (crop) => {
    const name = getLangName(crop);
    const emoji = getCropEmoji(crop);
    const selected = crop.id === selectedCropId;

    return (
      <motion.button
        key={crop.id}
        layout
        initial={{ opacity: 0, scale: 0.9 }}
        animate={{ opacity: 1, scale: 1 }}
        exit={{ opacity: 0, scale: 0.9 }}
        transition={{ type: 'spring', stiffness: 300, damping: 25 }}
        whileTap={{ scale: 0.96 }}
        onClick={() => handleSelect(crop)}
        id={`crop-${crop.id}`}
        className={`
          relative flex flex-col items-center justify-between py-4 px-3 rounded-2xl border-2 transition-all text-center group
          ${selected
            ? 'border-agri-green-500 bg-agri-green-50 dark:bg-agri-green-950/40 shadow-md ring-2 ring-agri-green-500/20'
            : 'border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 hover:border-agri-green-400 hover:shadow-sm'}
        `}
      >
        {selected && (
          <div className="absolute top-2 right-2 w-5 h-5 rounded-full bg-agri-green-600 text-white flex items-center justify-center shadow-sm">
            <Check className="w-3 h-3 stroke-[3]" />
          </div>
        )}
        <span className="text-4xl mb-2 drop-shadow-sm transition-transform group-hover:scale-110">
          {emoji}
        </span>
        <div className="w-full min-h-[2.5rem] flex flex-col items-center justify-center">
          <span className="text-sm font-bold text-slate-800 dark:text-slate-100 leading-snug">
            {name}
          </span>
          {i18n.language !== 'en' && crop.name !== name && (
            <span className="text-[11px] font-medium text-slate-400 dark:text-slate-500 truncate max-w-full">
              {crop.name}
            </span>
          )}
        </div>
        {crop.duration_days && (
          <span className="mt-2 text-[10px] font-semibold text-slate-500 dark:text-slate-400 bg-slate-100 dark:bg-slate-700/60 px-2 py-0.5 rounded-full">
            {crop.duration_days} {t('crop.days')}
          </span>
        )}
      </motion.button>
    );
  };

  return (
    <div className="flex flex-col">
      {/* Title Header */}
      <div className="text-center mb-6">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 220 }}
          className="text-5xl mb-3"
        >
          🌾
        </motion.div>
        <h2 className="text-2xl font-black text-slate-800 dark:text-slate-100">
          {t('crop.select_title')}
        </h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">
          {t('crop.select_subtitle')}
        </p>
      </div>

      {/* Live Search Box */}
      <div className="relative mb-4">
        <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
        <input
          id="crop-search"
          type="text"
          placeholder="Search crop..."
          className="block w-full rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 pl-10 pr-9 py-3 text-sm font-medium text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:outline-none focus:border-agri-green-500 transition-colors"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
        {search && (
          <button
            type="button"
            onClick={() => setSearch('')}
            aria-label="Clear search"
            className="absolute right-3 top-1/2 -translate-y-1/2 p-1 rounded-full text-slate-400 hover:text-slate-600 dark:hover:text-slate-200"
          >
            <X className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* Category Tabs */}
      <div className="mb-5 overflow-x-auto no-scrollbar -mx-1 px-1 pb-1">
        <div className="flex gap-2 min-w-max">
          {CATEGORIES_ORDER.map((catKey) => {
            const count = categoryCounts[catKey] ?? 0;
            if (catKey !== 'all' && count === 0) return null;
            const meta = CATEGORY_META[catKey] || { label: catKey, icon: '🌱' };
            const isActive = activeCategory === catKey;

            return (
              <button
                key={catKey}
                type="button"
                id={`tab-${catKey}`}
                onClick={() => setActiveCategory(catKey)}
                className={`
                  flex items-center gap-1.5 px-3.5 py-1.5 rounded-full text-xs font-bold transition-all
                  ${isActive
                    ? 'bg-agri-green-700 text-white shadow-sm shadow-agri-green-700/30'
                    : 'bg-slate-100 dark:bg-slate-800 text-slate-600 dark:text-slate-300 hover:bg-slate-200 dark:hover:bg-slate-700'}
                `}
              >
                <span>{meta.icon}</span>
                <span>{getCategoryLabel(catKey)}</span>
                <span
                  className={`text-[10px] px-1.5 py-0.2 rounded-full ${
                    isActive
                      ? 'bg-white/20 text-white'
                      : 'bg-slate-200 dark:bg-slate-700 text-slate-500 dark:text-slate-400'
                  }`}
                >
                  {count}
                </span>
              </button>
            );
          })}
        </div>
      </div>

      {/* Crop Grid & Category Sections */}
      {isLoading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="w-8 h-8 animate-spin text-agri-green-600" />
        </div>
      ) : filteredCrops.length === 0 ? (
        <div className="py-12 text-center bg-white dark:bg-slate-800 rounded-3xl border border-slate-200 dark:border-slate-700 p-6">
          <Sprout className="w-10 h-10 mx-auto text-slate-300 dark:text-slate-600 mb-3" />
          <p className="text-sm font-semibold text-slate-600 dark:text-slate-300">
            {t('crop.not_found')}
          </p>
          {(search || activeCategory !== 'all') && (
            <button
              type="button"
              onClick={() => {
                setSearch('');
                setActiveCategory('all');
              }}
              className="mt-4 px-4 py-2 text-xs font-bold text-agri-green-700 dark:text-agri-green-300 bg-agri-green-50 dark:bg-agri-green-950/60 rounded-xl hover:bg-agri-green-100 transition-colors"
            >
              {t('crop.clear_search', { defaultValue: 'Show all crops' })}
            </button>
          )}
        </div>
      ) : activeCategory === 'all' ? (
        /* Grouped Under Category Section Headers */
        <div className="space-y-6 pb-6">
          {groupedCategories.map(({ key, crops: catCrops }) => {
            const meta = CATEGORY_META[key] || { label: key, icon: '🌱' };
            return (
              <section key={key} id={`section-${key}`} className="space-y-2.5">
                <div className="flex items-center justify-between px-1">
                  <div className="flex items-center gap-2">
                    <span className="text-lg">{meta.icon}</span>
                    <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-700 dark:text-slate-200">
                      {getCategoryLabel(key)}
                    </h3>
                  </div>
                  <span className="text-[11px] font-bold text-slate-400 dark:text-slate-500 bg-slate-100 dark:bg-slate-800/80 px-2 py-0.5 rounded-full">
                    {catCrops.length}
                  </span>
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <AnimatePresence>
                    {catCrops.map((crop) => renderCropCard(crop))}
                  </AnimatePresence>
                </div>
              </section>
            );
          })}
        </div>
      ) : (
        /* Single Selected Category View */
        <div className="space-y-2.5 pb-6">
          <div className="flex items-center justify-between px-1 mb-2">
            <div className="flex items-center gap-2">
              <span className="text-lg">{CATEGORY_META[activeCategory]?.icon || '🌱'}</span>
              <h3 className="text-xs font-extrabold uppercase tracking-wider text-slate-700 dark:text-slate-200">
                {getCategoryLabel(activeCategory)}
              </h3>
            </div>
            <span className="text-[11px] font-bold text-slate-400 dark:text-slate-500 bg-slate-100 dark:bg-slate-800/80 px-2 py-0.5 rounded-full">
              {filteredCrops.length}
            </span>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <AnimatePresence>
              {filteredCrops.map((crop) => renderCropCard(crop))}
            </AnimatePresence>
          </div>
        </div>
      )}
    </div>
  );
};

Step2Crop.propTypes = { onNext: PropTypes.func.isRequired };
