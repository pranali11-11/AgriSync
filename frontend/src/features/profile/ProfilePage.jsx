import React, { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { ChevronRight, LogOut, MapPin, Sprout, UserRound, Save, Loader2 } from "lucide-react";
import toast from "react-hot-toast";
import { useOnboardingStore } from "../../store/useOnboardingStore";
import { AppBottomNav } from "../../components/AppBottomNav";
import { meApi } from "../../services/api";

export default function ProfilePage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { userName, phone, language, village, district, state, setUserName } =
    useOnboardingStore();

  const [nameInput, setNameInput] = useState(userName || "");
  const [isSaving, setIsSaving] = useState(false);

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    const cleanName = nameInput.trim();
    if (!cleanName || cleanName.length < 2 || cleanName.length > 60) {
      toast.error(t('profile.name_error'));
      return;
    }

    setIsSaving(true);
    try {
      const response = await meApi.update({
        name: cleanName,
        language: language || "en",
      });
      setUserName(response.data.name || cleanName);
      toast.success(t('profile.save_success'));
    } catch (err) {
      const msg = err.response?.data?.detail || t('profile.save_error');
      toast.error(msg);
    } finally {
      setIsSaving(false);
    }
  };

  const signOut = () => {
    useOnboardingStore.setState({
      token: null,
      refreshToken: null,
      userId: null,
      farmId: null,
      step: 0,
    });
    navigate("/", { replace: true });
  };

  return (
    <main className="min-h-screen bg-[#f5f7f2] px-5 pb-24 pt-8 text-slate-900">
      <div className="mx-auto max-w-xl space-y-5">
        <header>
          <p className="text-sm font-bold uppercase tracking-[0.18em] text-emerald-700">
            {t('app.name')}
          </p>
          <h1 className="mt-1 text-3xl font-black">{t('profile.title')}</h1>
        </header>

        {/* User Card */}
        <section className="rounded-3xl bg-white p-5 shadow-sm">
          <div className="flex items-center gap-4">
            <div className="flex h-16 w-16 items-center justify-center rounded-full bg-emerald-100 text-emerald-800">
              <UserRound className="h-8 w-8" />
            </div>
            <div>
              <h2 className="text-xl font-black">{userName || t('profile.farmer_fallback')}</h2>
              <p className="text-sm text-slate-500">
                {phone || t('profile.phone_empty')}
              </p>
            </div>
          </div>
        </section>

        {/* Name / Profile Settings Form */}
        <section className="rounded-2xl bg-white p-5 shadow-sm space-y-4">
          <h3 className="text-base font-black text-slate-800">{t('profile.personal_info')}</h3>
          <form onSubmit={handleSaveProfile} className="space-y-4">
            <div>
              <label
                htmlFor="user-name-input"
                className="block text-sm font-semibold text-slate-600 mb-1"
              >
                {t('profile.your_name_label')}
              </label>
              <input
                id="user-name-input"
                type="text"
                maxLength={60}
                value={nameInput}
                onChange={(e) => setNameInput(e.target.value)}
                placeholder={t('profile.name_placeholder')}
                className="block w-full rounded-xl border border-slate-200 bg-slate-50 px-4 py-3 text-base font-semibold text-slate-800 focus:border-emerald-600 focus:bg-white focus:outline-none transition-colors"
              />
              <p className="mt-1 text-xs text-slate-400">
                {t('profile.name_hint')}
              </p>
            </div>

            <button
              type="submit"
              disabled={isSaving || !nameInput.trim() || nameInput.trim() === userName}
              className="inline-flex items-center justify-center gap-2 rounded-xl bg-emerald-700 hover:bg-emerald-800 px-5 py-3 text-sm font-bold text-white shadow-md shadow-emerald-700/20 active:scale-[0.98] transition-all disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isSaving ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <Save className="h-4 w-4" />
              )}
              <span>{t('profile.save_name')}</span>
            </button>
          </form>
        </section>

        {/* Farm & App Details */}
        <section className="overflow-hidden rounded-2xl bg-white shadow-sm">
          <button
            onClick={() => navigate("/onboarding")}
            className="flex min-h-14 w-full items-center gap-3 border-b border-slate-100 px-4 text-left font-bold"
          >
            <Sprout className="h-5 w-5 text-emerald-700" /> {t('profile.update_farm')}{" "}
            <ChevronRight className="ml-auto h-5 w-5 text-slate-400" />
          </button>
          <div className="flex items-start gap-3 px-4 py-4">
            <MapPin className="mt-0.5 h-5 w-5 text-emerald-700" />
            <div>
              <p className="font-bold">{t('profile.farm_location')}</p>
              <p className="text-sm text-slate-500">
                {[village, district, state].filter(Boolean).join(", ") ||
                  t('profile.location_empty')}
              </p>
            </div>
          </div>
          <div className="px-4 pb-4 text-sm text-slate-500">
            {t('profile.language_label')}: {language || "en"}
          </div>
        </section>

        <button
          onClick={signOut}
          className="flex min-h-12 w-full items-center justify-center gap-2 rounded-xl border border-red-200 bg-white font-bold text-red-700 hover:bg-red-50 transition-colors"
        >
          <LogOut className="h-5 w-5" /> {t('profile.sign_out')}
        </button>
      </div>
      <AppBottomNav />
    </main>
  );
}
