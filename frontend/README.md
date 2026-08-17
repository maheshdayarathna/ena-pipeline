# ENA Biomarker — Frontend

A small React (Vite, JavaScript) single-page app that uploads a fish blood
smear image to the FastAPI backend and displays the three-way ENA biomarker
result.

## Requirements

- Node.js (18+)
- The backend running at `http://127.0.0.1:8000` (see `../backend`)

## Install

```bash
npm install
```

## Run

```bash
npm run dev
```

This starts the Vite dev server (default `http://localhost:5173`). Make sure
the backend is running first — start it from `backend/` with:

```bash
uvicorn main:app --reload
```

## How it works

1. **Upload** (`components/UploadSection.jsx`) — pick or drop one image,
   preview it, then click "Analyze".
2. `src/api.js` sends the file to `POST /analyze` on the backend as
   `multipart/form-data` and returns the parsed JSON.
3. `App.jsx` stores the response (`{ biomarker, meta }`) in state and passes
   it down to the result sections:
   - `PrimarySection` — biomarker A (observed cells only), the primary result.
   - `ReconstructionSection` — biomarkers C and B, plus a bar chart comparing
     A/B/C.
   - `BreakdownSection` — per-source cell counts (single, watershed_whole,
     inpainted).
4. If `meta.note` contains `"SYNTHETIC"` (true while the backend uses its
   mock pipeline), an amber banner reminds you the numbers aren't from a real
   model yet. It disappears automatically once the backend is swapped to a
   real pipeline.

## Folder structure

```
src/
  api.js               API_BASE constant + analyzeImage() fetch call
  format.js            number formatting helpers (rounding, thousands separators)
  App.jsx              top-level state (result / loading / error) and layout
  index.css            all styling for the app, in one file
  components/
    Header.jsx
    SyntheticBanner.jsx
    UploadSection.jsx       Section 1: file picker/drop zone + preview
    PrimarySection.jsx      Section 2: biomarker A card
    ReconstructionSection.jsx  Section 3: biomarker C/B cards + chart
    BreakdownSection.jsx    Section 4: per-source tables
    BiomarkerCard.jsx       reusable card for A/B/C
    ComparisonChart.jsx     hand-drawn bar chart (no charting library)
    BreakdownTable.jsx      reusable source-breakdown table
```
