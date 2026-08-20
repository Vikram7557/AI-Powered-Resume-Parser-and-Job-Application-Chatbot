export default function ChatInput({ value, onChange, onSend, disabled, done, suggestions, onSuggestion }) {
  return (
    <div className="border-t border-white/10 bg-[#0e1730] p-4">
      {suggestions?.length > 0 && (
        <div className="mb-3 flex flex-wrap gap-2">
          {suggestions.map((label) => (
            <button
              key={label}
              type="button"
              disabled={disabled}
              onClick={() => onSuggestion(label)}
              className="rounded-full border border-white/10 bg-white/5 px-3 py-1.5 text-xs text-slate-200 hover:border-cyan-400/40 hover:bg-cyan-400/10 disabled:opacity-40"
            >
              {label}
            </button>
          ))}
        </div>
      )}
      <div className="flex gap-2">
        <input
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && onSend()}
          placeholder={done ? "Ask a follow-up about hiring…" : "Type a message…"}
          disabled={disabled}
          className="flex-1 rounded-full border border-white/10 bg-white/5 px-4 py-3 text-sm text-white outline-none placeholder:text-slate-500 focus:border-cyan-400/60"
        />
        <button
          type="button"
          onClick={onSend}
          disabled={disabled || !value.trim()}
          className="rounded-full bg-cyan-400 px-5 py-3 text-sm font-semibold text-slate-950 disabled:cursor-not-allowed disabled:opacity-40"
        >
          Send
        </button>
      </div>
    </div>
  );
}
