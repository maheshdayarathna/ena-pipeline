// Single place that knows how to talk to the FastAPI backend.
// Change API_BASE if the backend ever runs somewhere else.
export const API_BASE = "http://127.0.0.1:8000";

/**
 * Upload one image to POST /analyze and return the parsed JSON response.
 *
 * Data flow: UploadSection collects a File object from the user -> App calls
 * this function -> we wrap the file in multipart/form-data (field name
 * "file", matching the backend's `UploadFile = File(...)` parameter) -> the
 * backend runs its pipeline and returns { biomarker, meta } -> App stores
 * that in state and passes it down to the results sections as props.
 *
 * useDiffusion is sent as the "use_diffusion" form field (matching the
 * backend's `use_diffusion: bool = Form(False)` parameter) to opt into the
 * slower diffusion-inpainting reconstruction.
 *
 * Throws an Error with a human-readable message on network failure or a
 * non-2xx response, so callers can show it directly to the user.
 */
export async function analyzeImage(file, useDiffusion = false) {
  const formData = new FormData();
  formData.append("file", file);
  formData.append("use_diffusion", useDiffusion ? "true" : "false");

  let response;
  try {
    response = await fetch(`${API_BASE}/analyze`, {
      method: "POST",
      body: formData,
    });
  } catch {
    throw new Error(
      `Could not reach the backend at ${API_BASE}. Is it running?`
    );
  }

  if (!response.ok) {
    let detail = response.statusText;
    try {
      const body = await response.json();
      if (body.detail) detail = body.detail;
    } catch {
      // response wasn't JSON — fall back to statusText
    }
    throw new Error(`Analyze failed (${response.status}): ${detail}`);
  }

  return response.json();
}
