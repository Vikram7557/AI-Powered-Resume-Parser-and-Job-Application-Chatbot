import { useRef, useState } from "react";

export default function ResumeUpload({
  onUpload,
  onReuse,
  disabled,
  existingName,
  allowReuse,
}) {
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  function handleFiles(files) {
    const file = files?.[0];
    if (!file || disabled) return;
    onUpload(file);
  }

  return (
    <div className="border-t border-white/10 bg-[#101a33] px-4 py-3 space-y-2">
      {allowReuse && (
        <button
          type="button"
          disabled={disabled}
          onClick={onReuse}
          className="flex w-full items-center justify-between rounded-2xl border border-emerald-400/40 bg-emerald-400/10 px-4 py-3 text-left hover:bg-emerald-400/15 disabled:opacity-50"
        >
          <div>
            <p className="text-sm font-medium text-emerald-100">Continue with uploaded resume</p>
            <p className="text-xs text-slate-400">{existingName || "Resume already on file"}</p>
          </div>
          <span className="rounded-full bg-emerald-400 px-3 py-1 text-xs font-semibold text-slate-950">
            Use this
          </span>
        </button>
      )}
      <button
        type="button"
        disabled={disabled}
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragOver(false);
          handleFiles(e.dataTransfer.files);
        }}
        className={`flex w-full items-center justify-between rounded-2xl border border-dashed px-4 py-3 text-left transition ${dragOver
            ? "border-cyan-300 bg-cyan-400/10"
            : "border-cyan-400/40 bg-cyan-400/5 hover:bg-cyan-400/10"
          } disabled:opacity-50`}
      >
        <div>
          <p className="text-sm font-medium text-cyan-100">
            {allowReuse ? "Upload a different resume (PDF or TXT)" : "Upload your resume (PDF or TXT)"}
          </p>
          <p className="text-xs text-slate-400">PDF or .txt — drag and drop, or click to browse</p>
        </div>
        <span className="rounded-full bg-cyan-400 px-3 py-1 text-xs font-semibold text-slate-950">
          Choose file
        </span>
      </button>
      <input
        ref={inputRef}
        type="file"
        accept=".pdf,.txt,text/plain,application/pdf"
        className="hidden"
        disabled={disabled}
        onChange={(e) => handleFiles(e.target.files)}
      />
    </div>
  );
}
