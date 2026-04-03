import { useCallback, useEffect, useRef, useState } from "react";
import { toast } from "react-toastify";

function VoiceTutorSection({ apiBase }) {
  const [history, setHistory] = useState([]);
  const historyRef = useRef([]);
  const [listening, setListening] = useState(false);
  const [recognizer, setRecognizer] = useState(null);
  const [pendingText, setPendingText] = useState("");
  const [audioUrl, setAudioUrl] = useState("");
  const audioUrlRef = useRef("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    historyRef.current = history;
  }, [history]);

  useEffect(() => {
    audioUrlRef.current = audioUrl;
  }, [audioUrl]);

  useEffect(() => {
    return () => {
      if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
    };
  }, []);

  const sendMessage = useCallback(
    async (text) => {
      if (!text) return;
      setLoading(true);
      try {
        const response = await fetch(`${apiBase}/api/voice/chat`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ message: text, history: historyRef.current }),
        });
        const data = await response.json().catch(() => ({}));
        if (!response.ok) {
          throw new Error(data?.error || "Voice tutor failed");
        }

        const reply = data.reply || "";
        const suggestions = Array.isArray(data.suggestions) ? data.suggestions : [];

        setHistory((prev) => [...prev.slice(-6), { role: "user", text }, { role: "assistant", text: reply }]);

        if (reply) {
          const ttsResp = await fetch(`${apiBase}/api/tts`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ text: reply, language: "en" }),
          });
          if (ttsResp.ok) {
            const blob = await ttsResp.blob();
            const url = URL.createObjectURL(blob);
            if (audioUrlRef.current) URL.revokeObjectURL(audioUrlRef.current);
            setAudioUrl(url);
          }
        }

        if (suggestions.length > 0) {
          toast.info(suggestions.join(" • "));
        }
      } catch (error) {
        console.error(error);
        toast.error(error.message || "Voice tutor error");
      } finally {
        setLoading(false);
      }
    },
    [apiBase]
  );

  useEffect(() => {
    const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    if (!Recognition) return undefined;

    const rec = new Recognition();
    rec.lang = "en-US";
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onresult = (event) => {
      const text = String(event.results?.[0]?.[0]?.transcript || "").trim();
      if (text) {
        setPendingText(text);
        sendMessage(text);
      }
      setListening(false);
    };
    rec.onerror = () => setListening(false);
    rec.onend = () => setListening(false);
    setRecognizer(rec);

    return () => {
      try {
        rec.onresult = null;
        rec.onerror = null;
        rec.onend = null;
      } catch (_err) {
        // ignore
      }
    };
  }, [sendMessage]);

  const toggleMic = () => {
    if (!recognizer) {
      toast.error("Speech recognition not supported in this browser.");
      return;
    }
    if (listening) {
      recognizer.stop();
      setListening(false);
      return;
    }
    setPendingText("");
    setListening(true);
    recognizer.start();
  };

  return (
    <section className="result-section">
      <div className="summary-header">
        <h3>Voice Tutor</h3>
        <div className="summary-actions">
          <button
            type="button"
            className={`voice-mic-btn ${listening ? "voice-mic-live" : ""}`}
            onClick={toggleMic}
            disabled={loading}
          >
            {listening ? "Stop Mic" : "Mic"}
          </button>
        </div>
      </div>
      <p className="topic-empty-text">Speak to ask a question. The tutor will reply with audio and suggest next steps.</p>
      <div className="summary-text" style={{ maxHeight: "220px", overflowY: "auto" }}>
        {history.map((msg, idx) => (
          <p key={idx}>
            <strong>{msg.role === "user" ? "You: " : "Tutor: "}</strong>
            {msg.text}
          </p>
        ))}
      </div>
      {audioUrl && (
        <div className="summary-audio">
          <audio controls src={audioUrl} autoPlay />
        </div>
      )}
      {pendingText && <p className="topic-empty-text">You said: {pendingText}</p>}
    </section>
  );
}

export default VoiceTutorSection;

