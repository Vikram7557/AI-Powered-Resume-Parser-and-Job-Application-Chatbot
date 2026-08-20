import { useMemo, useState } from "react";

function expLabel(years) {
  if (years === 0.5) return "6+ months experience";
  return `${years}+ years experience`;
}

export default function OpeningsPage({
  roles,
  appliedRoles = [],
  rejectedRoles = [],
  selectedRole,
  onSelectRole,
  onBack,
  onApply,
  disabled,
}) {
  const [query, setQuery] = useState("");
  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return roles;
    return roles.filter((role) => {
      const hay = [
        role.title,
        role.description,
        role.qualifications,
        ...(role.required_skills || []),
        ...(role.nice_to_have || []),
      ]
        .join(" ")
        .toLowerCase();
      return hay.includes(q);
    });
  }, [roles, query]);

  if (selectedRole) {
    const applied = appliedRoles.includes(selectedRole.title);
    const rejected = rejectedRoles.includes(selectedRole.title);
    return (
      <div className="mx-auto w-full max-w-3xl px-4 py-6 lg:px-10">
        <button
          type="button"
          onClick={onBack}
          className="mb-4 text-sm text-cyan-300 hover:text-cyan-200"
        >
          ← Back to openings
        </button>
        <div className="rounded-3xl border border-white/10 bg-[#0e1730] p-6">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div>
              <h2 className="text-2xl font-semibold text-white">{selectedRole.title}</h2>
              <p className="mt-1 text-sm text-slate-400">{expLabel(selectedRole.min_experience_years)}</p>
            </div>
            <div className="flex items-center gap-2">
              {applied && (
                <span className="rounded-full bg-emerald-400/20 px-3 py-1 text-xs text-emerald-200">Applied</span>
              )}
              {rejected && (
                <span className="rounded-full bg-rose-400/20 px-3 py-1 text-xs text-rose-200">Not selected</span>
              )}
              <button
                type="button"
                disabled={disabled}
                onClick={() => onApply(selectedRole.title)}
                className="rounded-full bg-cyan-400 px-4 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-40"
              >
                Apply
              </button>
            </div>
          </div>

          <section className="mt-6">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">About the role</h3>
            <p className="mt-2 whitespace-pre-wrap text-sm leading-relaxed text-slate-200">
              {selectedRole.description}
            </p>
          </section>

          <section className="mt-6">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">What you'll do</h3>
            <ul className="mt-2 list-disc space-y-1 pl-5 text-sm text-slate-200">
              {(selectedRole.responsibilities || []).map((item) => (
                <li key={item}>{item}</li>
              ))}
            </ul>
          </section>

          <section className="mt-6">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Required skills</h3>
            <div className="mt-2 flex flex-wrap gap-1.5">
              {(selectedRole.required_skills || []).map((skill) => (
                <span key={skill} className="rounded-full bg-cyan-400/10 px-2.5 py-1 text-xs text-cyan-100">
                  {skill}
                </span>
              ))}
            </div>
          </section>

          {(selectedRole.nice_to_have || []).length > 0 && (
            <section className="mt-6">
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Nice to have</h3>
              <div className="mt-2 flex flex-wrap gap-1.5">
                {selectedRole.nice_to_have.map((skill) => (
                  <span key={skill} className="rounded-full bg-white/10 px-2.5 py-1 text-xs text-slate-200">
                    {skill}
                  </span>
                ))}
              </div>
            </section>
          )}

          <section className="mt-6 grid gap-4 sm:grid-cols-2">
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Qualifications</h3>
              <p className="mt-2 text-sm text-slate-200">{selectedRole.qualifications}</p>
            </div>
            <div>
              <h3 className="text-xs font-semibold uppercase tracking-wide text-slate-500">Experience</h3>
              <p className="mt-2 text-sm text-slate-200">{expLabel(selectedRole.min_experience_years)}</p>
            </div>
          </section>
        </div>
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-5xl px-4 py-6 lg:px-10">
      <div className="mb-5 flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 className="text-xl font-semibold text-white">Open roles</h2>
          <p className="text-sm text-slate-400">
            Browse openings. View a description, or apply to continue in chat with Ava.
          </p>
        </div>
        <p className="text-xs text-slate-500">
          {filtered.length} opening{filtered.length === 1 ? "" : "s"}
        </p>
      </div>

      <input
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        placeholder="Search by title, skill, or keyword…"
        className="mb-5 w-full rounded-full border border-white/10 bg-white/5 px-4 py-2.5 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-400/60"
      />

      {filtered.length === 0 && (
        <p className="text-sm text-slate-400">No openings match that search.</p>
      )}

      <div className="grid gap-4 md:grid-cols-2">
        {filtered.map((role) => {
          const applied = appliedRoles.includes(role.title);
          const rejected = rejectedRoles.includes(role.title);
          return (
            <article
              key={role.title}
              className="flex flex-col rounded-3xl border border-white/10 bg-[#0e1730] p-5"
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <h3 className="text-lg font-semibold text-white">{role.title}</h3>
                  <p className="mt-0.5 text-xs text-slate-400">{expLabel(role.min_experience_years)}</p>
                </div>
                {applied && (
                  <span className="rounded-full bg-emerald-400/20 px-2 py-0.5 text-[10px] text-emerald-200">Applied</span>
                )}
                {rejected && !applied && (
                  <span className="rounded-full bg-rose-400/20 px-2 py-0.5 text-[10px] text-rose-200">Not selected</span>
                )}
              </div>
              <p className="mt-3 line-clamp-3 flex-1 text-sm leading-relaxed text-slate-400">
                {role.description}
              </p>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {(role.required_skills || []).map((skill) => (
                  <span key={skill} className="rounded-full bg-white/10 px-2 py-0.5 text-[11px] text-slate-200">
                    {skill}
                  </span>
                ))}
              </div>
              <div className="mt-4 flex gap-2">
                <button
                  type="button"
                  onClick={() => onSelectRole(role)}
                  className="flex-1 rounded-full border border-white/15 bg-white/5 py-2 text-sm font-medium text-slate-200 hover:border-cyan-400/40 hover:bg-cyan-400/10"
                >
                  View
                </button>
                <button
                  type="button"
                  disabled={disabled}
                  onClick={() => onApply(role.title)}
                  className="flex-1 rounded-full bg-cyan-400 py-2 text-sm font-semibold text-slate-950 hover:bg-cyan-300 disabled:opacity-40"
                >
                  Apply
                </button>
              </div>
            </article>
          );
        })}
      </div>
    </div>
  );
}
