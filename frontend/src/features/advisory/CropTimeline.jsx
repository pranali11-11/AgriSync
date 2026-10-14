import React, { useState, useRef, useEffect, useMemo } from "react";
import PropTypes from "prop-types";
import { motion, AnimatePresence } from "framer-motion";
import {
  Calendar,
  Clock,
  Info,
  ChevronLeft,
  ChevronRight,
  X,
  CheckCircle2,
  Sparkles,
  ShieldCheck,
  Wrench,
} from "lucide-react";

export function CropTimeline({
  timeline = [],
  currentDay = 0,
  previewDay = null,
  onSelectDay = () => {},
  cropName = "",
  onOpenMachineryPlan,
}) {
  const containerRef = useRef(null);
  const [hoveredIndex, setHoveredIndex] = useState(null);
  const [bottomSheetOpen, setBottomSheetOpen] = useState(false);
  const [inspectedIndex, setInspectedIndex] = useState(null);

  const totalDuration = useMemo(() => {
    if (!timeline.length) return 120;
    return timeline[timeline.length - 1].end_day || 120;
  }, [timeline]);

  // Current active stage index based on currentDay
  const currentIndex = useMemo(() => {
    if (!timeline.length) return 0;
    const idx = timeline.findIndex((st, i) =>
      i === timeline.length - 1
        ? currentDay >= st.start_day && currentDay <= st.end_day
        : currentDay >= st.start_day && currentDay < st.end_day,
    );
    return idx >= 0 ? idx : currentDay >= totalDuration ? timeline.length - 1 : 0;
  }, [timeline, currentDay, totalDuration]);

  // Previewed stage index based on previewDay
  const previewIndex = useMemo(() => {
    if (previewDay === null || !timeline.length) return null;
    const idx = timeline.findIndex((st, i) =>
      i === timeline.length - 1
        ? previewDay >= st.start_day && previewDay <= st.end_day
        : previewDay >= st.start_day && previewDay < st.end_day,
    );
    return idx >= 0 ? idx : previewDay >= totalDuration ? timeline.length - 1 : 0;
  }, [timeline, previewDay, totalDuration]);

  // Initialize inspected stage to current stage
  useEffect(() => {
    if (inspectedIndex === null && currentIndex !== null) {
      setInspectedIndex(currentIndex);
    }
  }, [currentIndex, inspectedIndex]);

  const activeDisplayDay = previewDay !== null ? previewDay : currentDay;
  const activeStage = timeline[inspectedIndex ?? currentIndex] || timeline[0];

  const handleSelectStage = (index) => {
    setInspectedIndex(index);
    setBottomSheetOpen(true);
    const targetStage = timeline[index];
    if (targetStage) {
      // Pick a representative day in that stage
      const midDay = Math.min(
        targetStage.end_day,
        Math.max(targetStage.start_day, Math.round((targetStage.start_day + targetStage.end_day) / 2)),
      );
      onSelectDay(midDay);
    }
  };

  const handleDrag = (_event, info) => {
    if (!containerRef.current) return;
    const rect = containerRef.current.getBoundingClientRect();
    const relativeX = Math.max(0, Math.min(rect.width, info.point.x - rect.left));
    const calculatedDay = Math.round((relativeX / rect.width) * totalDuration);
    onSelectDay(calculatedDay);

    // Find which stage this belongs to and set as inspected
    const idx = timeline.findIndex((st, i) =>
      i === timeline.length - 1
        ? calculatedDay >= st.start_day && calculatedDay <= st.end_day
        : calculatedDay >= st.start_day && calculatedDay < st.end_day,
    );
    if (idx >= 0) {
      setInspectedIndex(idx);
      setBottomSheetOpen(true);
    }
  };

  const scrubberPercent = Math.min(
    100,
    Math.max(0, (activeDisplayDay / totalDuration) * 100),
  );

  if (!timeline.length) {
    return null;
  }

  return (
    <section className="relative rounded-3xl bg-white p-5 shadow-sm md:p-6" id="crop-timeline-section">
      {/* Header */}
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-xl font-black text-slate-900">Crop Lifecycle Timeline</h2>
            {cropName && (
              <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-bold text-emerald-800">
                {cropName}
              </span>
            )}
          </div>
          <p className="mt-0.5 text-sm text-slate-500">
            {timeline.length} distinct ICAR growth stages · Day {activeDisplayDay} of {totalDuration} days
            {previewDay !== null && (
              <span className="ml-2 inline-flex items-center font-bold text-amber-600">
                (Preview Mode)
              </span>
            )}
          </p>
        </div>

        <div className="flex items-center gap-2">
          {previewDay !== null && (
            <button
              onClick={() => onSelectDay(null)}
              className="rounded-xl border border-slate-300 bg-slate-50 px-3 py-1.5 text-xs font-bold text-slate-700 transition hover:bg-slate-100"
            >
              Reset to Today
            </button>
          )}
          <button
            onClick={() => setBottomSheetOpen(true)}
            className="inline-flex items-center gap-1.5 rounded-xl bg-emerald-50 px-3 py-1.5 text-xs font-bold text-emerald-800 transition hover:bg-emerald-100"
            id="view-stage-guide-btn"
          >
            <Info className="h-3.5 w-3.5" />
            Stage Details
          </button>
        </div>
      </div>

      {/* Interactive Proportional Timeline Bar */}
      <div className="relative mt-8 select-none">
        {/* Track container */}
        <div
          ref={containerRef}
          className="relative flex h-14 sm:h-16 w-full overflow-hidden rounded-2xl bg-slate-100 p-1 shadow-inner border border-slate-200/90"
        >
          {timeline.map((stage, idx) => {
            const length = Math.max(1, stage.end_day - stage.start_day);
            const widthPct = (length / totalDuration) * 100;
            const isCurrent = idx === currentIndex;
            const isPreview = idx === previewIndex;
            const isPast = activeDisplayDay >= stage.end_day;
            const isInspected = idx === inspectedIndex;

            // Background & text styles based on status
            let segmentBg = "bg-slate-200/80 text-slate-600 hover:bg-slate-300/80";
            if (isCurrent) {
              segmentBg =
                "bg-emerald-600 text-white shadow-md ring-2 ring-emerald-400 ring-offset-1 ring-offset-white z-10";
            } else if (isPast) {
              segmentBg = "bg-emerald-200/90 text-emerald-900 hover:bg-emerald-300/90";
            } else if (isPreview) {
              segmentBg = "bg-amber-500 text-white shadow ring-2 ring-amber-300 z-10";
            }

            return (
              <div
                key={stage.stage || idx}
                id={`timeline-stage-segment-${idx}`}
                data-testid={`stage-segment-${idx}`}
                onClick={() => handleSelectStage(idx)}
                onMouseEnter={() => setHoveredIndex(idx)}
                onMouseLeave={() => setHoveredIndex(null)}
                style={{ width: `${widthPct}%` }}
                className={`group relative flex h-full cursor-pointer flex-col justify-center px-1 text-center transition-all duration-150 ${segmentBg} ${
                  idx !== timeline.length - 1 ? "border-r border-white/70" : ""
                } ${isInspected ? "outline outline-2 outline-amber-500" : ""}`}
                role="button"
                tabIndex={0}
                aria-label={`${stage.stage}: Day ${stage.start_day} to ${stage.end_day}. Click for details.`}
              >
                {/* Stage name inside segment if wide enough */}
                <div className="truncate text-[11px] font-bold leading-tight sm:text-xs">
                  {stage.stage}
                </div>
                <div className="mt-0.5 text-[9px] font-medium opacity-80 sm:text-[10px]">
                  {length}d · d{stage.start_day}–{stage.end_day}
                </div>

                {/* Current Stage Indicator Badge */}
                {isCurrent && (
                  <span className="absolute -top-3 left-1/2 -translate-x-1/2 rounded-full bg-emerald-700 px-2 py-0.5 text-[9px] font-black uppercase tracking-wider text-white shadow ring-2 ring-white">
                    Current
                  </span>
                )}
              </div>
            );
          })}
        </div>

        {/* Floating Tooltip on Hover */}
        <AnimatePresence>
          {hoveredIndex !== null && timeline[hoveredIndex] && (
            <motion.div
              initial={{ opacity: 0, y: 8, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 8, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="pointer-events-none absolute -top-24 left-1/2 z-30 w-72 -translate-x-1/2 rounded-2xl border border-slate-700 bg-slate-900/95 p-3 text-white shadow-xl backdrop-blur-md"
            >
              <div className="flex items-center justify-between text-xs font-bold text-emerald-400">
                <span>{timeline[hoveredIndex].stage}</span>
                <span>
                  Day {timeline[hoveredIndex].start_day} – {timeline[hoveredIndex].end_day} (
                  {timeline[hoveredIndex].end_day - timeline[hoveredIndex].start_day} days)
                </span>
              </div>
              <p className="mt-1 line-clamp-2 text-xs leading-relaxed text-slate-300">
                {timeline[hoveredIndex].stage_description || "Tap to read full stage advisory."}
              </p>
              <div className="mt-1 text-[10px] text-slate-400">
                Tap segment to inspect full details & advice
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Draggable Scrubber Pin */}
        <div
          className="pointer-events-none absolute inset-x-0 top-0 h-14 sm:h-16"
        >
          <motion.div
            drag="x"
            dragConstraints={containerRef}
            dragElastic={0}
            onDrag={handleDrag}
            onDragEnd={handleDrag}
            style={{ left: `${scrubberPercent}%` }}
            className="pointer-events-auto absolute top-0 -translate-x-1/2 -translate-y-2 cursor-grab active:cursor-grabbing"
            aria-label="Drag timeline scrubber across crop stages"
          >
            <div className="flex flex-col items-center">
              <div className="flex items-center gap-1 rounded-full border-2 border-white bg-slate-900 px-2 py-0.5 text-[10px] font-black text-white shadow-lg">
                <Clock className="h-3 w-3 text-emerald-400" />
                <span>Day {activeDisplayDay}</span>
              </div>
              <div className="h-6 w-1 rounded-full bg-slate-900 shadow" />
              <div className="h-3 w-3 rounded-full border-2 border-white bg-emerald-500 shadow-md" />
            </div>
          </motion.div>
        </div>

        {/* Legend / Range labels */}
        <div className="mt-4 flex items-center justify-between text-xs font-bold text-slate-500">
          <div className="flex items-center gap-1.5">
            <Calendar className="h-3.5 w-3.5 text-slate-400" />
            <span>Sowing (Day 0)</span>
          </div>
          <span className="text-[11px] font-normal text-slate-400">
            Tip: Tap any stage or drag the pin to preview advice
          </span>
          <div className="flex items-center gap-1.5">
            <CheckCircle2 className="h-3.5 w-3.5 text-emerald-600" />
            <span>Harvest ({totalDuration}d)</span>
          </div>
        </div>
      </div>

      {/* Stage Detail Highlight Card (Always accessible directly under timeline) */}
      {activeStage && (
        <div
          id="stage-details-highlight-card"
          className="mt-6 rounded-2xl border border-emerald-100 bg-gradient-to-br from-emerald-50/70 via-white to-emerald-50/30 p-4 transition-all"
        >
          <div className="flex flex-wrap items-center justify-between gap-2 border-b border-emerald-100/80 pb-3">
            <div className="flex items-center gap-2">
              <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-emerald-600 text-white shadow-sm">
                <Sparkles className="h-5 w-5" />
              </div>
              <div>
                <h3 className="text-base font-black text-slate-900 sm:text-lg" id="inspected-stage-title">
                  {activeStage.stage}
                </h3>
                <p className="text-xs font-bold text-emerald-800">
                  Days {activeStage.start_day} – {activeStage.end_day} ({activeStage.end_day - activeStage.start_day} days)
                </p>
              </div>
            </div>

            <div className="flex items-center gap-2">
              {inspectedIndex === currentIndex ? (
                <span className="rounded-full bg-emerald-700 px-3 py-1 text-xs font-bold text-white shadow-sm">
                  🌱 Current Active Stage
                </span>
              ) : inspectedIndex < currentIndex ? (
                <span className="rounded-full bg-slate-200 px-3 py-1 text-xs font-bold text-slate-700">
                  ✓ Completed Stage
                </span>
              ) : (
                <span className="rounded-full bg-sky-100 px-3 py-1 text-xs font-bold text-sky-800">
                  ⏳ Upcoming in {Math.max(0, activeStage.start_day - currentDay)} days
                </span>
              )}

              {onOpenMachineryPlan && (
                <button
                  onClick={() => onOpenMachineryPlan(activeStage.stage)}
                  className="inline-flex items-center gap-1 rounded-xl border border-emerald-300 bg-white px-2.5 py-1 text-xs font-bold text-emerald-800 shadow-sm hover:bg-emerald-50"
                >
                  <Wrench className="h-3 w-3" />
                  Machinery
                </button>
              )}
            </div>
          </div>

          <div className="mt-3 space-y-2">
            <h4 className="text-xs font-bold uppercase tracking-wider text-slate-500">
              Agronomic Insights & What To Watch For
            </h4>
            <p className="text-sm leading-relaxed text-slate-700" id="inspected-stage-description">
              {activeStage.stage_description ||
                "Watch crop development closely during this phase and ensure adequate nutrient and water management."}
            </p>
            <div className="flex items-center gap-1 text-[11px] font-semibold text-slate-400">
              <ShieldCheck className="h-3.5 w-3.5 text-emerald-600" />
              <span>Source: {activeStage.source || "SAMPLE - verify with ICAR / state agriculture dept"}</span>
            </div>
          </div>
        </div>
      )}

      {/* Interactive Bottom Sheet / Drawer Modal */}
      <AnimatePresence>
        {bottomSheetOpen && activeStage && (
          <>
            {/* Backdrop */}
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setBottomSheetOpen(false)}
              className="fixed inset-0 z-40 bg-slate-900/60 backdrop-blur-sm"
            />

            {/* Bottom Sheet Drawer */}
            <motion.div
              initial={{ y: "100%" }}
              animate={{ y: 0 }}
              exit={{ y: "100%" }}
              transition={{ type: "spring", damping: 25, stiffness: 300 }}
              className="fixed inset-x-0 bottom-0 z-50 mx-auto max-w-2xl rounded-t-3xl border-t border-slate-200 bg-white p-6 shadow-2xl"
              id="stage-bottom-sheet"
              role="dialog"
              aria-modal="true"
              aria-labelledby="bottom-sheet-stage-title"
            >
              <div className="mx-auto mb-4 h-1.5 w-12 rounded-full bg-slate-300" />

              <div className="flex items-start justify-between">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="rounded-full bg-emerald-100 px-2.5 py-0.5 text-xs font-bold text-emerald-800">
                      Stage {(inspectedIndex ?? 0) + 1} of {timeline.length}
                    </span>
                    {inspectedIndex === currentIndex && (
                      <span className="rounded-full bg-emerald-700 px-2.5 py-0.5 text-xs font-bold text-white">
                        Current Stage
                      </span>
                    )}
                  </div>
                  <h3
                    id="bottom-sheet-stage-title"
                    className="mt-1 text-2xl font-black text-slate-900"
                  >
                    {activeStage.stage}
                  </h3>
                  <p className="mt-0.5 text-sm font-bold text-slate-500">
                    Day {activeStage.start_day} to Day {activeStage.end_day} (Duration:{" "}
                    {activeStage.end_day - activeStage.start_day} days)
                  </p>
                </div>

                <button
                  onClick={() => setBottomSheetOpen(false)}
                  className="rounded-full p-2 text-slate-400 hover:bg-slate-100 hover:text-slate-600"
                  aria-label="Close bottom sheet"
                  id="close-bottom-sheet-btn"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>

              <div className="mt-5 space-y-4">
                <div className="rounded-2xl bg-emerald-50/70 p-4 border border-emerald-100">
                  <h4 className="text-xs font-black uppercase tracking-wider text-emerald-900">
                    Agronomic Observation & Care
                  </h4>
                  <p className="mt-1.5 text-sm leading-relaxed text-slate-800" id="bottom-sheet-stage-desc">
                    {activeStage.stage_description}
                  </p>
                </div>

                <div className="flex items-center justify-between text-xs text-slate-500">
                  <div className="flex items-center gap-1.5">
                    <ShieldCheck className="h-4 w-4 text-emerald-600" />
                    <span>Source: {activeStage.source || "SAMPLE - verify with ICAR / state agriculture dept"}</span>
                  </div>
                </div>

                {/* Navigation controls */}
                <div className="flex items-center justify-between gap-3 pt-2">
                  <button
                    disabled={(inspectedIndex ?? 0) <= 0}
                    onClick={() => handleSelectStage(Math.max(0, (inspectedIndex ?? 0) - 1))}
                    className="inline-flex items-center gap-1 rounded-xl border border-slate-200 px-3.5 py-2 text-xs font-bold text-slate-700 transition hover:bg-slate-50 disabled:opacity-40"
                    id="prev-stage-btn"
                  >
                    <ChevronLeft className="h-4 w-4" />
                    Previous Stage
                  </button>

                  <button
                    onClick={() => {
                      setBottomSheetOpen(false);
                      if (onOpenMachineryPlan) onOpenMachineryPlan(activeStage.stage);
                    }}
                    className="rounded-xl bg-emerald-700 px-4 py-2 text-xs font-bold text-white shadow transition hover:bg-emerald-800"
                  >
                    View Machinery for this Stage
                  </button>

                  <button
                    disabled={(inspectedIndex ?? 0) >= timeline.length - 1}
                    onClick={() => handleSelectStage(Math.min(timeline.length - 1, (inspectedIndex ?? 0) + 1))}
                    className="inline-flex items-center gap-1 rounded-xl border border-slate-200 px-3.5 py-2 text-xs font-bold text-slate-700 transition hover:bg-slate-50 disabled:opacity-40"
                    id="next-stage-btn"
                  >
                    Next Stage
                    <ChevronRight className="h-4 w-4" />
                  </button>
                </div>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </section>
  );
}

CropTimeline.propTypes = {
  timeline: PropTypes.arrayOf(
    PropTypes.shape({
      stage: PropTypes.string.isRequired,
      start_day: PropTypes.number.isRequired,
      end_day: PropTypes.number.isRequired,
      stage_description: PropTypes.string,
      source: PropTypes.string,
    }),
  ),
  currentDay: PropTypes.number,
  previewDay: PropTypes.number,
  onSelectDay: PropTypes.func,
  cropName: PropTypes.string,
  onOpenMachineryPlan: PropTypes.func,
};
