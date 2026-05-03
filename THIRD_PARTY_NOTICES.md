# Third-Party Notices

This project combines original integration work with open-source software,
public scientific APIs, and a pretrained foundation model.

## Evo2

The backend uses the Evo2 DNA language model package and checkpoints from the
Arc Institute. Evo2 is an external model and library, not authored by this
project.

- Project: https://github.com/ArcInstitute/evo2
- Model checkpoints: https://huggingface.co/arcinstitute
- License and citation requirements should be checked from the official Evo2
  repository and model pages before publication or commercial use.

## Frontend Foundation

The frontend stack is based on Next.js, React, TypeScript, Tailwind CSS, and
shadcn-style UI components. Some UI implementation patterns were adapted from
public MIT-licensed example code for Evo2 variant analysis:

- Original example repository: https://github.com/Andreaswt/variant-analysis-evo2
- Original license: MIT License, Copyright (c) 2025 Andreas Trolle

This repository keeps the application focused on the final minor-project use
case and adds a cleaned Modal backend, CORS support, deployment documentation,
and project-specific documentation.

## Public Data APIs

The application reads biological data from public APIs:

- UCSC Genome Browser API for genome assemblies, chromosomes, and DNA sequence
  windows: https://api.genome.ucsc.edu
- NCBI E-utilities and Clinical Tables APIs for gene and ClinVar variant data:
  https://www.ncbi.nlm.nih.gov/books/NBK25501/

## Infrastructure and Packages

- Modal is used for serverless GPU execution.
- Vercel or a similar Node.js hosting provider can host the frontend.
- Package dependencies are listed in `frontend/package.json` and
  `backend/requirements.txt`.

## Medical Disclaimer

This software is for educational and research demonstration purposes only. It is
not a medical diagnostic tool and should not be used for clinical decision
making.
