import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { motion, AnimatePresence } from 'framer-motion';
import { useTranslation } from 'react-i18next';
import { Smartphone, Loader2, KeyRound, CheckCircle2, RotateCcw, User as UserIcon, Tractor, Wrench, ChevronDown } from 'lucide-react';
import toast from 'react-hot-toast';
import { authApi } from '../../services/api';
import { useOnboardingStore } from '../../store/useOnboardingStore';

const INPUT_CLASS =
  'block w-full rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-4 text-lg font-semibold text-slate-800 dark:text-slate-100 focus:outline-none focus:border-agri-green-500 dark:focus:border-agri-green-400 transition-colors placeholder:text-slate-300 dark:placeholder:text-slate-600';

const BTN_CLASS =
  'w-full py-4 rounded-2xl text-white font-bold text-lg bg-agri-green-700 hover:bg-agri-green-800 active:scale-[0.98] shadow-lg shadow-agri-green-700/30 transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2';

export const Step0Login = ({ onCompleted }) => {
  const { t } = useTranslation();
  const { setAuth, setPhone } = useOnboardingStore();
  const [phone, setPhoneLocal] = useState('');
  const [name, setName] = useState('');
  const [otp, setOtp] = useState('');
  const [stage, setStage] = useState('phone'); // 'phone' | 'otp' | 'success'
  const [loading, setLoading] = useState(false);
  const [isNewUser, setIsNewUser] = useState(false);
  const [cooldown, setCooldown] = useState(0);
  const [devOtp, setDevOtp] = useState(''); // Only populated in dev/non-production mode
  // Role selection — only visible to new users
  const [selectedRole, setSelectedRole] = useState('farmer');
  const [orgType, setOrgType] = useState('owner');

  // 30-second cooldown timer for Resend OTP
  useEffect(() => {
    if (cooldown <= 0) return;
    const interval = setInterval(() => {
      setCooldown((prev) => Math.max(0, prev - 1));
    }, 1000);
    return () => clearInterval(interval);
  }, [cooldown]);

  const cleanPhone = phone.replace(/\D/g, '').slice(-10);

  const handleRequestOtp = async () => {
    if (cleanPhone.length < 10) {
      toast.error(t('auth.invalid_phone'));
      return;
    }
    setLoading(true);
    try {
      const res = await authApi.requestOtp(cleanPhone);
      setPhone(cleanPhone);
      setIsNewUser(Boolean(res.data?.is_new_user));
      setCooldown(30);
      setStage('otp');
      if (res.data?.dev_otp) {
        setDevOtp(res.data.dev_otp);
        toast(
          <span>🛠 <strong>Dev OTP:</strong> <code style={{letterSpacing:'0.15em',fontWeight:700}}>{res.data.dev_otp}</code></span>,
          { duration: 15000, style: { background: '#1e3a25', color: '#86efac', border: '1px solid #15803d', borderRadius: '14px' } }
        );
      } else {
        toast.success(t('auth.otp_sent'));
      }
    } catch (e) {
      const msg = e.response?.data?.detail || t('auth.request_failed');
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleResendOtp = async () => {
    if (cooldown > 0 || loading) return;
    setLoading(true);
    try {
      const res = await authApi.requestOtp(cleanPhone);
      setIsNewUser(Boolean(res.data?.is_new_user));
      setCooldown(30);
      if (res.data?.dev_otp) {
        setDevOtp(res.data.dev_otp);
        toast(
          <span>🛠 <strong>Dev OTP:</strong> <code style={{letterSpacing:'0.15em',fontWeight:700}}>{res.data.dev_otp}</code></span>,
          { duration: 15000, style: { background: '#1e3a25', color: '#86efac', border: '1px solid #15803d', borderRadius: '14px' } }
        );
      } else {
        toast.success(t('auth.otp_sent'));
      }
    } catch (e) {
      const msg = e.response?.data?.detail || t('auth.request_failed');
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  const handleVerifyOtp = async () => {
    if (otp.length !== 6) {
      toast.error(t('auth.invalid_otp'));
      return;
    }

    if (isNewUser) {
      const trimmedName = name.trim();
      if (!trimmedName || trimmedName.length < 2 || trimmedName.length > 60) {
        toast.error(t('auth.name_required') || 'Please enter your name (2-60 characters).');
        return;
      }
    }

    setLoading(true);
    try {
      const { data } = await authApi.verifyOtp(
        cleanPhone,
        otp,
        isNewUser ? name.trim() : undefined,
        isNewUser ? selectedRole : undefined,
        isNewUser ? orgType : undefined,
      );
      const user = data.user || {};
      setAuth(data.access_token, data.refresh_token, user.id, user.name || '', user.role || 'farmer');
      setStage('success');
      setTimeout(onCompleted, 800);
    } catch (e) {
      const msg = e.response?.data?.detail || t('auth.otp_wrong');
      toast.error(msg);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col min-h-[70vh] justify-center">
      {/* Hero */}
      <div className="text-center mb-10">
        <motion.div
          initial={{ scale: 0, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ type: 'spring', stiffness: 200 }}
          className="w-24 h-24 mx-auto mb-5 rounded-3xl bg-gradient-to-br from-agri-green-500 to-agri-green-800 flex items-center justify-center shadow-2xl"
        >
          {stage === 'success' ? (
            <CheckCircle2 className="w-12 h-12 text-white" />
          ) : stage === 'otp' ? (
            <KeyRound className="w-12 h-12 text-white" />
          ) : (
            <Smartphone className="w-12 h-12 text-white" />
          )}
        </motion.div>

        <motion.h1
          key={stage}
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          className="text-2xl font-black text-slate-800 dark:text-slate-100"
        >
          {stage === 'success'
            ? t('auth.welcome_back')
            : stage === 'otp'
            ? t('auth.enter_otp')
            : t('auth.welcome_title')}
        </motion.h1>
        <p className="mt-2 text-sm text-slate-500 dark:text-slate-400">
          {stage === 'phone'
            ? t('auth.welcome_subtitle')
            : stage === 'otp'
            ? t('auth.otp_hint')
            : t('auth.success_msg')}
        </p>
      </div>

      {/* Form */}
      {stage !== 'success' && (
        <motion.div
          key={stage + '-form'}
          initial={{ opacity: 0, x: 20 }}
          animate={{ opacity: 1, x: 0 }}
          className="space-y-4"
        >
          {stage === 'phone' && (
            <>
              <div>
                <label className="block text-sm font-semibold text-slate-600 dark:text-slate-300 mb-2">
                  {t('auth.phone_label')}
                </label>
                <input
                  id="phone-input"
                  type="tel"
                  inputMode="numeric"
                  maxLength={14}
                  className={INPUT_CLASS}
                  placeholder={t('auth.phone_placeholder')}
                  value={phone}
                  onChange={(e) => setPhoneLocal(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && handleRequestOtp()}
                />
              </div>
              <button
                id="send-otp-btn"
                onClick={handleRequestOtp}
                disabled={loading}
                className={BTN_CLASS}
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : null}
                <span>{t('auth.send_otp')}</span>
              </button>
            </>
          )}

          {stage === 'otp' && (
            <>
              {isNewUser && (
                <motion.div
                  initial={{ opacity: 0, y: -6 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="space-y-1"
                >
                  <label className="block text-sm font-semibold text-slate-600 dark:text-slate-300 mb-1">
                    {t('auth.name_label')} <span className="text-rose-500">*</span>
                  </label>
                  <div className="relative flex items-center">
                    <UserIcon className="w-5 h-5 absolute left-4 text-slate-400 pointer-events-none" />
                    <input
                      id="name-input"
                      type="text"
                      maxLength={60}
                      className={`${INPUT_CLASS} pl-12 text-base font-medium`}
                      placeholder={t('auth.name_placeholder')}
                      value={name}
                      onChange={(e) => setName(e.target.value)}
                    />
                  </div>
                  <p className="text-xs text-slate-400 dark:text-slate-500 px-1">
                    {t('auth.name_required')}
                  </p>

                  {/* Role toggle */}
                  <div className="pt-3">
                    <p className="text-sm font-semibold text-slate-600 dark:text-slate-300 mb-2">
                      {t('auth.role_label')}
                    </p>
                    <div className="grid grid-cols-2 gap-3">
                      {[
                        { value: 'farmer', icon: <Tractor className="w-5 h-5" />, label: t('auth.role_farmer'), hint: t('auth.role_hint_farmer') },
                        { value: 'provider', icon: <Wrench className="w-5 h-5" />, label: t('auth.role_provider'), hint: t('auth.role_hint_provider') },
                      ].map(({ value, icon, label, hint }) => (
                        <button
                          key={value}
                          type="button"
                          id={`role-${value}-btn`}
                          onClick={() => setSelectedRole(value)}
                          className={`flex flex-col items-center gap-1.5 rounded-2xl border-2 p-3 text-center transition-all ${
                            selectedRole === value
                              ? 'border-agri-green-600 bg-agri-green-50 dark:bg-agri-green-900/30 text-agri-green-700 dark:text-agri-green-300'
                              : 'border-slate-200 dark:border-slate-700 text-slate-500 dark:text-slate-400'
                          }`}
                        >
                          {icon}
                          <span className="text-xs font-bold leading-tight">{label}</span>
                          <span className="text-[10px] leading-tight opacity-70">{hint}</span>
                        </button>
                      ))}
                    </div>
                  </div>

                  {/* org_type selector — only when provider chosen */}
                  <AnimatePresence>
                    {selectedRole === 'provider' && (
                      <motion.div
                        initial={{ opacity: 0, height: 0 }}
                        animate={{ opacity: 1, height: 'auto' }}
                        exit={{ opacity: 0, height: 0 }}
                        className="overflow-hidden pt-2"
                      >
                        <label className="block text-sm font-semibold text-slate-600 dark:text-slate-300 mb-1">
                          {t('auth.org_type_label')}
                        </label>
                        <div className="relative">
                          <select
                            id="org-type-select"
                            value={orgType}
                            onChange={(e) => setOrgType(e.target.value)}
                            className={`${INPUT_CLASS} appearance-none pr-10 text-base font-medium`}
                          >
                            <option value="owner">{t('auth.org_type_owner')}</option>
                            <option value="FPO">{t('auth.org_type_fpo')}</option>
                            <option value="CHC">{t('auth.org_type_chc')}</option>
                            <option value="service">{t('auth.org_type_service')}</option>
                          </select>
                          <ChevronDown className="w-4 h-4 absolute right-4 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none" />
                        </div>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
              )}


              <div>
                <label className="block text-sm font-semibold text-slate-600 dark:text-slate-300 mb-2">
                  {t('auth.otp_label')}
                </label>
                <input
                  id="otp-input"
                  type="text"
                  inputMode="numeric"
                  maxLength={6}
                  className={`${INPUT_CLASS} tracking-[0.4em] text-center text-2xl`}
                  placeholder="••••••"
                  value={otp}
                  onChange={(e) => setOtp(e.target.value.replace(/\D/g, ''))}
                  onKeyDown={(e) => e.key === 'Enter' && handleVerifyOtp()}
                />
                {devOtp && (
                  <div className="mt-2 flex items-center justify-center gap-2 rounded-xl bg-emerald-950 px-3 py-2">
                    <span className="text-xs font-bold text-emerald-400">🛠 Dev OTP:</span>
                    <button
                      type="button"
                      onClick={() => setOtp(devOtp)}
                      className="font-mono text-lg font-black tracking-[0.3em] text-emerald-300 hover:text-white transition-colors"
                      title="Click to auto-fill"
                    >
                      {devOtp}
                    </button>
                    <span className="text-[10px] text-emerald-600">(click to fill)</span>
                  </div>
                )}
              </div>

              <button
                id="verify-otp-btn"
                onClick={handleVerifyOtp}
                disabled={loading}
                className={BTN_CLASS}
              >
                {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : null}
                <span>{t('auth.verify_otp')}</span>
              </button>

              <div className="flex items-center justify-between pt-2">
                <button
                  type="button"
                  id="resend-otp-btn"
                  onClick={handleResendOtp}
                  disabled={cooldown > 0 || loading}
                  className="inline-flex items-center space-x-1.5 text-sm font-semibold text-agri-green-700 dark:text-agri-green-400 hover:underline disabled:opacity-50 disabled:no-underline disabled:cursor-not-allowed transition-all"
                >
                  <RotateCcw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
                  <span>
                    {cooldown > 0
                      ? (t('auth.resend_in', { seconds: cooldown }) || `Resend in ${cooldown}s`)
                      : (t('auth.resend_otp') || 'Resend OTP')}
                  </span>
                </button>

                <button
                  type="button"
                  onClick={() => { setStage('phone'); setOtp(''); setCooldown(0); }}
                  className="text-sm font-semibold text-slate-500 dark:text-slate-400 hover:text-slate-700 dark:hover:text-slate-200 transition-colors"
                >
                  {t('auth.change_phone')}
                </button>
              </div>
            </>
          )}
        </motion.div>
      )}

      {stage === 'success' && (
        <motion.div
          initial={{ scale: 0.8, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          className="text-center mt-4"
        >
          <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-agri-green-100 dark:bg-agri-green-900/40">
            <CheckCircle2 className="w-9 h-9 text-agri-green-600" />
          </div>
        </motion.div>
      )}
    </div>
  );
};

Step0Login.propTypes = { onCompleted: PropTypes.func.isRequired };
