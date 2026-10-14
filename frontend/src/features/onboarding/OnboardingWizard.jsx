import React from "react";
import PropTypes from "prop-types";
import { AnimatePresence, motion } from "framer-motion";
import { useTranslation } from "react-i18next";
import { useOnboardingStore } from "../../store/useOnboardingStore";
import { Step0Login } from "./Step0Login";
import { Step1Language } from "./Step1Language";
import { Step2Crop } from "./Step2Crop";
import { Step3SowingDate } from "./Step3SowingDate";
import { Step4Area } from "./Step4Area";
import { Step5SoilInfo } from "./Step5SoilInfo";
import { Step6Location } from "./Step6Location";
import { Step7Summary } from "./Step7Summary";
import { ChevronLeft, Sprout } from "lucide-react";

const STEP_TITLES = [
  "auth.welcome_title",
  "language.select_title",
  "crop.select_title",
  "sowing.title",
  "area.title",
  "soil.title",
  "location.title",
  "summary.title",
];

const TOTAL_STEPS = 8; // Steps 0-7

const slideVariants = {
  enter: (dir) => ({ x: dir > 0 ? "100%" : "-100%", opacity: 0 }),
  center: { x: 0, opacity: 1 },
  exit: (dir) => ({ x: dir < 0 ? "100%" : "-100%", opacity: 0 }),
};

export const OnboardingWizard = ({ onComplete }) => {
  const { t } = useTranslation();
  const { step, userRole, nextStep, prevStep } = useOnboardingStore();
  const [direction, setDirection] = React.useState(1);

  const goNext = () => {
    setDirection(1);
    if (step === 0 && userRole === "provider") {
      onComplete();
      return;
    }
    nextStep();
  };

  const goBack = () => {
    setDirection(-1);
    prevStep();
  };

  const renderStep = () => {
    switch (step) {
      case 0:
        return <Step0Login onCompleted={goNext} />;
      case 1:
        return <Step1Language onNext={goNext} />;
      case 2:
        return <Step2Crop onNext={goNext} />;
      case 3:
        return <Step3SowingDate onNext={goNext} />;
      case 4:
        return <Step4Area onNext={goNext} />;
      case 5:
        return <Step5SoilInfo onNext={goNext} />;
      case 6:
        return <Step6Location onNext={goNext} />;
      case 7:
        return <Step7Summary onFinish={onComplete} />;
      default:
        return <Step0Login onCompleted={goNext} />;
    }
  };

  const progressPct = Math.round((step / (TOTAL_STEPS - 1)) * 100);

  return (
    <div className="min-h-screen bg-slate-50 dark:bg-slate-950 flex flex-col max-w-md mx-auto">
      {/* Top Bar */}
      <div className="sticky top-0 z-30 bg-white/95 dark:bg-slate-900/95 backdrop-blur-md border-b border-slate-100 dark:border-slate-800 px-4 py-3">
        <div className="flex items-center justify-between mb-2.5">
          {/* Back button — hidden on step 0 */}
          {step > 0 ? (
            <button
              onClick={goBack}
              className="p-2 rounded-xl bg-slate-100 dark:bg-slate-800 hover:bg-slate-200 dark:hover:bg-slate-700 touch-target min-h-[38px] min-w-[38px] transition-all"
              aria-label="Go back"
            >
              <ChevronLeft className="w-5 h-5 text-slate-600 dark:text-slate-300" />
            </button>
          ) : (
            <div className="flex items-center space-x-2">
              <div className="w-8 h-8 rounded-xl bg-agri-green-700 text-white flex items-center justify-center">
                <Sprout className="w-4 h-4" />
              </div>
              <span className="text-xs font-bold text-agri-green-900 dark:text-agri-green-200">
                AgriSync
              </span>
            </div>
          )}

          {/* Step indicator */}
          <span className="text-xs font-bold text-slate-500 dark:text-slate-400 tabular-nums">
            {step + 1} / {TOTAL_STEPS}
          </span>
        </div>

        {/* Progress Bar */}
        <div className="h-1.5 bg-slate-200 dark:bg-slate-800 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-gradient-to-r from-agri-green-600 to-agri-green-400 rounded-full"
            animate={{ width: `${progressPct}%` }}
            transition={{ duration: 0.4, ease: "easeOut" }}
          />
        </div>
      </div>

      {/* Step Content with Slide Transitions */}
      <div className="flex-1 overflow-hidden relative">
        <AnimatePresence custom={direction} mode="wait">
          <motion.div
            key={step}
            custom={direction}
            variants={slideVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ type: "spring", stiffness: 350, damping: 35 }}
            className="absolute inset-0 p-5 overflow-y-auto"
          >
            {renderStep()}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
};

OnboardingWizard.propTypes = {
  onComplete: PropTypes.func.isRequired,
};
