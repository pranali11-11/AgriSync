import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { motion } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { MapContainer, TileLayer, Marker, useMapEvents } from 'react-leaflet';
import { ChevronRight, MapPin, Loader2 } from 'lucide-react';
import toast from 'react-hot-toast';
import 'leaflet/dist/leaflet.css';
import L from 'leaflet';
import { useOnboardingStore } from '../../store/useOnboardingStore';

// Fix default leaflet marker icon
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
});

const DEFAULT_CENTER = [20.5937, 78.9629]; // Center of India

function ClickableMap({ onMarker }) {
  useMapEvents({
    click(e) { onMarker(e.latlng.lat, e.latlng.lng); },
  });
  return null;
}

ClickableMap.propTypes = { onMarker: PropTypes.func.isRequired };

export const Step6Location = ({ onNext }) => {
  const { t } = useTranslation();
  const { village, district, state, lat, lng, setLocation } = useOnboardingStore();

  const [villageVal, setVillage] = useState(village || '');
  const [districtVal, setDistrict] = useState(district || '');
  const [stateVal, setState] = useState(state || '');
  const [markerPos, setMarkerPos] = useState(lat && lng ? [lat, lng] : null);
  const [geoLoading, setGeoLoading] = useState(false);

  const handleGPSLocate = () => {
    if (!navigator.geolocation) {
      toast.error(t('location.gps_unsupported'));
      return;
    }
    setGeoLoading(true);
    navigator.geolocation.getCurrentPosition(
      ({ coords }) => {
        setMarkerPos([coords.latitude, coords.longitude]);
        setGeoLoading(false);
        toast.success(t('location.gps_found'));
      },
      () => {
        toast.error(t('location.gps_error'));
        setGeoLoading(false);
      },
      { timeout: 8000 }
    );
  };

  const handleNext = () => {
    if (!villageVal.trim()) { toast.error(t('location.village_required')); return; }
    if (!districtVal.trim()) { toast.error(t('location.district_required')); return; }
    if (!stateVal.trim()) { toast.error(t('location.state_required')); return; }
    setLocation(
      villageVal.trim(), districtVal.trim(), stateVal.trim(),
      markerPos ? markerPos[0] : null,
      markerPos ? markerPos[1] : null
    );
    onNext();
  };

  const inputClass =
    'block w-full rounded-xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-900 px-4 py-3 text-sm font-semibold text-slate-800 dark:text-slate-100 focus:outline-none focus:border-agri-green-500 transition-colors placeholder:text-slate-300 dark:placeholder:text-slate-600';

  return (
    <div className="flex flex-col">
      <div className="text-center mb-7">
        <motion.div
          initial={{ scale: 0 }}
          animate={{ scale: 1 }}
          transition={{ type: 'spring', stiffness: 200 }}
          className="text-6xl mb-4"
        >
          📍
        </motion.div>
        <h2 className="text-2xl font-black text-slate-800 dark:text-slate-100">{t('location.title')}</h2>
        <p className="text-sm text-slate-500 dark:text-slate-400 mt-1">{t('location.subtitle')}</p>
      </div>

      {/* Text Fields */}
      <div className="bg-white dark:bg-slate-800 rounded-3xl border-2 border-slate-200 dark:border-slate-700 p-5 shadow-sm space-y-3 mb-4">
        <input id="village-input" className={inputClass} placeholder={t('location.village_placeholder')}
          value={villageVal} onChange={(e) => setVillage(e.target.value)} />
        <input id="district-input" className={inputClass} placeholder={t('location.district_placeholder')}
          value={districtVal} onChange={(e) => setDistrict(e.target.value)} />
        <input id="state-input" className={inputClass} placeholder={t('location.state_placeholder')}
          value={stateVal} onChange={(e) => setState(e.target.value)} />
      </div>

      {/* Map */}
      <div className="mb-4">
        <div className="flex items-center justify-between mb-2">
          <p className="text-sm font-semibold text-slate-600 dark:text-slate-300">{t('location.map_hint')}</p>
          <button
            onClick={handleGPSLocate}
            disabled={geoLoading}
            className="flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-agri-green-50 dark:bg-agri-green-900/30 border border-agri-green-200 dark:border-agri-green-700 text-agri-green-700 dark:text-agri-green-300 text-xs font-bold hover:bg-agri-green-100 transition-all"
          >
            {geoLoading ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : <MapPin className="w-3.5 h-3.5" />}
            <span>{t('location.gps_btn')}</span>
          </button>
        </div>

        <div className="rounded-2xl overflow-hidden h-52 border-2 border-slate-200 dark:border-slate-700 shadow-sm">
          <MapContainer
            center={markerPos || DEFAULT_CENTER}
            zoom={markerPos ? 13 : 5}
            style={{ height: '100%', width: '100%' }}
            className="z-10"
          >
            <TileLayer
              url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
              attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            />
            <ClickableMap onMarker={(lt, lg) => setMarkerPos([lt, lg])} />
            {markerPos && <Marker position={markerPos} />}
          </MapContainer>
        </div>
        {markerPos && (
          <p className="mt-1 text-xs text-slate-400 dark:text-slate-500 text-center">
            {markerPos[0].toFixed(5)}, {markerPos[1].toFixed(5)}
          </p>
        )}
      </div>

      <button
        id="location-next-btn"
        onClick={handleNext}
        className="w-full py-4 rounded-2xl bg-agri-green-700 hover:bg-agri-green-800 text-white font-bold text-lg shadow-lg shadow-agri-green-700/30 transition-all active:scale-[0.98] flex items-center justify-center space-x-2"
      >
        <span>{t('common.next')}</span>
        <ChevronRight className="w-5 h-5" />
      </button>
    </div>
  );
};

Step6Location.propTypes = { onNext: PropTypes.func.isRequired };
