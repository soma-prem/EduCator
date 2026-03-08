import { useEffect, useState } from "react";
import { toast } from "react-toastify";
import { useNavigate } from "react-router-dom";
import { API_BASE } from "../../config/api";
import HistoryPanel from "./HistoryPanel";

function HistoryPage() {
  const navigate = useNavigate();
  const [historyItems, setHistoryItems] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [expandedHistoryId, setExpandedHistoryId] = useState("");

  const getReadableErrorMessage = (error, fallbackMessage) => {
    const raw = String(error?.message || "").toLowerCase();
    if (raw.includes("failed to fetch") || raw.includes("networkerror") || raw.includes("load failed")) {
      return `Cannot reach backend at ${API_BASE}. Start backend server and verify CORS/API URL.`;
    }
    return error?.message || fallbackMessage;
  };

  const loadHistory = async () => {
    try {
      setHistoryLoading(true);
      const response = await fetch(`${API_BASE}/api/history?limit=25`);
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || "Failed to load history");
      }
      setHistoryItems(Array.isArray(data?.items) ? data.items : []);
    } catch (error) {
      console.error(error);
      toast.error(getReadableErrorMessage(error, "Failed to load history"));
    } finally {
      setHistoryLoading(false);
    }
  };

  useEffect(() => {
    loadHistory();
  }, []);

  const toggleHistoryDetails = (id) => {
    setExpandedHistoryId((prev) => (prev === id ? "" : id));
  };

  const handleClearHistory = async () => {
    try {
      setHistoryLoading(true);
      const response = await fetch(`${API_BASE}/api/history/clear`, { method: "POST" });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || "Failed to clear history");
      }
      setHistoryItems([]);
      toast.success("History cleared");
    } catch (error) {
      console.error(error);
      toast.error(getReadableErrorMessage(error, "Failed to clear history"));
    } finally {
      setHistoryLoading(false);
    }
  };

  const handleDeleteHistoryItem = async (id) => {
    try {
      const response = await fetch(`${API_BASE}/api/history/${id}`, { method: "DELETE" });
      const data = await response.json();
      if (!response.ok) {
        throw new Error(data?.error || "Failed to delete history item");
      }
      if (!data?.deleted) {
        throw new Error(data?.message || "History item not deleted");
      }
      setHistoryItems((prev) => prev.filter((item) => item.id !== id));
      setExpandedHistoryId((prev) => (prev === id ? "" : prev));
      toast.success("History item deleted");
    } catch (error) {
      console.error(error);
      toast.error(getReadableErrorMessage(error, "Failed to delete history item"));
    }
  };

  return (
    <main className="upload-page">
      <div className="home-bots" aria-hidden="true">
        <div className="boat-group">
          <img src="/blue.png" alt="" className="bot boat boat-blue" />
        </div>
      </div>
      <section className="upload-card upload-layout notebook-shell">
        <header className="upload-header">
          <button type="button" className="history-btn" onClick={() => navigate("/uplod")}>
            Back
          </button>
          <h1>Study Resource History</h1>
          <p>Saved sources, MCQs, flashcards, and summaries.</p>
        </header>

        <div className="notebook-grid notebook-grid-full">
          <section className="notebook-card notebook-sources history-wide">
            <div className="card-header">
              <h2 className="card-title">History</h2>
            </div>
            <p className="card-subtitle">Review and manage your saved sessions.</p>
            <div className="notebook-card-body">
              <HistoryPanel
                historyItems={historyItems}
                historyLoading={historyLoading}
                expandedHistoryId={expandedHistoryId}
                onClearHistory={handleClearHistory}
                onToggleDetails={toggleHistoryDetails}
                onDeleteItem={handleDeleteHistoryItem}
              />
            </div>
          </section>
        </div>
      </section>
    </main>
  );
}

export default HistoryPage;
