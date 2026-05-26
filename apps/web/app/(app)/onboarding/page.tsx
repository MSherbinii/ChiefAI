'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Rocket, GraduationCap, Briefcase, Code2, Palette, User,
  ArrowRight, Zap,
} from 'lucide-react';
import { Button } from '@/components/design-system';
import { StepIndicator } from '@/components/onboarding/StepIndicator';
import { RoleCard } from '@/components/onboarding/RoleCard';
import { FocusTagInput } from '@/components/onboarding/FocusTagInput';

const ROLES = [
  { label: 'Founder', icon: Rocket },
  { label: 'Student', icon: GraduationCap },
  { label: 'Freelancer', icon: Briefcase },
  { label: 'Engineer', icon: Code2 },
  { label: 'Creator', icon: Palette },
  { label: 'Other', icon: User },
];

const TIMEZONES = [
  'Europe/Berlin', 'Europe/London', 'Europe/Paris', 'America/New_York',
  'America/Los_Angeles', 'America/Chicago', 'Asia/Dubai', 'Asia/Karachi',
  'Asia/Kolkata', 'Asia/Singapore', 'Australia/Sydney', 'Pacific/Auckland',
];

function detectTimezone(): string {
  try {
    return Intl.DateTimeFormat().resolvedOptions().timeZone;
  } catch {
    return 'Europe/Berlin';
  }
}

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [submitting, setSubmitting] = useState(false);

  const [name, setName] = useState('');
  const [timezone, setTimezone] = useState(detectTimezone);
  const [roles, setRoles] = useState<string[]>([]);
  const [focuses, setFocuses] = useState<string[]>([]);

  function toggleRole(label: string) {
    setRoles(prev =>
      prev.includes(label) ? prev.filter(r => r !== label) : [...prev, label]
    );
  }

  async function handleComplete() {
    setSubmitting(true);
    const res = await fetch('/api/onboarding/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ display_name: name, timezone, roles, focuses }),
    });
    if (res.ok) {
      router.push('/today');
    } else {
      setSubmitting(false);
    }
  }

  const stepVariants = {
    enter: { opacity: 0, x: 24 },
    center: { opacity: 1, x: 0 },
    exit: { opacity: 0, x: -24 },
  };

  return (
    <div className="w-full max-w-md space-y-8">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-full bg-[linear-gradient(135deg,#2633D9,#8A3AFF)] flex items-center justify-center">
            <Zap size={13} className="text-white" />
          </div>
          <span className="text-sm font-bold tracking-[0.12em] text-[var(--v2-text)] uppercase">Chief</span>
        </div>
        <StepIndicator total={3} current={step} />
      </div>

      <AnimatePresence mode="wait">
        {step === 0 && (
          <motion.div
            key="step0"
            variants={stepVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.22 }}
            className="space-y-7"
          >
            <div className="space-y-1.5">
              <h1 className="text-2xl font-bold text-[var(--v2-text)]">What should Chief call you?</h1>
              <p className="text-[var(--v2-muted)] text-sm">Used in your Morning Brief and responses.</p>
            </div>
            <div className="space-y-4">
              <div className="space-y-1.5">
                <label className="text-[12px] font-medium text-[var(--v2-muted)] uppercase tracking-[0.08em]">
                  Your name
                </label>
                <input
                  type="text"
                  placeholder="Mohamed"
                  value={name}
                  onChange={e => setName(e.target.value)}
                  autoFocus
                  className="w-full h-11 px-3.5 rounded-[10px] bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] text-[var(--v2-text)] placeholder:text-[var(--v2-subtle)] text-sm focus:outline-none focus:border-[var(--v2-border-focus)] transition-colors"
                />
              </div>
              <div className="space-y-1.5">
                <label className="text-[12px] font-medium text-[var(--v2-muted)] uppercase tracking-[0.08em]">
                  Timezone
                </label>
                <select
                  value={timezone}
                  onChange={e => setTimezone(e.target.value)}
                  className="w-full h-11 px-3.5 rounded-[10px] bg-[rgba(247,240,255,0.04)] border border-[rgba(247,240,255,0.12)] text-[var(--v2-text)] text-sm focus:outline-none focus:border-[var(--v2-border-focus)] transition-colors appearance-none cursor-pointer"
                >
                  {TIMEZONES.map(tz => (
                    <option key={tz} value={tz} className="bg-[#0C1017] text-[var(--v2-text)]">
                      {tz.replace(/_/g, ' ')}
                    </option>
                  ))}
                </select>
              </div>
            </div>
            <Button
              variant="solid" size="lg" className="w-full"
              disabled={!name.trim()}
              onClick={() => setStep(1)}
              iconRight={<ArrowRight size={15} />}
            >
              Continue
            </Button>
          </motion.div>
        )}

        {step === 1 && (
          <motion.div
            key="step1"
            variants={stepVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.22 }}
            className="space-y-7"
          >
            <div className="space-y-1.5">
              <h1 className="text-2xl font-bold text-[var(--v2-text)]">What best describes you?</h1>
              <p className="text-[var(--v2-muted)] text-sm">Chief personalizes your brief and suggestions. Pick all that apply.</p>
            </div>
            <div className="grid grid-cols-3 gap-3">
              {ROLES.map(({ label, icon }) => (
                <RoleCard
                  key={label}
                  label={label}
                  icon={icon}
                  selected={roles.includes(label)}
                  onToggle={() => toggleRole(label)}
                />
              ))}
            </div>
            <div className="flex gap-3">
              <Button variant="outline" size="lg" className="flex-1" onClick={() => setStep(0)}>
                Back
              </Button>
              <Button
                variant="solid" size="lg" className="flex-1"
                onClick={() => setStep(2)}
                iconRight={<ArrowRight size={15} />}
              >
                Continue
              </Button>
            </div>
          </motion.div>
        )}

        {step === 2 && (
          <motion.div
            key="step2"
            variants={stepVariants}
            initial="enter"
            animate="center"
            exit="exit"
            transition={{ duration: 0.22 }}
            className="space-y-7"
          >
            <div className="space-y-1.5">
              <h1 className="text-2xl font-bold text-[var(--v2-text)]">What are you focused on?</h1>
              <p className="text-[var(--v2-muted)] text-sm">
                Chief tracks these as active projects in your Life Graph. Add up to 3.
              </p>
            </div>
            <FocusTagInput
              tags={focuses}
              onChange={setFocuses}
              roles={roles}
              maxTags={3}
            />
            <div className="flex gap-3">
              <Button variant="outline" size="lg" className="flex-1" onClick={() => setStep(1)}>
                Back
              </Button>
              <Button
                variant="solid" size="lg" className="flex-1"
                loading={submitting}
                onClick={handleComplete}
                iconRight={!submitting ? <Zap size={15} /> : undefined}
              >
                Start using Chief
              </Button>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
