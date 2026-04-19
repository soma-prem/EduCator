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
  const [draggingId, setDraggingId] = useState(null);
  const [activeDropId, setActiveDropId] = useState(null);
  const [wrongDropId, setWrongDropId] = useState(null);
  const wrongDropTimerRef = useRef(null);

  useEffect(() => {
    const nextLeft = pairs.map((pair) => ({ id: pair.id, text: pair.left }));
    const nextRight = pairs.map((pair) => ({ id: pair.id, text: pair.right }));
    setLeftCards(shuffle(nextLeft));
    setRightCards(shuffle(nextRight));
    setMatchedIds({});
    setDraggingId(null);
    setActiveDropId(null);
    setWrongDropId(null);
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

  const onDragStartLeft = (event, id) => {
    try {
      event.dataTransfer.setData("text/plain", String(id));
      event.dataTransfer.effectAllowed = "move";
    } catch (_error) {}
    setDraggingId(id);
  };

  const onDragEndLeft = () => {
    setDraggingId(null);
    setActiveDropId(null);
  };

  const onDragOverRight = (event, rightId) => {
    event.preventDefault();
    if (matchedIds[rightId]) return;
    setActiveDropId(rightId);
    try {
      event.dataTransfer.dropEffect = "move";
    } catch (_error) {}
  };

  const onDragLeaveRight = (_event, rightId) => {
    if (activeDropId === rightId) {
      setActiveDropId(null);
    }
  };

  const onDropRight = (event, rightId) => {
    event.preventDefault();
    setActiveDropId(null);
    if (matchedIds[rightId]) return;

    const raw = event.dataTransfer?.getData?.("text/plain");
    const leftId = Number(raw);
    if (!Number.isFinite(leftId)) return;

    if (leftId === rightId) {
      setMatchedIds((prev) => ({ ...prev, [rightId]: true }));
      return;
    }

    setWrongDropId(rightId);
    if (wrongDropTimerRef.current) {
      clearTimeout(wrongDropTimerRef.current);
    }
    wrongDropTimerRef.current = setTimeout(() => {
      setWrongDropId(null);
      wrongDropTimerRef.current = null;
    }, 550);
  };

  const leftLabel = (id) => pairs.find((p) => p.id === id)?.left || "";

  return (
    <section className="result-section match-pair-set">
      <div className="match-pair-set-header">
        <div>
          <h3>
            {title || `Set ${setIndex + 1}`}
          </h3>
          <p className="match-pair-subtitle">
            Drag a left card onto its matching right card. ({matchedCount}/{totalCount})
          </p>
        </div>
        <div className="match-pair-controls">
          <button
            type="button"
            className="ghost-btn"
            onClick={() => {
              const nextLeft = pairs.map((pair) => ({ id: pair.id, text: pair.left }));
              const nextRight = pairs.map((pair) => ({ id: pair.id, text: pair.right }));
              setLeftCards(shuffle(nextLeft));
              setRightCards(shuffle(nextRight));
              setMatchedIds({});
              setDraggingId(null);
              setActiveDropId(null);
              setWrongDropId(null);
            }}
          >
            Reset
          </button>
        </div>
      </div>

      {isComplete && <div className="match-pair-complete">All pairs matched.</div>}

      <div className="match-pair-board" role="group" aria-label={`Match the Pair set ${setIndex + 1}`}>
        <div className="match-pair-column" aria-label="Left items">
          {leftCards.map((card) => {
            const isMatched = Boolean(matchedIds[card.id]);
            const isDragging = draggingId === card.id;
            return (
              <div
                key={`L-${card.id}`}
                className={`match-pair-card draggable ${isMatched ? "matched" : ""} ${isDragging ? "dragging" : ""}`.trim()}
                draggable={!isMatched}
                onDragStart={(event) => onDragStartLeft(event, card.id)}
                onDragEnd={onDragEndLeft}
                aria-disabled={isMatched ? "true" : "false"}
              >
                <div className="match-pair-card-text">{card.text}</div>
                {isMatched && <div className="match-pair-card-badge">Matched</div>}
              </div>
            );
          })}
        </div>

        <div className="match-pair-column" aria-label="Right items">
          {rightCards.map((card) => {
            const isMatched = Boolean(matchedIds[card.id]);
            const isActive = activeDropId === card.id && !isMatched;
            const isWrong = wrongDropId === card.id && !isMatched;
            return (
              <div
                key={`R-${card.id}`}
                className={`match-pair-card droppable ${isMatched ? "matched" : ""} ${isActive ? "active" : ""} ${
                  isWrong ? "wrong" : ""
                }`.trim()}
                onDragOver={(event) => onDragOverRight(event, card.id)}
                onDragLeave={(event) => onDragLeaveRight(event, card.id)}
                onDrop={(event) => onDropRight(event, card.id)}
                role="button"
                tabIndex={0}
                aria-label={isMatched ? `Matched: ${card.text}` : `Drop match for: ${card.text}`}
              >
                <div className="match-pair-card-text">{card.text}</div>
                {isMatched && <div className="match-pair-card-badge success">✓ {leftLabel(card.id)}</div>}
                {!isMatched && <div className="match-pair-card-hint">Drop here</div>}
              </div>
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
