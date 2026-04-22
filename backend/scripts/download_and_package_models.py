#!/usr/bin/env python3
"""
Run this ONCE on your local machine before deploying to AWS.
Downloads both models and packages them as tarballs ready for S3 upload.

Usage:
    pip install sentence-transformers transformers torch
    python scripts/download_and_package_models.py
    # Then upload the two .tar.gz files to S3 (instructions in guide)
"""
import os, tarfile
from pathlib import Path

MODELS_DIR = Path('./models')
MODELS_DIR.mkdir(exist_ok=True)

# ── 1. Sentence-BERT ───────────────────────────────────────────────────────
print('Downloading all-mpnet-base-v2 (~420 MB) ...')
from sentence_transformers import SentenceTransformer
sbert_dir = MODELS_DIR / 'sbert'
sbert_dir.mkdir(exist_ok=True)
model = SentenceTransformer('all-mpnet-base-v2')
model.save(str(sbert_dir))

# Sanity check
embs = model.encode(['Artemis II Moon mission launches', 'Stock markets rise'])
print(f'  SBERT embedding shape: {embs.shape}  ✅')

# Package
print('  Packaging sbert.tar.gz ...')
with tarfile.open(MODELS_DIR / 'sbert.tar.gz', 'w:gz') as tf:
    tf.add(sbert_dir, arcname='.')
print(f'  sbert.tar.gz size: {(MODELS_DIR / "sbert.tar.gz").stat().st_size / 1e6:.0f} MB')

# ── 2. DistilBART ─────────────────────────────────────────────────────────
print('\nDownloading sshleifer/distilbart-cnn-6-6 (~300 MB) ...')
from transformers import BartForConditionalGeneration, BartTokenizer
bart_dir = MODELS_DIR / 'distilbart'
bart_dir.mkdir(exist_ok=True)
tok  = BartTokenizer.from_pretrained('sshleifer/distilbart-cnn-6-6')
bart = BartForConditionalGeneration.from_pretrained('sshleifer/distilbart-cnn-6-6')
tok.save_pretrained(str(bart_dir))
bart.save_pretrained(str(bart_dir))

# Sanity check
test = 'NASA Artemis II crew launched to lunar orbit. Crew departed Kennedy Space Center.'
inp  = tok(test, return_tensors='pt', max_length=512, truncation=True)
out  = bart.generate(**inp, max_new_tokens=60, num_beams=2)
print(f'  DistilBART test summary: {tok.decode(out[0], skip_special_tokens=True)}  ✅')

# Package
print('  Packaging distilbart.tar.gz ...')
with tarfile.open(MODELS_DIR / 'distilbart.tar.gz', 'w:gz') as tf:
    tf.add(bart_dir, arcname='.')
print(f'  distilbart.tar.gz size: {(MODELS_DIR / "distilbart.tar.gz").stat().st_size / 1e6:.0f} MB')

print('\n✅ Done. Upload these two files to S3:')
print(f'   {MODELS_DIR}/sbert.tar.gz      → s3://YOUR-BUCKET/models/sbert.tar.gz')
print(f'   {MODELS_DIR}/distilbart.tar.gz → s3://YOUR-BUCKET/models/distilbart.tar.gz')
