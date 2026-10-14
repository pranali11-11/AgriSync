/**
 * AddMachineForm — full-screen slide-over for listing a new machine.
 *
 * Flow:
 *  1. Fill in machine type, rate, dates, optional description/model year/specs
 *  2. Upload photos (drag-drop or file picker, up to 5)
 *  3. Pick location (GPS or type lat/lng)
 *  4. Submit → POST /provider/machines
 */
import React, { useState, useRef, useCallback } from "react";
import { useTranslation } from "react-i18next";
import { motion } from "framer-motion";
import { useQuery, useMutation } from "@tanstack/react-query";
import {
  X,
  Loader2,
  ImagePlus,
  XCircle,
  MapPin,
  Zap,
  Calendar,
} from "lucide-react";
import toast from "react-hot-toast";
import api, {
  providerMachineApi,
  uploadMachinePhotos,
} from "../../services/api";

const ATTACHMENTS = [
  "rotavator",
  "plough",
  "seeder",
  "sprayer",
  "trailer",
  "harrow",
];

const FIELD =
  "block w-full rounded-2xl border-2 border-slate-200 dark:border-slate-700 bg-white dark:bg-slate-800 px-4 py-3.5 text-sm font-medium text-slate-800 dark:text-slate-100 focus:outline-none focus:border-agri-green-500 transition-colors placeholder:text-slate-300 dark:placeholder:text-slate-600";
const LABEL =
  "block text-sm font-semibold text-slate-600 dark:text-slate-300 mb-1.5";

export default function AddMachineForm({ onClose, onSuccess }) {
  const { t } = useTranslation();
  const fileInputRef = useRef(null);

  // Form state
  const [machineTypeId, setMachineTypeId] = useState("");
  const [ratePerAcre, setRatePerAcre] = useState("");
  const [mobilizationCost, setMobilizationCost] = useState("0");
  const [availableFrom, setAvailableFrom] = useState("");
  const [availableTo, setAvailableTo] = useState("");
  const [description, setDescription] = useState("");
  const [modelYear, setModelYear] = useState("");
  const [horsepower, setHorsepower] = useState("");
  const [attachments, setAttachments] = useState([]);
  const [lat, setLat] = useState("");
  const [lng, setLng] = useState("");
  const [gpsLoading, setGpsLoading] = useState(false);

  // Photo state
  const [photoFiles, setPhotoFiles] = useState([]); // File[]
  const [photoPreviews, setPhotoPreviews] = useState([]); // DataURL[]
  const [uploadError, setUploadError] = useState("");

  // Fetch machine types from resources endpoint (existing)
  const { data: mtListData } = useQuery({
    queryKey: ["machine-type-list"],
    queryFn: () =>
      api.get("/resources/machine-types").then((response) => response.data),
    retry: false,
  });

  const machineTypes = mtListData || [];

  const useGps = () => {
    setGpsLoading(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLat(pos.coords.latitude.toFixed(6));
        setLng(pos.coords.longitude.toFixed(6));
        setGpsLoading(false);
        toast.success("Location captured");
      },
      () => {
        toast.error("Could not get GPS location. Enter manually.");
        setGpsLoading(false);
      },
      { enableHighAccuracy: true, timeout: 8000 },
    );
  };

  const handlePhotoChange = (files) => {
    setUploadError("");
    const toAdd = Array.from(files || []);
    if (photoFiles.length + toAdd.length > 5) {
      setUploadError(t("provider.upload_error_count"));
      return;
    }
    const errors = [];

    const valid = toAdd.filter((f) => {
      if (!["image/jpeg", "image/jpg", "image/png"].includes(f.type)) {
        errors.push(t("provider.upload_error_type"));
        return false;
      }
      if (f.size > 5 * 1024 * 1024) {
        errors.push(t("provider.upload_error_size"));
        return false;
      }
      return true;
    });

    if (errors.length) {
      setUploadError(errors[0]);
      return;
    }
    setPhotoFiles((p) => [...p, ...valid]);
    valid.forEach((f) => {
      const reader = new FileReader();
      reader.onload = (e) => setPhotoPreviews((p) => [...p, e.target.result]);
      reader.readAsDataURL(f);
    });
  };

  const removePhoto = (idx) => {
    setPhotoFiles((p) => p.filter((_, i) => i !== idx));
    setPhotoPreviews((p) => p.filter((_, i) => i !== idx));
  };

  const onDrop = useCallback(
    (e) => {
      e.preventDefault();
      handlePhotoChange(e.dataTransfer.files);
    },
    [photoFiles],
  );

  const mutation = useMutation({
    mutationFn: async () => {
      // 1. Create machine first (without photos to get ID)
      const specs = {};
      if (horsepower) specs.horsepower = Number(horsepower);
      if (attachments.length) specs.attachments = attachments;

      const payload = {
        machine_type_id: Number(machineTypeId),
        rate_per_acre: Number(ratePerAcre),
        mobilization_cost: Number(mobilizationCost) || 0,
        available_from: availableFrom,
        available_to: availableTo,
        latitude: Number(lat),
        longitude: Number(lng),
        description: description || null,
        model_year: modelYear ? Number(modelYear) : null,
        specifications: Object.keys(specs).length ? specs : null,
        photo_urls: [],
      };

      const createRes = await providerMachineApi.create(payload);
      const machineId = createRes.data.id;

      // 2. Upload photos if any
      let photoUrls = [];
      try {
        if (photoFiles.length > 0) {
          const uploadRes = await uploadMachinePhotos(machineId, photoFiles);
          photoUrls = uploadRes.data.urls;
          await providerMachineApi.update(machineId, { photo_urls: photoUrls });
        }
      } catch (error) {
        await providerMachineApi.remove(machineId).catch(() => {});
        throw error;
      }

      return { machineId, photoUrls };
    },
    onSuccess: () => {
      toast.success(t("provider.form_success_add"));
      onSuccess();
    },
    onError: (err) => {
      const msg =
        err?.response?.data?.detail || t("provider.form_error_generic");
      toast.error(msg);
    },
  });

  const canSubmit =
    machineTypeId && ratePerAcre && availableFrom && availableTo && lat && lng;

  return (
    <motion.div
      initial={{ x: "100%" }}
      animate={{ x: 0 }}
      exit={{ x: "100%" }}
      transition={{ type: "spring", damping: 28, stiffness: 300 }}
      className="fixed inset-0 z-50 bg-slate-50 dark:bg-slate-950 overflow-y-auto"
    >
      {/* Sticky header */}
      <div className="sticky top-0 z-10 bg-white dark:bg-slate-900 border-b border-slate-100 dark:border-slate-800 px-5 py-4 flex items-center justify-between shadow-sm">
        <h2 className="text-lg font-black text-slate-800 dark:text-slate-100">
          {t("provider.add_machine")}
        </h2>
        <button
          onClick={onClose}
          className="rounded-full p-2 hover:bg-slate-100 dark:hover:bg-slate-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      <div className="p-5 space-y-6 max-w-lg mx-auto pb-32">
        {/* Machine Type */}
        <div>
          <label className={LABEL}>
            {t("provider.machine_type_label")}{" "}
            <span className="text-rose-500">*</span>
          </label>
          <div className="relative">
            <select
              id="machine-type-select"
              value={machineTypeId}
              onChange={(e) => setMachineTypeId(e.target.value)}
              className={`${FIELD} appearance-none`}
            >
              <option value="">{t("provider.machine_type_placeholder")}</option>
              {machineTypes.map((mt) => (
                <option key={mt.id} value={mt.id}>
                  {mt.name}
                </option>
              ))}
              {/* fallback hardcoded list if API unavailable */}
              {!machineTypes.length &&
                [
                  { id: 1, name: "Tractor" },
                  { id: 2, name: "Harvester" },
                  { id: 3, name: "Sprayer" },
                  { id: 4, name: "Rotavator" },
                  { id: 5, name: "Seed Drill" },
                  { id: 6, name: "Thresher" },
                ].map((mt) => (
                  <option key={mt.id} value={mt.id}>
                    {mt.name}
                  </option>
                ))}
            </select>
          </div>
        </div>

        {/* Rate + Mobilization */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={LABEL}>
              <Zap className="inline w-3.5 h-3.5 mr-1" />
              {t("provider.rate_per_acre")} *
            </label>
            <input
              id="rate-per-acre-input"
              type="number"
              min="1"
              value={ratePerAcre}
              onChange={(e) => setRatePerAcre(e.target.value)}
              className={FIELD}
              placeholder="₹300"
            />
          </div>
          <div>
            <label className={LABEL}>{t("provider.mobilization_cost")}</label>
            <input
              id="mobilization-cost-input"
              type="number"
              min="0"
              value={mobilizationCost}
              onChange={(e) => setMobilizationCost(e.target.value)}
              className={FIELD}
              placeholder="₹0"
            />
          </div>
        </div>

        {/* Date range */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={LABEL}>
              <Calendar className="inline w-3.5 h-3.5 mr-1" />
              {t("provider.available_from")} *
            </label>
            <input
              id="available-from-input"
              type="date"
              value={availableFrom}
              onChange={(e) => setAvailableFrom(e.target.value)}
              className={FIELD}
            />
          </div>
          <div>
            <label className={LABEL}>{t("provider.available_to")} *</label>
            <input
              id="available-to-input"
              type="date"
              value={availableTo}
              onChange={(e) => setAvailableTo(e.target.value)}
              className={FIELD}
            />
          </div>
        </div>

        {/* Location */}
        <div>
          <label className={LABEL}>
            <MapPin className="inline w-3.5 h-3.5 mr-1" />
            {t("provider.location_label")} *
          </label>
          <button
            type="button"
            id="use-gps-btn"
            onClick={useGps}
            disabled={gpsLoading}
            className="mb-2 flex items-center gap-2 rounded-xl border border-agri-green-300 text-agri-green-700 dark:text-agri-green-400 px-3 py-2 text-xs font-bold hover:bg-agri-green-50 dark:hover:bg-agri-green-900/20 transition-colors disabled:opacity-50"
          >
            {gpsLoading ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <MapPin className="w-3.5 h-3.5" />
            )}
            {t("provider.location_hint")}
          </button>
          <div className="grid grid-cols-2 gap-3">
            <input
              id="lat-input"
              type="number"
              step="0.000001"
              placeholder="Latitude"
              value={lat}
              onChange={(e) => setLat(e.target.value)}
              className={FIELD}
            />
            <input
              id="lng-input"
              type="number"
              step="0.000001"
              placeholder="Longitude"
              value={lng}
              onChange={(e) => setLng(e.target.value)}
              className={FIELD}
            />
          </div>
        </div>

        {/* Description */}
        <div>
          <label className={LABEL}>{t("provider.description_label")}</label>
          <textarea
            id="description-input"
            rows={3}
            value={description}
            onChange={(e) => setDescription(e.target.value)}
            placeholder={t("provider.description_placeholder")}
            className={`${FIELD} resize-none`}
          />
        </div>

        {/* Model year + Horsepower */}
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className={LABEL}>{t("provider.model_year_label")}</label>
            <input
              id="model-year-input"
              type="number"
              min="1950"
              max="2100"
              placeholder="2021"
              value={modelYear}
              onChange={(e) => setModelYear(e.target.value)}
              className={FIELD}
            />
          </div>
          <div>
            <label className={LABEL}>{t("provider.horsepower_label")}</label>
            <input
              id="horsepower-input"
              type="number"
              min="1"
              placeholder="45 HP"
              value={horsepower}
              onChange={(e) => setHorsepower(e.target.value)}
              className={FIELD}
            />
          </div>
        </div>

        {/* Attachments */}
        <div>
          <label className={LABEL}>{t("provider.attachments_label")}</label>
          <div className="flex flex-wrap gap-2">
            {ATTACHMENTS.map((a) => (
              <button
                key={a}
                type="button"
                id={`attachment-${a}-btn`}
                onClick={() =>
                  setAttachments((prev) =>
                    prev.includes(a)
                      ? prev.filter((x) => x !== a)
                      : [...prev, a],
                  )
                }
                className={`rounded-xl px-3 py-1.5 text-xs font-bold border-2 transition-colors ${
                  attachments.includes(a)
                    ? "border-agri-green-600 bg-agri-green-50 dark:bg-agri-green-900/30 text-agri-green-700 dark:text-agri-green-300"
                    : "border-slate-200 dark:border-slate-700 text-slate-600 dark:text-slate-400"
                }`}
              >
                {t(`provider.attachment_${a}`)}
              </button>
            ))}
          </div>
        </div>

        {/* Photo upload */}
        <div>
          <label className={LABEL}>{t("provider.photos_label")}</label>

          {/* Drag-drop zone */}
          <div
            id="photo-drop-zone"
            onDrop={onDrop}
            onDragOver={(e) => e.preventDefault()}
            onClick={() =>
              photoFiles.length < 5 && fileInputRef.current?.click()
            }
            className={`border-2 border-dashed rounded-2xl p-6 text-center cursor-pointer transition-colors ${
              photoFiles.length >= 5
                ? "border-slate-200 dark:border-slate-700 opacity-50 cursor-not-allowed"
                : "border-agri-green-300 dark:border-agri-green-700 hover:bg-agri-green-50 dark:hover:bg-agri-green-900/10"
            }`}
          >
            <ImagePlus className="w-8 h-8 mx-auto text-agri-green-500 mb-2" />
            <p className="text-sm text-slate-500 dark:text-slate-400">
              {t("provider.photos_drag")}
            </p>
            <p className="text-xs text-slate-400 mt-1">
              {photoFiles.length}/5 photos
            </p>
          </div>
          <input
            ref={fileInputRef}
            type="file"
            accept="image/jpeg,image/png"
            multiple
            className="hidden"
            onChange={(e) => handlePhotoChange(e.target.files)}
          />

          {uploadError && (
            <p className="mt-2 text-xs text-rose-500 font-semibold">
              {uploadError}
            </p>
          )}

          {/* Thumbnails */}
          {photoPreviews.length > 0 && (
            <div className="mt-3 flex flex-wrap gap-2">
              {photoPreviews.map((src, i) => (
                <div
                  key={i}
                  className="relative w-20 h-20 rounded-xl overflow-hidden border-2 border-slate-100 dark:border-slate-700"
                >
                  <img
                    src={src}
                    alt=""
                    className="w-full h-full object-cover"
                  />
                  <button
                    type="button"
                    onClick={() => removePhoto(i)}
                    className="absolute top-0.5 right-0.5 bg-black/60 rounded-full p-0.5"
                  >
                    <XCircle className="w-3.5 h-3.5 text-white" />
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Submit */}
        <button
          id="submit-add-machine-btn"
          onClick={() => mutation.mutate()}
          disabled={!canSubmit || mutation.isPending}
          className="w-full py-4 rounded-2xl bg-agri-green-700 text-white font-black text-base shadow-lg shadow-agri-green-700/30 flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          {mutation.isPending && <Loader2 className="w-5 h-5 animate-spin" />}
          {t("provider.submit_add")}
        </button>
      </div>
    </motion.div>
  );
}
