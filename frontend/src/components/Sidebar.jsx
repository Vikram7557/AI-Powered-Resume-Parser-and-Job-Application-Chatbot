function badgeFor(roleTitle, { intendedRole, appliedRoles, rejectedRoles, match }) {
  if (appliedRoles.includes(roleTitle)) {
    return { label: "Applied", className: "bg-emerald-400/20 text-emerald-200" };
  }
  if (rejectedRoles.includes(roleTitle)) {
    return { label: "Not selected", className: "bg-rose-400/20 text-rose-200" };
  }
  if (match?.qualifies && intendedRole !== roleTitle) {
    return { label: "Good match", className: "bg-cyan-400/20 text-cyan-200" };
  }
  if (intendedRole === roleTitle) {
    return { label: "Selected", className: "bg-white/10 text-slate-300" };
  }
  return null;
}

function MatchRow({ item, intendedRole, appliedRoles, rejectedRoles }) {
  const pct = Math.round((item.confidence || 0) * 100);
  const badge = badgeFor(item.role, {
    intendedRole,
    appliedRoles,
    rejectedRoles,
    match: item,
  });

  return (
    <div className="rounded-xl border border-white/10 bg-white/5 p-3">
      <div className="flex items-start justify-between gap-2">
        <p className="text-sm font-medium text-white">{item.role}</p>
        {badge && (
          <span className={`shrink-0 rounded-full px-2 py-0.5 text-[10px] font-medium ${badge.className}`}>
            {badge.label}
          </span>
        )}
      </div>
      <div className="mt-2 h-1.5 overflow-hidden rounded-full bg-white/10">
        <div
          className={`h-full rounded-full ${item.qualifies ? "bg-cyan-400" : "bg-rose-400/80"}`}
          style={{ width: `${pct}%` }}
        />
      </div>
      <p className="mt-1 text-xs text-slate-400">
        {pct}% · {item.qualifies ? "qualifies" : "below threshold"}
      </p>
    </div>
  );
}

export default function Sidebar({
  stage,
  profile,
  matches,
  intendedRole,
  appliedRoles = [],
  rejectedRoles = [],
}) {
  const stageLabel = {
    CHATTING: "Chatting",
    AWAIT_RESUME: "Awaiting resume",
    AWAIT_RESUME_CHOICE: "Resume on file",
    AWAIT_CONTACT_CONFIRM: "Confirming contact",
    DONE: "Application complete",
  }[stage] || stage;

  const scored = (matches && matches.length > 0)
    ? matches
    : [];

  return (
    <aside className="hidden w-[320px] shrink-0 flex-col overflow-y-auto border-r border-white/10 bg-[#0e1730] lg:flex">
      <div className="border-b border-white/10 px-6 py-5">
        <p className="text-xs font-semibold uppercase tracking-[0.18em] text-cyan-300/80">
          Conversive.ai
        </p>
        <h1 className="mt-1 text-xl font-semibold text-white">Ava</h1>
        <p className="mt-1 text-sm text-slate-400">Job application assistant</p>
      </div>

      <div className="px-6 py-4">
        <p className="text-xs font-medium uppercase tracking-wide text-slate-500">Status</p>
        <div className="mt-2 inline-flex items-center gap-2 rounded-full bg-white/5 px-3 py-1 text-sm text-slate-200">
          <span className="h-2 w-2 rounded-full bg-emerald-400" />
          {stageLabel}
        </div>
      </div>

      {scored.length > 0 && (
        <div className="mx-4 space-y-2">
          <p className="text-xs uppercase tracking-wide text-cyan-300/80">Role matches</p>
          {scored.map((item) => (
            <MatchRow
              key={item.role}
              item={item}
              intendedRole={intendedRole}
              appliedRoles={appliedRoles}
              rejectedRoles={rejectedRoles}
            />
          ))}
        </div>
      )}

      {profile && (
        <div className="mx-4 mt-4 mb-6 rounded-2xl border border-white/10 bg-white/5 p-4">
          <p className="text-xs uppercase tracking-wide text-slate-500">Parsed profile</p>
          <p className="mt-2 font-medium text-white">{profile.name || "Unknown"}</p>
          <p className="text-sm text-slate-400">{profile.email}</p>
          <p className="text-sm text-slate-400">{profile.phone}</p>
          <p className="mt-2 text-xs text-slate-500">{profile.education}</p>
          <div className="mt-3 flex flex-wrap gap-1.5">
            {(profile.skills || []).slice(0, 8).map((skill) => (
              <span
                key={skill}
                className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] text-slate-200"
              >
                {skill}
              </span>
            ))}
          </div>
        </div>
      )}
    </aside>
  );
}
