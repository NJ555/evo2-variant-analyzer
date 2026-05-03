import os

import modal
from pydantic import BaseModel, field_validator


MODEL_NAME = os.getenv("EVO2_MODEL_NAME", "evo2_7b")
GPU_TYPE = os.getenv("EVO2_GPU_TYPE", "H100")
WINDOW_SIZE = int(os.getenv("EVO2_WINDOW_SIZE", "8192"))
IDLE_TIMEOUT_SECONDS = int(os.getenv("EVO2_IDLE_TIMEOUT", "120"))
MAX_CONTAINERS = int(os.getenv("EVO2_MAX_CONTAINERS", "1"))
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*")

HF_CACHE_PATH = "/root/.cache/huggingface"
hf_cache_volume = modal.Volume.from_name("evo2-hf-cache", create_if_missing=True)

image = (
    modal.Image.from_registry("nvcr.io/nvidia/pytorch:25.04-py3")
    .env({"HF_HOME": HF_CACHE_PATH})
    .pip_install("biopython", "huggingface_hub", "einops==0.8.1", "vtx>=0.0.8")
    .run_commands("pip install --no-deps evo2==0.3.0")
    .pip_install("fastapi[standard]", "pydantic", "requests")
)

app = modal.App("evo2-variant-analyzer", image=image)


class VariantRequest(BaseModel):
    variant_position: int
    alternative: str
    genome: str = "hg38"
    chromosome: str

    @field_validator("alternative")
    @classmethod
    def validate_alternative(cls, value: str) -> str:
        value = value.upper()
        if len(value) != 1 or value not in "ACGT":
            raise ValueError("alternative must be one nucleotide: A, C, G, or T")
        return value

    @field_validator("genome", "chromosome")
    @classmethod
    def validate_non_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("value is required")
        return value


class SequenceMutationRequest(BaseModel):
    reference: str
    position: int
    alternate: str

    @field_validator("reference")
    @classmethod
    def validate_reference(cls, value: str) -> str:
        value = value.upper()
        if not value or any(base not in "ACGT" for base in value):
            raise ValueError("reference must contain only A, C, G, and T")
        if len(value) > WINDOW_SIZE:
            raise ValueError(f"reference cannot exceed {WINDOW_SIZE} bp")
        return value

    @field_validator("alternate")
    @classmethod
    def validate_alternate(cls, value: str) -> str:
        value = value.upper()
        if len(value) != 1 or value not in "ACGT":
            raise ValueError("alternate must be one nucleotide: A, C, G, or T")
        return value


def fetch_genome_window(
    *,
    position: int,
    genome: str,
    chromosome: str,
    window_size: int = WINDOW_SIZE,
) -> tuple[str, int]:
    import requests

    half_window = window_size // 2
    start = max(0, position - 1 - half_window)
    end = position - 1 + half_window + 1

    url = (
        "https://api.genome.ucsc.edu/getData/sequence"
        f"?genome={genome};chrom={chromosome};start={start};end={end}"
    )
    response = requests.get(url, timeout=30)
    response.raise_for_status()

    data = response.json()
    if "dna" not in data:
        raise ValueError(data.get("error", "UCSC did not return a DNA sequence"))

    sequence = data["dna"].upper()
    if any(base not in "ACGT" for base in sequence):
        raise ValueError("UCSC returned a sequence with unsupported bases")
    return sequence, start


def classify_delta_score(delta_score: float) -> dict[str, float | str]:
    threshold = -0.0009178519
    lof_std = 0.0015140239
    func_std = 0.0009016589

    if delta_score < threshold:
        confidence = min(1.0, abs(delta_score - threshold) / lof_std)
        return {
            "prediction": "Likely pathogenic",
            "classification_confidence": float(confidence),
        }

    confidence = min(1.0, abs(delta_score - threshold) / func_std)
    return {
        "prediction": "Likely benign",
        "classification_confidence": float(confidence),
    }


@app.cls(
    gpu=GPU_TYPE,
    volumes={HF_CACHE_PATH: hf_cache_volume},
    max_containers=MAX_CONTAINERS,
    retries=2,
    scaledown_window=IDLE_TIMEOUT_SECONDS,
    timeout=1000,
    startup_timeout=1500,
)
class Evo2Service:
    @modal.enter()
    def load_model(self):
        from evo2 import Evo2

        print(f"Loading Evo2 model: {MODEL_NAME}")
        self.model = Evo2(MODEL_NAME)
        print("Evo2 model loaded")

    def _score_mutation(self, reference: str, position: int, alternate: str) -> float:
        if not (0 <= position < len(reference)):
            raise ValueError(f"position {position} is outside sequence length {len(reference)}")

        mutated = reference[:position] + alternate + reference[position + 1 :]
        reference_score, mutated_score = self.model.score_sequences([reference, mutated])
        return float(mutated_score - reference_score)

    def _analyze_genomic_variant(self, request: VariantRequest) -> dict:
        window_seq, seq_start = fetch_genome_window(
            position=request.variant_position,
            genome=request.genome,
            chromosome=request.chromosome,
        )
        relative_pos = request.variant_position - 1 - seq_start
        if not (0 <= relative_pos < len(window_seq)):
            raise ValueError(
                f"variant_position {request.variant_position} is outside the fetched window"
            )

        reference = window_seq[relative_pos]
        delta_score = self._score_mutation(window_seq, relative_pos, request.alternative)
        result = {
            "reference": reference,
            "alternative": request.alternative,
            "position": request.variant_position,
            "genome": request.genome,
            "chromosome": request.chromosome,
            "delta_score": delta_score,
        }
        result.update(classify_delta_score(delta_score))
        return result

    @modal.asgi_app()
    def web(self):
        from fastapi import Body, FastAPI, HTTPException, Query
        from fastapi.middleware.cors import CORSMiddleware

        api = FastAPI(title="Evo2 Variant Analyzer API", version="1.0.0")
        api.add_middleware(
            CORSMiddleware,
            allow_origins=["*"] if CORS_ORIGINS == "*" else CORS_ORIGINS.split(","),
            allow_methods=["*"],
            allow_headers=["*"],
        )

        @api.get("/")
        def root():
            return {"status": "ok", "model": MODEL_NAME}

        @api.get("/health")
        def health():
            return {"status": "ok", "loaded": True, "model": MODEL_NAME}

        def parse_variant_request(
            request: VariantRequest | None,
            variant_position: int | None,
            alternative: str | None,
            genome: str | None,
            chromosome: str | None,
        ) -> VariantRequest:
            if request is not None:
                return request
            missing = [
                name
                for name, value in {
                    "variant_position": variant_position,
                    "alternative": alternative,
                    "chromosome": chromosome,
                }.items()
                if value is None
            ]
            if missing:
                raise HTTPException(
                    status_code=422,
                    detail=f"Missing query parameter(s): {', '.join(missing)}",
                )
            return VariantRequest(
                variant_position=variant_position,
                alternative=alternative,
                genome=genome or "hg38",
                chromosome=chromosome,
            )

        @api.post("/")
        def analyze_from_root(
            request: VariantRequest | None = Body(default=None),
            variant_position: int | None = Query(default=None),
            alternative: str | None = Query(default=None),
            genome: str | None = Query(default=None),
            chromosome: str | None = Query(default=None),
        ):
            parsed = parse_variant_request(
                request, variant_position, alternative, genome, chromosome
            )
            return self._handle_genomic_request(parsed)

        @api.post("/analyze_single_variant")
        def analyze_single_variant(
            request: VariantRequest | None = Body(default=None),
            variant_position: int | None = Query(default=None),
            alternative: str | None = Query(default=None),
            genome: str | None = Query(default=None),
            chromosome: str | None = Query(default=None),
        ):
            parsed = parse_variant_request(
                request, variant_position, alternative, genome, chromosome
            )
            return self._handle_genomic_request(parsed)

        @api.post("/analyze")
        def analyze_sequence_mutation(request: SequenceMutationRequest):
            try:
                delta_score = self._score_mutation(
                    request.reference,
                    request.position,
                    request.alternate,
                )
                result = {
                    "reference": request.reference[request.position],
                    "alternative": request.alternate,
                    "position": request.position,
                    "delta_score": delta_score,
                }
                result.update(classify_delta_score(delta_score))
                return result
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc

        return api

    def _handle_genomic_request(self, request: VariantRequest):
        from fastapi import HTTPException

        try:
            return self._analyze_genomic_variant(request)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @modal.method()
    def smoke_test(self):
        delta_score = self._score_mutation("ACGTACGTACGT", 2, "T")
        result = {
            "reference": "G",
            "alternative": "T",
            "position": 2,
            "delta_score": delta_score,
        }
        result.update(classify_delta_score(delta_score))
        return result


@app.local_entrypoint()
def main():
    service = Evo2Service()
    print(f"Config: model={MODEL_NAME} gpu={GPU_TYPE}")
    print(service.smoke_test.remote())
