import { API_BASE } from "../../config/api";

function buildSourceFormData(source, tool, difficulty = "medium", count = 12, options = {}) {
  const formData = new FormData();
  const normalizedTool = String(tool || "").trim();
  if (!normalizedTool) {
    return null;
  }
  formData.append("tool", normalizedTool);
  formData.append("difficulty", String(difficulty || "medium"));
  formData.append("count", String(count || 12));
  if (options?.includeImages) {
    formData.append("includeImages", "1");
  }

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
    return hasAny ? formData : null;
  }

  if (source?.mode === "file" && source?.fileId) {
    formData.append("fileId", source.fileId);
    return formData;
  }
  if (source?.mode === "file" && source?.file instanceof File) {
    formData.append("file", source.file);
    return formData;
  }
  if (source?.mode === "text" && source?.text) {
    formData.append("text", source.text);
    return formData;
  }
  return null;
}

async function generateWithTool({ tool, source, difficulty = "medium", count = 12, includeImages = false, authToken = "" }) {
  const formData = buildSourceFormData(source, tool, difficulty, count, { includeImages });
  if (!formData) {
    throw new Error("Source missing. Provide text or file.");
  }
  const headers = authToken ? { Authorization: `Bearer ${authToken}` } : undefined;
  const response = await fetch(`${API_BASE}/api/tools/generate`, { method: "POST", body: formData, headers });
  const rawText = await response.text();
  let data = {};
  try {
    data = rawText ? JSON.parse(rawText) : {};
  } catch (_error) {
    data = {};
  }
  if (!response.ok) {
    throw new Error(data?.error || rawText || "Tool generation failed");
  }
  return data;
}

export { buildSourceFormData };
export default generateWithTool;
