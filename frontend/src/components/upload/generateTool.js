import { callClaude } from "../../utils/callClaude";

function buildSourceFormData(source, tool, difficulty = "medium", count = 12, options = {}) {
  const formData = new FormData();
  const normalizedTool = String(tool || "").trim();
  if (!normalizedTool) {
    return null;
  }
  formData.append("tool", normalizedTool);
  formData.append("difficulty", String(difficulty || "medium"));
  formData.append("count", String(count || 12));

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

async function generateWithTool({ tool, source, difficulty = "medium", count = 12, authToken = "" }) {
  return callClaude(tool, source, { difficulty, count, authToken });
}

export { buildSourceFormData };
export default generateWithTool;
