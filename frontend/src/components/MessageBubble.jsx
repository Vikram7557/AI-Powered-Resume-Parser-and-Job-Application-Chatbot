function renderText(text) {
  const parts = String(text || "").split(/(\*\*[^*]+\*\*)/g);
  return parts.map((part, i) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={i} className="font-semibold text-white">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return part;
  });
}

export default function MessageBubble({
  sender,
  text,
  suggestions,
  onSuggestion,
  disabled,
}) {
  const isUser = sender === "user";

  return (
    <div className={`flex ${isUser ? "justify-end" : "justify-start"}`}>
      {!isUser && (
        <div className="mr-2 mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-cyan-400/20 text-xs font-semibold text-cyan-200">
          A
        </div>
      )}
      <div className={`max-w-[78%] ${isUser ? "" : "w-full"}`}>
        <div
          className={`whitespace-pre-wrap rounded-2xl px-4 py-3 text-sm leading-relaxed ${
            isUser
              ? "rounded-br-md bg-cyan-500 text-slate-950"
              : "rounded-bl-md bg-white/10 text-slate-100"
          }`}
        >
          {renderText(text)}
        </div>
        {!isUser && suggestions?.length > 0 && (
          <div className="mt-2 flex flex-wrap gap-1.5">
            {suggestions.map((label) => (
              <button
                key={label}
                type="button"
                disabled={disabled}
                onClick={() => onSuggestion(label)}
                className="rounded-full border border-cyan-400/30 bg-cyan-400/10 px-3 py-1 text-[11px] text-cyan-100 hover:bg-cyan-400/20 disabled:opacity-40"
              >
                {label}
              </button>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
