import { useState, useEffect } from 'react'
import { QRCodeSVG } from 'qrcode.react'
import {
  X,
  DeviceMobileCamera,
  Copy as CopySimple,
  Check as CheckSimple,
  ArrowUpRight as ArrowUpRight,
} from '@phosphor-icons/react'

const MOBILE_URL = 'https://innovate-idbi.vercel.app/'
const DO_NOT_SHOW_KEY = 'idbi-qr-dont-show'

// ─── QR modal ──────────────────────────────────────────────────────────────────
// Shown automatically on a user's first visit (per browser session) and reachable
// again at any time via the floating "scan" button. Explains that the experience is
// tuned for mobile widths (the problem statement asked for integration into the
// existing mobile app) and lets the visitor open it on a phone.

export default function QrModal({ open, onClose }) {
  const [copied, setCopied] = useState(false)

  // Close on Escape
  useEffect(() => {
    if (!open) return
    const onKey = (e) => {
      if (e.key === 'Escape') onClose()
    }
    document.addEventListener('keydown', onKey)
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = ''
    }
  }, [open, onClose])

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(MOBILE_URL)
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    } catch {
      /* clipboard may be blocked; ignore */
    }
  }

  if (!open) return null

  return (
    <div
      className="fixed inset-0 z-[100] flex items-center justify-center p-4"
      role="dialog"
      aria-modal="true"
      aria-labelledby="qr-modal-title"
    >
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/50 backdrop-blur-sm animate-[fadeIn_0.2s_ease-out]"
        onClick={onClose}
      />

      {/* Card */}
      <div className="relative z-10 w-full max-w-sm overflow-hidden rounded-2xl border border-border bg-card text-card-foreground shadow-2xl animate-[popIn_0.25s_cubic-bezier(0.16,1,0.3,1)]">
        {/* Header */}
        <div className="flex items-start gap-3 bg-gradient-to-br from-primary to-[#0b6f63] p-5 text-primary-foreground">
          <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-xl bg-white/15">
            <DeviceMobileCamera size={24} weight="bold" />
          </div>
          <div className="flex-1">
            <h2 id="qr-modal-title" className="text-lg font-semibold leading-tight">
              Best viewed on your phone
            </h2>
            <p className="mt-0.5 text-sm text-primary-foreground/80">
              Scan the code or open the link below
            </p>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded-lg p-1.5 text-primary-foreground/80 transition-colors hover:bg-white/15 hover:text-primary-foreground"
          >
            <X size={20} weight="bold" />
          </button>
        </div>

        {/* Body */}
        <div className="space-y-4 p-5">
          <p className="text-sm leading-relaxed text-muted-foreground">
            The problem statement asked us to integrate this experience into your
            existing mobile app, so we have tailored the interface specifically for
            mobile widths. It works on wider screens too — but for the best
            experience, scan this QR code with your phone, or open the link below on
            your mobile device.
          </p>

          {/* QR */}
          <div className="flex justify-center">
            <div className="rounded-2xl border border-border bg-white p-4 shadow-sm">
              <QRCodeSVG
                value={MOBILE_URL}
                size={184}
                level="M"
                fgColor="#075e54"
                bgColor="#ffffff"
                includeMargin={false}
              />
            </div>
          </div>

          {/* Link row */}
          <div className="flex items-center gap-2 rounded-xl border border-border bg-muted/60 p-2">
            <a
              href={MOBILE_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="flex min-w-0 flex-1 items-center gap-1.5 text-sm font-medium text-primary hover:underline"
            >
              <span className="truncate">{MOBILE_URL}</span>
              <ArrowUpRight size={16} weight="bold" className="shrink-0" />
            </a>
            <button
              onClick={handleCopy}
              aria-label="Copy link"
              className="shrink-0 rounded-lg p-2 text-muted-foreground transition-colors hover:bg-accent hover:text-accent-foreground"
            >
              {copied ? (
                <CheckSimple size={18} weight="bold" className="text-accent" />
              ) : (
                <CopySimple size={18} weight="bold" />
              )}
            </button>
          </div>

          {/* Don't show again */}
          <label className="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground">
            <input
              type="checkbox"
              defaultChecked={localStorage.getItem(DO_NOT_SHOW_KEY) === '1'}
              onChange={(e) =>
                localStorage.setItem(DO_NOT_SHOW_KEY, e.target.checked ? '1' : '0')
              }
              className="h-4 w-4 rounded border-border accent-[#075e54]"
            />
            Don&apos;t show this automatically again
          </label>
        </div>
      </div>
    </div>
  )
}
