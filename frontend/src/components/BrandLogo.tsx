import React from 'react';

export function BrandLogo({
  compact = false,
  onDark = false,
}: {
  compact?: boolean;
  onDark?: boolean;
}) {
  const logoImg = (
    <img
      src="/images/chanakya/chanakya-logo-official.png"
      alt="Chanakya University"
      className="h-9 w-auto object-contain select-none"
    />
  );

  if (onDark) {
    return (
      <div className="inline-flex items-center gap-3">
        <div className="bg-white/95 rounded-lg px-3 py-1.5 shadow-sm inline-flex items-center">
          {logoImg}
        </div>
        {!compact && (
          <div className="border-l border-white/25 pl-3 leading-tight">
            <div className="text-xs font-semibold tracking-wide text-[#FBF5E4] uppercase">
              Research Commons
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <div className="inline-flex items-center gap-3 py-1">
      {logoImg}
      {!compact && (
        <div className="border-l border-[#DCD7CA] pl-3 leading-tight hidden sm:block">
          <div className="text-[11px] font-semibold uppercase tracking-[0.08em] text-[#142B4A]">
            Research Commons
          </div>
          <div className="text-[10px] text-[#697386]">Campus Community</div>
        </div>
      )}
    </div>
  );
}
