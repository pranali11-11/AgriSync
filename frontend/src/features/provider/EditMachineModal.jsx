import React, { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { Loader2, X, XCircle } from "lucide-react";
import toast from "react-hot-toast";
import { providerMachineApi, uploadMachinePhotos } from "../../services/api";

const FIELD =
  "block w-full rounded-lg border border-slate-300 bg-white px-3 py-2.5 text-sm text-slate-800 focus:border-emerald-600 focus:outline-none";

export default function EditMachineModal({ machine, onClose, onSuccess }) {
  const { t } = useTranslation();
  const fileInputRef = useRef(null);
  const [rate, setRate] = useState(String(machine.rate_per_acre));
  const [mobilizationCost, setMobilizationCost] = useState(
    String(machine.mobilization_cost ?? 0),
  );
  const [availableFrom, setAvailableFrom] = useState(
    machine.available_from || "",
  );
  const [availableTo, setAvailableTo] = useState(machine.available_to || "");
  const [description, setDescription] = useState(machine.description || "");
  const [modelYear, setModelYear] = useState(
    machine.model_year ? String(machine.model_year) : "",
  );
  const [horsepower, setHorsepower] = useState(
    machine.specifications?.horsepower
      ? String(machine.specifications.horsepower)
      : "",
  );
  const [attachments, setAttachments] = useState(
    machine.specifications?.attachments || [],
  );
  const [photos, setPhotos] = useState(machine.photos || []);
  const [newFiles, setNewFiles] = useState([]);
  const [newPhotoPreviews, setNewPhotoPreviews] = useState([]);

  useEffect(() => {
    const previews = newFiles.map((file) => URL.createObjectURL(file));
    setNewPhotoPreviews(previews);
    return () => previews.forEach((preview) => URL.revokeObjectURL(preview));
  }, [newFiles]);

  const mutation = useMutation({
    mutationFn: async () => {
      let newPhotoUrls = [];
      if (newFiles.length) {
        const response = await uploadMachinePhotos(machine.id, newFiles);
        newPhotoUrls = response.data.urls;
      }
      const specifications = {};
      if (horsepower) specifications.horsepower = Number(horsepower);
      if (attachments.length) specifications.attachments = attachments;
      return providerMachineApi.update(machine.id, {
        rate_per_acre: Number(rate),
        mobilization_cost: Number(mobilizationCost) || 0,
        available_from: availableFrom,
        available_to: availableTo,
        description,
        model_year: modelYear ? Number(modelYear) : null,
        specifications,
        photo_urls: [...photos, ...newPhotoUrls],
      });
    },
    onSuccess: () => {
      toast.success(t("provider.form_success_edit"));
      onSuccess();
    },
    onError: (error) =>
      toast.error(
        error.response?.data?.detail || t("provider.form_error_generic"),
      ),
  });

  const choosePhotos = (event) => {
    const files = Array.from(event.target.files || []);
    if (photos.length + newFiles.length + files.length > 5) {
      toast.error(t("provider.upload_error_count"));
      return;
    }
    if (
      files.some(
        (file) =>
          !["image/jpeg", "image/png"].includes(file.type) ||
          file.size > 5 * 1024 * 1024,
      )
    ) {
      toast.error(t("provider.upload_error_invalid"));
      return;
    }
    setNewFiles((current) => [...current, ...files]);
  };

  const attachmentsList = [
    "rotavator",
    "plough",
    "seeder",
    "sprayer",
    "trailer",
    "harrow",
  ];

  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center overflow-y-auto bg-black/50 p-4">
      <div className="my-auto max-h-[90vh] w-full max-w-lg overflow-y-auto rounded-xl bg-white p-5 shadow-2xl">
        <header className="mb-5 flex items-center justify-between">
          <h2 className="text-lg font-bold text-slate-900">
            {t("provider.edit_btn")} ·{" "}
            {machine.machine_type?.name || `#${machine.id}`}
          </h2>
          <button
            type="button"
            onClick={onClose}
            aria-label={t("provider.cancel")}
            className="rounded-md p-2 hover:bg-slate-100"
          >
            <X className="h-5 w-5" />
          </button>
        </header>
        <form
          onSubmit={(event) => {
            event.preventDefault();
            mutation.mutate();
          }}
          className="space-y-4"
        >
          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm font-semibold">
              {t("provider.rate_per_acre")}
              <input
                required
                min="1"
                type="number"
                value={rate}
                onChange={(event) => setRate(event.target.value)}
                className={`${FIELD} mt-1`}
              />
            </label>
            <label className="text-sm font-semibold">
              {t("provider.mobilization_cost")}
              <input
                min="0"
                type="number"
                value={mobilizationCost}
                onChange={(event) => setMobilizationCost(event.target.value)}
                className={`${FIELD} mt-1`}
              />
            </label>
            <label className="text-sm font-semibold">
              {t("provider.available_from")}
              <input
                required
                type="date"
                value={availableFrom}
                onChange={(event) => setAvailableFrom(event.target.value)}
                className={`${FIELD} mt-1`}
              />
            </label>
            <label className="text-sm font-semibold">
              {t("provider.available_to")}
              <input
                required
                type="date"
                value={availableTo}
                onChange={(event) => setAvailableTo(event.target.value)}
                className={`${FIELD} mt-1`}
              />
            </label>
          </div>
          <label className="block text-sm font-semibold">
            {t("provider.description_label")}
            <textarea
              rows="3"
              value={description}
              onChange={(event) => setDescription(event.target.value)}
              className={`${FIELD} mt-1`}
            />
          </label>
          <div className="grid grid-cols-2 gap-3">
            <label className="text-sm font-semibold">
              {t("provider.model_year_label")}
              <input
                min="1950"
                max="2100"
                type="number"
                value={modelYear}
                onChange={(event) => setModelYear(event.target.value)}
                className={`${FIELD} mt-1`}
              />
            </label>
            <label className="text-sm font-semibold">
              {t("provider.horsepower_label")}
              <input
                min="1"
                type="number"
                value={horsepower}
                onChange={(event) => setHorsepower(event.target.value)}
                className={`${FIELD} mt-1`}
              />
            </label>
          </div>
          <fieldset>
            <legend className="mb-2 text-sm font-semibold">
              {t("provider.attachments_label")}
            </legend>
            <div className="flex flex-wrap gap-2">
              {attachmentsList.map((attachment) => (
                <label
                  key={attachment}
                  className="flex items-center gap-1 rounded-md border px-2 py-1 text-xs"
                >
                  <input
                    type="checkbox"
                    checked={attachments.includes(attachment)}
                    onChange={() =>
                      setAttachments((current) =>
                        current.includes(attachment)
                          ? current.filter((value) => value !== attachment)
                          : [...current, attachment],
                      )
                    }
                  />
                  {t(`provider.attachment_${attachment}`)}
                </label>
              ))}
            </div>
          </fieldset>
          <div>
            <p className="mb-2 text-sm font-semibold">
              {t("provider.photos_label")}
            </p>
            <div className="flex flex-wrap gap-2">
              {photos.map((url) => (
                <div
                  key={url}
                  className="relative h-16 w-16 overflow-hidden rounded-md"
                >
                  <img
                    src={url}
                    alt=""
                    className="h-full w-full object-cover"
                  />
                  <button
                    type="button"
                    onClick={() =>
                      setPhotos((current) =>
                        current.filter((photo) => photo !== url),
                      )
                    }
                    className="absolute right-0.5 top-0.5 rounded-full bg-black/60 p-0.5"
                    aria-label={t("provider.photos_remove")}
                  >
                    <XCircle className="h-4 w-4 text-white" />
                  </button>
                </div>
              ))}
              {newFiles.map((file, index) => (
                <div
                  key={`${file.name}-${index}`}
                  className="relative h-16 w-16 overflow-hidden rounded-md"
                >
                  <img
                    src={newPhotoPreviews[index]}
                    alt=""
                    className="h-full w-full object-cover"
                  />
                  <button
                    type="button"
                    onClick={() =>
                      setNewFiles((current) =>
                        current.filter((_, photoIndex) => photoIndex !== index),
                      )
                    }
                    className="absolute right-0.5 top-0.5 rounded-full bg-black/60 p-0.5"
                    aria-label={t("provider.photos_remove")}
                  >
                    <XCircle className="h-4 w-4 text-white" />
                  </button>
                </div>
              ))}
            </div>
            <input
              ref={fileInputRef}
              type="file"
              accept="image/jpeg,image/png"
              multiple
              onChange={choosePhotos}
              className="mt-2 block w-full text-sm"
            />
          </div>
          <footer className="flex justify-end gap-2 border-t pt-4">
            <button
              type="button"
              onClick={onClose}
              className="rounded-md border px-4 py-2 text-sm font-semibold"
            >
              {t("provider.cancel")}
            </button>
            <button
              type="submit"
              disabled={mutation.isPending}
              className="flex items-center gap-2 rounded-md bg-emerald-700 px-4 py-2 text-sm font-bold text-white disabled:opacity-50"
            >
              {mutation.isPending && (
                <Loader2 className="h-4 w-4 animate-spin" />
              )}
              {t("provider.submit_edit")}
            </button>
          </footer>
        </form>
      </div>
    </div>
  );
}
