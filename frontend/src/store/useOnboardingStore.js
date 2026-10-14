import { create } from 'zustand';
import { persist } from 'zustand/middleware';

export const useOnboardingStore = create(
  persist(
    (set, get) => ({
      step: 0,
      // Data collected through the wizard
      language: 'en',
      selectedCropId: null,
      selectedCropName: null,
      sowingDate: '',
      areaAcres: '',
      soilType: '',
      irrigationType: '',
      irrigationTypeNote: '',
      village: '',
      district: '',
      state: '',
      lat: null,
      lng: null,
      // Auth
      phone: '',
      token: null,
      refreshToken: null,
      userId: null,
      userName: '',
      userRole: 'farmer',  // 'farmer' | 'provider'
      farmId: null,

      // Navigation
      nextStep: () => set((s) => ({ step: Math.min(s.step + 1, 7) })),
      prevStep: () => set((s) => ({ step: Math.max(s.step - 1, 0) })),
      goToStep: (n) => set({ step: n }),

      // Data setters
      setLanguage: (lang) => set({ language: lang }),
      setCrop: (id, name) => set({ selectedCropId: id, selectedCropName: name }),
      setSowingDate: (date) => set({ sowingDate: date }),
      setArea: (acres) => set({ areaAcres: acres }),
      setSoil: (soil, irrigation, irrigationTypeNote = '') =>
        set({ soilType: soil, irrigationType: irrigation, irrigationTypeNote }),
      setLocation: (village, district, state, lat, lng) =>
        set({ village, district, state, lat, lng }),
      setAuth: (token, refreshToken, userId, name, role = 'farmer') =>
        set({ token, refreshToken, userId, userName: name, userRole: role }),
      setPhone: (phone) => set({ phone }),
      setUserName: (name) => set({ userName: name }),
      setFarmId: (farmId) => set({ farmId }),

      // Reset wizard (keep language & auth)
      resetWizard: () =>
        set((s) => ({
          step: 2,
          selectedCropId: null,
          selectedCropName: null,
          sowingDate: '',
          areaAcres: '',
          soilType: '',
          irrigationType: '',
          irrigationTypeNote: '',
        })),
    }),
    {
      name: 'agrisync-onboarding',
      partialize: (state) => ({
        language: state.language,
        token: state.token,
        refreshToken: state.refreshToken,
        userId: state.userId,
        userName: state.userName,
        userRole: state.userRole,
        farmId: state.farmId,
        phone: state.phone,
        step: state.step,
        // persist partial wizard data in case of app restart
        selectedCropId: state.selectedCropId,
        selectedCropName: state.selectedCropName,
        sowingDate: state.sowingDate,
        areaAcres: state.areaAcres,
        soilType: state.soilType,
        irrigationType: state.irrigationType,
        irrigationTypeNote: state.irrigationTypeNote,
        village: state.village,
        district: state.district,
        state: state.state,
        lat: state.lat,
        lng: state.lng,
      }),
    }
  )
);
