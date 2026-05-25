import { API_BASE } from "../config/api";

const AI_GENERATE_URL = `${API_BASE}/api/ai/generate`;

const SYSTEM_PROMPTS = {
  mcq:
    "You are a quiz generator. Given a topic or text, generate 10 multiple choice questions. Return ONLY a JSON array: [{id, question, options:{A,B,C,D}, correct_answer, explanation}]",
  flashcard:
    "You are a flashcard generator. Given a topic or text, generate 15 flashcards. Return ONLY a JSON array: [{id, front, back, hint}]",
  truefalse:
    "You are a true/false quiz generator. Given a topic, generate 10 true/false questions. Return ONLY a JSON array: [{id, statement, answer:true|false, explanation}]",
  fillblank:
    "You are a fill-in-the-blank generator. Given a topic, generate 10 sentences with one word blanked. Return ONLY a JSON array: [{id, sentence_with_blank (use ___), answer, hint}]",
  summary:
    "You are a summarizer. Return ONLY a JSON object: {title, short_summary, key_points:[5 strings], important_terms:[{term, definition}]}",
  textai:
    "You are a study assistant. Return ONLY a JSON object: {answer, follow_up_questions:[3 strings], related_topics:[3 strings]}",
  matchpair:
    "You are a matching exercise generator. Generate 8 pairs. Return ONLY a JSON array: [{id, left_item, right_item, category}]",
  mocktest:
    "You are a mock test generator. Return ONLY a JSON object: {title, duration_minutes:20, sections:[{type, questions:[...]}]}",
};

const TOOL_BY_TYPE = {
  mcq: "mcq",
  flashcard: "flashcards",
  flashcards: "flashcards",
  truefalse: "true_false",
  true_false: "true_false",
  fillblank: "fill_blanks",
  fill_blanks: "fill_blanks",
  summary: "summary",
  matchpair: "match_the_pair",
  match_the_pair: "match_the_pair",
};

function appendSource(formData, source) {
  if (source?.mode === "multi" && Array.isArray(source?.sources) && source.sources.length > 0) {
    let hasAny = false;
    source.sources.forEach((item) => {
      if (item?.mode === "file" && item?.fileId) {
        formData.append("fileId", item.fileId);
        hasAny = true;
      } else if (item?.mode === "text" && item?.text) {
        formData.append("text", item.text);
        hasAny = true;
      }
    });
    return hasAny;
  }

  if (source?.mode === "file" && source?.fileId) {
    formData.append("fileId", source.fileId);
    return true;
  }
  if (source?.mode === "file" && source?.file instanceof File) {
    formData.append("file", source.file);
    return true;
  }
  if (source?.mode === "text" && source?.text) {
    formData.append("text", source.text);
    return true;
  }
  if (typeof source === "string" && source.trim()) {
    formData.append("text", source.trim());
    return true;
  }
  return false;
}

function buildToolFormData(type, userContent, options) {
  const tool = TOOL_BY_TYPE[type];
  if (!tool) {
    throw new Error(`Unsupported tool type: ${type}`);
  }

  const formData = userContent instanceof FormData ? userContent : new FormData();
  if (!(userContent instanceof FormData) && !appendSource(formData, userContent)) {
    throw new Error("Source missing. Provide text or file.");
  }
  formData.set("tool", tool);
  formData.set("type", type);
  formData.set("difficulty", String(options.difficulty || "medium"));
  formData.set("count", String(options.count || 12));
  return formData;
}

function buildTextAiFormData(userContent, options) {
  const formData = userContent instanceof FormData ? userContent : new FormData();
  if (!(userContent instanceof FormData)) {
    formData.set("question", String(options.question || "").trim());
    formData.set("mode", String(options.mode || "text"));
    if (!appendSource(formData, userContent)) {
      throw new Error("Source missing. Provide text or file.");
    }
  }
  formData.set("type", "textai");
  return formData;
}

function buildMockTestFormData(userContent, options) {
  const formData = userContent instanceof FormData ? userContent : new FormData();
  if (!(userContent instanceof FormData)) {
    formData.set("totalQuestions", String(options.totalQuestions || 20));
    formData.set("durationMinutes", String(options.durationMinutes || 60));
    if (options.file instanceof File) {
      formData.set("file", options.file);
      formData.set("mode", "file");
    }
    if (options.pastFile instanceof File) {
      formData.set("pastFile", options.pastFile);
    }
    if (options.text) {
      formData.set("text", String(options.text));
    }
  }
  formData.set("type", "mocktest");
  return formData;
}

async function parseResponse(response, fallbackMessage) {
  const rawText = await response.text();
  let data = null;
  try {
    data = rawText ? JSON.parse(rawText) : null;
  } catch (_error) {
    data = null;
  }
  if (!response.ok) {
    throw new Error(data?.error || rawText || fallbackMessage);
  }
  return data || {};
}

async function postGenerationRequest(body, headers, fallbackMessage) {
  const response = await fetch(AI_GENERATE_URL, { method: "POST", body, headers });
  return parseResponse(response, fallbackMessage);
}

export async function callClaude(type, userContent, options = {}) {
  const normalizedType = String(type || "").trim().toLowerCase();
  const headers = options.authToken ? { Authorization: `Bearer ${options.authToken}` } : undefined;

  if (normalizedType === "mocktest" || normalizedType === "mock_test") {
    const body = buildMockTestFormData(userContent, options);
    return postGenerationRequest(body, headers, "Failed to generate mock exam");
  }

  if (normalizedType === "textai" || normalizedType === "text_ai") {
    const body = buildTextAiFormData(userContent, options);
    return postGenerationRequest(body, headers, "Failed to answer question");
  }

  const body = buildToolFormData(normalizedType, userContent, options);
  return postGenerationRequest(body, headers, "Tool generation failed");
}

export { SYSTEM_PROMPTS };
