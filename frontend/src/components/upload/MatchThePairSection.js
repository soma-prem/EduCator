import { useEffect, useMemo, useRef, useState } from "react";

function shuffle(items) {
  const copy = Array.isArray(items) ? [...items] : [];
  for (let i = copy.length - 1; i > 0; i -= 1) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function normalizePairs(rawSet) {
  const rawPairs = Array.isArray(rawSet?.pairs) ? rawSet.pairs : [];
  return rawPairs
    .map((pair, index) => ({
      id: index,
      left: String(pair?.left || "").trim(),
      right: String(pair?.right || "").trim(),
    }))
    .filter((pair) => pair.left && pair.right);
}

function MatchThePairSet({ title, pairs, setIndex }) {
  const [leftCards, setLeftCards] = useState([]);
  const [rightCards, setRightCards] = useState([]);
  const [matchedIds, setMatchedIds] = useState({});
  const [selectedLeftId, setSelectedLeftId] = useState(null);
  const [selectedRightId, setSelectedRightId] = useState(null);
  const [wrongLeftId, setWrongLeftId] = useState(null);
  const [wrongRightId, setWrongRightId] = useState(null);
  const [lineCoords, setLineCoords] = useState([]);
  const boardRef = useRef(null);
  const wrongDropTimerRef = useRef(null);

  useEffect(() => {
    const nextLeft = pairs.map((pair) => ({ id: pair.id, text: pair.left }));
    const nextRight = pairs.map((pair) => ({ id: pair.id, text: pair.right }));
    setLeftCards(shuffle(nextLeft));
    setRightCards(shuffle(nextRight));
    setMatchedIds({});
    setSelectedLeftId(null);
    setSelectedRightId(null);
    setWrongLeftId(null);
    setWrongRightId(null);
    setLineCoords([]);
    if (wrongDropTimerRef.current) {
      clearTimeout(wrongDropTimerRef.current);
      wrongDropTimerRef.current = null;
    }
  }, [pairs]);

  useEffect(() => {
    return () => {
      if (wrongDropTimerRef.current) {
        clearTimeout(wrongDropTimerRef.current);
      }
    };
  }, []);

  const totalCount = pairs.length;
  const matchedCount = Object.keys(matchedIds).length;
  const isComplete = totalCount > 0 && matchedCount === totalCount;

  const handleLeftCardClick = (id) => {
    if (matchedIds[id] || wrongLeftId !== null) return;

    if (selectedRightId !== null) {
      if (id === selectedRightId) {
        setMatchedIds((prev) => ({ ...prev, [id]: true }));
        setSelectedLeftId(null);
        setSelectedRightId(null);
      } else {
        setWrongLeftId(id);
        setWrongRightId(selectedRightId);
        triggerWrongFeedback();
      }
    } else {
      setSelectedLeftId((prev) => (prev === id ? null : id));
    }
  };

  const handleRightCardClick = (id) => {
    if (matchedIds[id] || wrongRightId !== null) return;

    if (selectedLeftId !== null) {
      if (id === selectedLeftId) {
        setMatchedIds((prev) => ({ ...prev, [id]: true }));
        setSelectedLeftId(null);
        setSelectedRightId(null);
      } else {
        setWrongLeftId(selectedLeftId);
        setWrongRightId(id);
        triggerWrongFeedback();
      }
    } else {
      setSelectedRightId((prev) => (prev === id ? null : id));
    }
  };

  const triggerWrongFeedback = () => {
    if (wrongDropTimerRef.current) {
      clearTimeout(wrongDropTimerRef.current);
    }
    wrongDropTimerRef.current = setTimeout(() => {
      setWrongLeftId(null);
      setWrongRightId(null);
      setSelectedLeftId(null);
      setSelectedRightId(null);
      wrongDropTimerRef.current = null;
    }, 550);
  };

  const updateLineCoords = () => {
    if (!boardRef.current) return;
    const parentRect = boardRef.current.getBoundingClientRect();
    const coords = [];
    pairs.forEach((pair) => {
      if (matchedIds[pair.id]) {
        const leftEl = document.getElementById(`match-left-${setIndex}-${pair.id}`);
        const rightEl = document.getElementById(`match-right-${setIndex}-${pair.id}`);
        if (leftEl && rightEl) {
          const leftRect = leftEl.getBoundingClientRect();
          const rightRect = rightEl.getBoundingClientRect();
          coords.push({
            id: pair.id,
            x1: leftRect.right - parentRect.left,
            y1: leftRect.top + leftRect.height / 2 - parentRect.top,
            x2: rightRect.left - parentRect.left,
            y2: rightRect.top + rightRect.height / 2 - parentRect.top,
          });
        }
      }
    });
    setLineCoords(coords);
  };

  useEffect(() => {
    const handle = requestAnimationFrame(() => {
      updateLineCoords();
    });
    return () => cancelAnimationFrame(handle);
  }, [matchedIds, leftCards, rightCards]);

  useEffect(() => {
    window.addEventListener("resize", updateLineCoords);
    return () => window.removeEventListener("resize", updateLineCoords);
  }, [matchedIds, leftCards, rightCards]);

  const leftLabel = (id) => pairs.find((p) => p.id === id)?.left || "";

  const handleReset = () => {
    const nextLeft = pairs.map((pair) => ({ id: pair.id, text: pair.left }));
    const nextRight = pairs.map((pair) => ({ id: pair.id, text: pair.right }));
    setLeftCards(shuffle(nextLeft));
    setRightCards(shuffle(nextRight));
    setMatchedIds({});
    setSelectedLeftId(null);
    setSelectedRightId(null);
    setWrongLeftId(null);
    setWrongRightId(null);
    setLineCoords([]);
  };

  return (
    <section className="result-section match-pair-set">
      <div className="match-pair-set-header">
        <div>
          <h3>{title || `Set ${setIndex + 1}`}</h3>
          <p className="match-pair-subtitle">
            Click a left card, then click its matching right card to connect them. ({matchedCount}/{totalCount})
          </p>
        </div>
        <div className="match-pair-controls">
          <button type="button" className="ghost-btn" onClick={handleReset}>
            Reset
          </button>
        </div>
      </div>

      {isComplete && <div className="match-pair-complete">All pairs matched.</div>}

      <div 
        ref={boardRef}
        className="match-pair-board" 
        style={{ position: "relative" }}
        role="group" 
        aria-label={`Match the Pair set ${setIndex + 1}`}
      >
        {/* Connection Lines Overlay */}
        <svg 
          style={{
            position: "absolute",
            top: 0,
            left: 0,
            width: "100%",
            height: "100%",
            pointerEvents: "none",
            zIndex: 5
          }}
        >
          {lineCoords.map((coord) => (
            <line
              key={coord.id}
              x1={coord.x1}
              y1={coord.y1}
              x2={coord.x2}
              y2={coord.y2}
              stroke="#10b981"
              strokeWidth="3.5"
              strokeLinecap="round"
              style={{
                filter: "drop-shadow(0px 2px 4px rgba(16, 185, 129, 0.45))"
              }}
            />
          ))}
        </svg>

        <div className="match-pair-column" aria-label="Left items" style={{ zIndex: 10 }}>
          {leftCards.map((card) => {
            const isMatched = Boolean(matchedIds[card.id]);
            const isSelected = selectedLeftId === card.id;
            const isWrong = wrongLeftId === card.id;
            return (
              <button
                type="button"
                id={`match-left-${setIndex}-${card.id}`}
                key={`L-${card.id}`}
                className={`match-pair-card select-card ${isMatched ? "matched" : ""} ${isSelected ? "selected" : ""} ${isWrong ? "wrong" : ""}`.trim()}
                onClick={() => handleLeftCardClick(card.id)}
                disabled={isMatched}
                aria-disabled={isMatched ? "true" : "false"}
              >
                <div className="match-pair-card-text">{card.text}</div>
                {isMatched && <div className="match-pair-card-badge">Matched</div>}
              </button>
            );
          })}
        </div>

        <div className="match-pair-column" aria-label="Right items" style={{ zIndex: 10 }}>
          {rightCards.map((card) => {
            const isMatched = Boolean(matchedIds[card.id]);
            const isSelected = selectedRightId === card.id;
            const isWrong = wrongRightId === card.id;
            return (
              <button
                type="button"
                id={`match-right-${setIndex}-${card.id}`}
                key={`R-${card.id}`}
                className={`match-pair-card select-card ${isMatched ? "matched" : ""} ${isSelected ? "selected" : ""} ${isWrong ? "wrong" : ""}`.trim()}
                onClick={() => handleRightCardClick(card.id)}
                disabled={isMatched}
                aria-disabled={isMatched ? "true" : "false"}
              >
                <div className="match-pair-card-text">{card.text}</div>
                {isMatched && <div className="match-pair-card-badge success">✓ {leftLabel(card.id)}</div>}
              </button>
            );
          })}
        </div>
      </div>
    </section>
  );
}

function MatchThePairSection({ sets }) {
  const normalized = useMemo(() => {
    const safeSets = Array.isArray(sets) ? sets : [];
    return safeSets.slice(0, 5).map((rawSet, index) => ({
      index,
      title: String(rawSet?.title || "").trim(),
      pairs: normalizePairs(rawSet),
    }));
  }, [sets]);

  const hasAny = normalized.some((set) => set.pairs.length > 0);
  if (!hasAny) {
    return (
      <section className="result-section">
        <h3>Match the Pair</h3>
        <p className="topic-empty-text">No match-the-pair sets returned from the server.</p>
      </section>
    );
  }

  return (
    <div className="match-pair-all">
      {normalized.map((set) => (
        <MatchThePairSet
          key={`set-${set.index}`}
          title={set.title || `Set ${set.index + 1}`}
          pairs={set.pairs}
          setIndex={set.index}
        />
      ))}
    </div>
  );
}

export default MatchThePairSection;
