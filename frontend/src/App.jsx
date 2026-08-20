import { useEffect, useRef, useState } from "react";
import {
  createSession,
  fetchRoles,
  quickApply,
  reuseResume,
  sendChatMessage,
  uploadResume,
} from "./api";
import Sidebar from "./components/Sidebar.jsx";
import MessageBubble from "./components/MessageBubble.jsx";
import ResumeUpload from "./components/ResumeUpload.jsx";
import ChatInput from "./components/ChatInput.jsx";
import OpeningsPage from "./components/OpeningsPage.jsx";

export default function App() {
  const [tab, setTab] = useState("chat");
  const [viewingRole, setViewingRole] = useState(null);
  const [sessionId, setSessionId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [stage, setStage] = useState("CHATTING");
  const [busy, setBusy] = useState(true);
  const [roles, setRoles] = useState([]);
  const [profile, setProfile] = useState(null);
  const [matches, setMatches] = useState([]);
  const [intendedRole, setIntendedRole] = useState(null);
  const [appliedRoles, setAppliedRoles] = useState([]);
  const [rejectedRoles, setRejectedRoles] = useState([]);
  const [resumeFilename, setResumeFilename] = useState(null);
  const [modelLabel, setModelLabel] = useState("Claude");
  const [error, setError] = useState("");
  const bottomRef = useRef(null);

  function applySnapshot(res) {
    if (!res) return;
    if (res.stage) setStage(res.stage);
    if (res.profile) setProfile(res.profile);
    if (Array.isArray(res.matches)) setMatches(res.matches);
    if (res.intended_role !== undefined) setIntendedRole(res.intended_role);
    if (Array.isArray(res.applied_roles)) setAppliedRoles(res.applied_roles);
    if (Array.isArray(res.rejected_roles)) setRejectedRoles(res.rejected_roles);
    if (res.resume_filename !== undefined) setResumeFilename(res.resume_filename);
    if (res.model_label) setModelLabel(res.model_label);
  }

  function pushBot(res) {
    applySnapshot(res);
    setMessages((m) => [
      ...m,
      {
        sender: "bot",
        text: res.reply,
        suggestions: res.suggestions || [],
      },
    ]);
  }

  useEffect(() => {
    (async () => {
      try {
        const [id, openRoles] = await Promise.all([createSession(), fetchRoles().catch(() => [])]);
        setSessionId(id);
        setRoles(openRoles);
        const res = await sendChatMessage(id, "Hi");
        setMessages([
          {
            sender: "bot",
            text: res.reply,
            suggestions: res.suggestions || [],
          },
        ]);
        applySnapshot(res);
      } catch {
        setError("Could not connect to the FastAPI backend on port 8000.");
        setMessages([
          {
            sender: "bot",
            text: "I couldn't reach the server. Start the backend with uvicorn, then refresh this page.",
          },
        ]);
      } finally {
        setBusy(false);
      }
    })();
  }, []);

  useEffect(() => {
    if (tab === "chat") {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, busy, tab]);

  async function runAction(userLabel, action) {
    if (busy || !sessionId) return;
    setInput("");
    setMessages((m) => [...m, { sender: "user", text: userLabel }]);
    setBusy(true);
    setError("");
    try {
      const res = await action();
      pushBot(res);
    } catch {
      setMessages((m) => [
        ...m,
        { sender: "bot", text: "Something went wrong. Please try again." },
      ]);
    } finally {
      setBusy(false);
    }
  }

  async function handleSend(preset) {
    const userMsg = (typeof preset === "string" ? preset : input).trim();
    if (!userMsg || busy || !sessionId) return;
    await runAction(userMsg, () => sendChatMessage(sessionId, userMsg));
  }

  async function handleFileUpload(file) {
    await runAction(`Uploaded ${file.name}`, () => uploadResume(sessionId, file));
  }

  async function handleReuseResume() {
    await runAction("Continue with the uploaded resume", () =>
      reuseResume(sessionId, intendedRole)
    );
  }

  async function handleApply(title) {
    setViewingRole(null);
    setTab("chat");
    await runAction(`I'd like to apply for the ${title} role.`, () =>
      quickApply(sessionId, title)
    );
  }

  async function handleSuggestion(label) {
    if (label === "Show open roles" || label === "See other roles") {
      setViewingRole(null);
      setTab("openings");
      return;
    }
    const applyMatch = label.match(/^Apply for (.+)$/i);
    if (applyMatch) {
      await handleApply(applyMatch[1]);
      return;
    }
    if (label === "Continue with the uploaded resume") {
      await handleReuseResume();
      return;
    }
    await handleSend(label);
  }

  const done = stage === "DONE";
  const showResumePanel = stage === "AWAIT_RESUME" || stage === "AWAIT_RESUME_CHOICE";
  const allowReuse = Boolean(profile) && showResumePanel;
  const lastBotIndex = messages.reduce((acc, m, i) => (m.sender === "bot" ? i : acc), -1);

  return (
    <div className="flex h-full min-h-screen bg-[#0b1220] text-slate-100">
      <Sidebar
        stage={stage}
        profile={profile}
        matches={matches}
        intendedRole={intendedRole}
        appliedRoles={appliedRoles}
        rejectedRoles={rejectedRoles}
      />

      <main className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between gap-3 border-b border-white/10 px-5 py-3 lg:px-8">
          <div className="flex rounded-full bg-white/5 p-1">
            <button
              type="button"
              onClick={() => setTab("chat")}
              className={`rounded-full px-4 py-1.5 text-sm font-medium ${
                tab === "chat" ? "bg-cyan-400 text-slate-950" : "text-slate-300 hover:text-white"
              }`}
            >
              Chat assistant
            </button>
            <button
              type="button"
              onClick={() => setTab("openings")}
              className={`rounded-full px-4 py-1.5 text-sm font-medium ${
                tab === "openings" ? "bg-cyan-400 text-slate-950" : "text-slate-300 hover:text-white"
              }`}
            >
              Openings
            </button>
          </div>
          <span className="rounded-full border border-white/10 bg-white/5 px-3 py-1 text-xs text-slate-300">
            {error ? "Offline" : `FastAPI · ${modelLabel}`}
          </span>
        </header>

        {tab === "openings" ? (
          <div className="flex-1 overflow-y-auto">
            <OpeningsPage
              roles={roles}
              appliedRoles={appliedRoles}
              rejectedRoles={rejectedRoles}
              selectedRole={viewingRole}
              onSelectRole={setViewingRole}
              onBack={() => setViewingRole(null)}
              onApply={handleApply}
              disabled={busy || !sessionId}
            />
          </div>
        ) : (
          <>
            <div className="flex-1 space-y-4 overflow-y-auto px-4 py-6 lg:px-10">
              {messages.map((m, i) => (
                <MessageBubble
                  key={i}
                  sender={m.sender}
                  text={m.text}
                  suggestions={i === lastBotIndex ? m.suggestions : []}
                  onSuggestion={handleSuggestion}
                  disabled={busy}
                />
              ))}
              {busy && (
                <p className="pl-10 text-sm text-slate-500">Ava is typing…</p>
              )}
              <div ref={bottomRef} />
            </div>

            {showResumePanel && (
              <ResumeUpload
                onUpload={handleFileUpload}
                onReuse={handleReuseResume}
                disabled={busy}
                existingName={resumeFilename}
                allowReuse={allowReuse}
              />
            )}
            <ChatInput
              value={input}
              onChange={setInput}
              onSend={handleSend}
              disabled={busy || !sessionId}
              done={done}
              suggestions={[]}
              onSuggestion={handleSuggestion}
            />
          </>
        )}
      </main>
    </div>
  );
}
