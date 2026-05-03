# Evo2 Variant Analyzer

Developed by **Neeraj Jayaswal (NJ555)** as a B.Tech minor project.

Evo2 Variant Analyzer is a full-stack genomics web application that predicts
the possible effect of single nucleotide variants (SNVs) using the Evo2 DNA
language model. The application lets a user select a genome assembly, browse or
search genes, load gene sequences, submit a variant, and compare the model
prediction with known ClinVar information.

> This project is for learning, research, and demonstration only. It is not a
> medical diagnostic tool.

## Features

- Genome assembly and chromosome browsing through UCSC Genome Browser APIs
- Gene search and gene metadata through NCBI APIs
- Reference DNA sequence loading for selected genomic ranges
- Single nucleotide variant analysis using Evo2 on Modal GPU infrastructure
- Classification-style result: likely benign or likely pathogenic
- Confidence score based on the model delta likelihood
- Known ClinVar variant display and comparison view
- Clean Next.js frontend with reusable TypeScript components
- Serverless FastAPI backend deployed on Modal with H100 GPU support

## Tech Stack

| Layer | Technology |
| --- | --- |
| Frontend | Next.js, React, TypeScript |
| Styling | Tailwind CSS, shadcn-style components, lucide-react icons |
| Backend API | Python, FastAPI, Pydantic |
| AI Model | Evo2 DNA language model |
| GPU Runtime | Modal serverless GPU |
| Public Data | UCSC Genome Browser API, NCBI E-utilities, ClinVar |
| Deployment | Modal for backend, Vercel or any Node.js host for frontend |

## Architecture

```text
User Browser
  |
  | Next.js UI
  v
Frontend App
  |
  | Public genome/gene data
  |-----------------------> UCSC Genome API
  |-----------------------> NCBI / ClinVar APIs
  |
  | Variant request
  v
Modal FastAPI Backend
  |
  | Loads Evo2 on H100 GPU
  v
Evo2 Model
  |
  | Delta likelihood score + prediction
  v
Frontend Result View
```

## Project Structure

```text
evo2-variant-analyzer/
  backend/
    main.py
    modal_app.py
    requirements.txt
    .env.example

  frontend/
    src/
      app/
      components/
      lib/
      styles/
      utils/
    public/
    package.json
    .env.example

  LICENSE
  README.md
  THIRD_PARTY_NOTICES.md
```

## Backend Setup

Install Python 3.11 or 3.12, then from the backend folder:

```bash
cd backend
python -m venv .venv
```

Activate the environment:

```bash
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
# macOS / Linux
source .venv/bin/activate
```

Install dependencies:

```bash
pip install -r requirements.txt
```

Log in to Modal:

```bash
modal setup
```

Run a remote smoke test:

```bash
modal run main.py
```

Deploy the backend:

```bash
modal deploy main.py
```

After deployment, Modal prints a web endpoint like:

```text
https://your-username--evo2-variant-analyzer-evo2service-web.modal.run
```

Use this URL in the frontend `.env.local`.

## Frontend Setup

Install Node.js 20+ and npm, then from the frontend folder:

```bash
cd frontend
npm install
```

Create a local environment file:

```bash
cp .env.example .env.local
```

Set the backend endpoint:

```env
NEXT_PUBLIC_ANALYZE_SINGLE_VARIANT_BASE_URL="https://your-modal-endpoint.modal.run"
```

Run the frontend:

```bash
npm run dev
```

Open:

```text
http://localhost:3000
```

## API Endpoints

### Health Check

```http
GET /health
```

Response:

```json
{
  "status": "ok",
  "loaded": true,
  "model": "evo2_7b"
}
```

### Analyze Genomic Variant

```http
POST /?variant_position=43119628&alternative=G&genome=hg38&chromosome=chr17
```

Response:

```json
{
  "reference": "T",
  "alternative": "G",
  "position": 43119628,
  "genome": "hg38",
  "chromosome": "chr17",
  "delta_score": 0.000097811222076416,
  "prediction": "Likely benign",
  "classification_confidence": 1.0
}
```

## Deployment

### Backend on Modal

1. Create a Modal account.
2. Run `modal setup`.
3. From `backend/`, run `modal deploy main.py`.
4. Copy the generated Modal web URL.
5. Use that URL as `NEXT_PUBLIC_ANALYZE_SINGLE_VARIANT_BASE_URL`.

### Frontend on Vercel

1. Push this repository to GitHub.
2. Import the repository into Vercel.
3. Set the project root to `frontend`.
4. Add environment variable:
   `NEXT_PUBLIC_ANALYZE_SINGLE_VARIANT_BASE_URL=<your Modal URL>`.
5. Deploy.

## Why This Project Matters

Variant interpretation is an important problem in computational biology because
small DNA changes can influence biological function. This project demonstrates
how modern full-stack engineering can be combined with genomics APIs and a
large biological foundation model to create an interactive analysis workflow.

For a B.Tech minor project, it covers multiple useful areas:

- AI/ML model integration
- Cloud GPU deployment
- API design and validation
- Full-stack web development
- Public biological data integration
- Real-world debugging, CORS handling, environment configuration, and deployment

## Limitations

- Evo2 predictions are model-based estimates, not clinical conclusions.
- The confidence score is a simple threshold-based interpretation of delta
  likelihood.
- Public APIs can rate-limit or return incomplete data.
- First Modal requests can be slow because GPU containers scale from zero.

## Attribution

This project uses public APIs, open-source libraries, and the Evo2 model. See
`THIRD_PARTY_NOTICES.md` for details.
