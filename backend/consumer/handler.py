"""
NewsFlow Consumer Lambda
Reads articles from S3 (pipeline/articles-*.json written by scraper)
→ Embed (SBERT) → Cluster (DBSCAN) → Score → Summarize (DistilBART)
→ Quality Gate → DynamoDB → CloudWatch metrics

Single invocation processes ALL articles at once — guarantees one DBSCAN run,
no duplicate clusters across containers.
"""
import json, os, re, math, time, gc, tarfile, boto3
import numpy as np
from datetime import datetime, timezone
from collections import defaultdict, Counter
from itertools import combinations

# ── Environment variables (set in Lambda console) ──────────────────────────
MODEL_BUCKET    = os.environ.get('MODEL_BUCKET', '')
PIPELINE_BUCKET = os.environ.get('PIPELINE_BUCKET', '')
TABLE_ARTICLES  = os.environ.get('TABLE_ARTICLES', 'nf-articles')
TABLE_CLUSTERS  = os.environ.get('TABLE_CLUSTERS', 'nf-clusters')
TABLE_SUMMARIES = os.environ.get('TABLE_SUMMARIES', 'nf-summaries')

# ── AWS clients ────────────────────────────────────────────────────────────
dynamodb = boto3.resource('dynamodb')
s3       = boto3.client('s3')
cw       = boto3.client('cloudwatch')

# ── Pipeline parameters (exact values from notebook) ──────────────────────
DBSCAN_EPS         = 0.45   # cosine distance threshold — 0.45 = similarity >= 0.55
                             # 0.35 was too strict with full 3600+ article batches,
                             # producing only ~50 clusters instead of 200+
DBSCAN_MIN_SAMPLES = 2
MAX_SRC_PER_CLUSTER= 3   # top-authority sources used for summarization prompt

HALF_LIVES = {
    'World Politics': 6, 'Sports': 6,
    'Technology': 12,    'Business': 12,
    'Health': 24,        'Environment': 24,
    'Science': 48,       'Entertainment': 12,
}

REFUSAL_PHRASES = ['i cannot', "i can't", 'as an ai', "i'm sorry", 'i am unable']

# ── Module-level model cache (survives warm invocations) ──────────────────
_sbert  = None
_tok    = None
_bart   = None


def _download_model(name):
    local_dir = f'/tmp/{name}'
    tar_path  = f'/tmp/{name}.tar.gz'
    if not os.path.exists(local_dir):
        os.makedirs(local_dir, exist_ok=True)
        print(f'[COLD START] downloading {name} from s3://{MODEL_BUCKET}/models/{name}.tar.gz')
        s3.download_file(MODEL_BUCKET, f'models/{name}.tar.gz', tar_path)
        with tarfile.open(tar_path) as tf:
            tf.extractall(local_dir)
        os.remove(tar_path)
        print(f'[COLD START] {name} ready')
    return local_dir

def _load_models():
    global _sbert, _tok, _bart
    # Check ALL three — a partial cold-start failure leaves _sbert set but _tok None
    if _sbert is not None and _tok is not None and _bart is not None:
        return
    from sentence_transformers import SentenceTransformer
    from transformers import BartForConditionalGeneration, AutoTokenizer

    sbert_dir = _download_model('sbert')
    bart_dir  = _download_model('distilbart')

    _sbert = SentenceTransformer(sbert_dir)
    # AutoTokenizer handles RobertaTokenizer saved inside distilbart correctly
    _tok   = AutoTokenizer.from_pretrained(bart_dir)
    # Load in float16 — halves BART memory footprint from ~580 MB to ~290 MB
    # CPU inference in float16 is supported and produces identical quality output
    import torch
    _bart  = BartForConditionalGeneration.from_pretrained(bart_dir, torch_dtype=torch.float16)
    print('[INFO] Models loaded and cached')


# ── Helpers ────────────────────────────────────────────────────────────────

def get_recency(newest_str, topic):
    try:
        newest = datetime.fromisoformat(newest_str)
        if newest.tzinfo is None:
            newest = newest.replace(tzinfo=timezone.utc)
    except Exception:
        return 0.5
    age_h = (datetime.now(timezone.utc) - newest).total_seconds() / 3600
    hl    = HALF_LIVES.get(topic, 12)
    return math.exp(-0.693 * age_h / hl)


def score_cluster(centroid, sources, newest_str, topic, topic_centroids):
    """0.50*relevance + 0.25*authority + 0.25*recency  (from notebook)"""
    best_rel = 0.0
    for tc in topic_centroids.values():
        rel = float(np.dot(centroid, tc))
        if rel > best_rel:
            best_rel = rel
    auth = max((a.get('authority', 0.5) for a in sources), default=0.5)
    rec  = get_recency(newest_str, topic)
    return 0.50 * best_rel + 0.25 * auth + 0.25 * rec, best_rel, auth, rec


def generate_summary(articles):
    """Build multi-source prompt and run DistilBART (exact notebook logic)"""
    import torch
    arts   = sorted(articles, key=lambda a: a.get('authority', 0.5), reverse=True)[:MAX_SRC_PER_CLUSTER]
    prompt = ' '.join(f"{a['title']}. {a['summary'][:200]}" for a in arts)
    inputs = _tok(prompt, return_tensors='pt', max_length=512, truncation=True)
    with torch.no_grad():   # no gradient storage — saves ~50-100 MB RAM
        out = _bart.generate(
            **inputs, max_new_tokens=120, min_length=40,
            num_beams=2, early_stopping=True,
            length_penalty=1.5, no_repeat_ngram_size=3
        )
    return _tok.decode(out[0], skip_special_tokens=True)


def quality_gate(summary, source_articles):
    """Length + refusal + named-entity faithfulness (exact notebook logic)"""
    words = summary.split()
    if len(words) < 20:
        return False, f'too_short ({len(words)} words)'
    if len(words) > 200:
        return False, f'too_long ({len(words)} words)'
    lower = summary.lower()
    for phrase in REFUSAL_PHRASES:
        if phrase in lower:
            return False, f'refusal: {phrase}'
    # Named-entity faithfulness
    src_text = ' '.join(a['title'] + ' ' + a['summary'] for a in source_articles).lower()
    entities = {w.strip('.,;:\'"()[]').lower()
                for i, w in enumerate(summary.split())
                if w and w[0].isupper() and i > 0 and len(w.strip('.,;:\'"()[]')) > 1}
    if entities:
        faithful = {e for e in entities if e in src_text}
        score    = len(faithful) / len(entities)
        if score < 0.80:
            return False, f'low_faithfulness={score:.2f}'
    return True, 'ok'


# ── Main handler ───────────────────────────────────────────────────────────

def _clear_todays_summaries():
    """
    Delete only today's summaries from nf-summaries before writing fresh ones.
    Preserves all historical data from previous days so the date filter works.
    """
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    print(f'[INFO] Clearing existing summaries for {today}...')

    tbl = dynamodb.Table(TABLE_SUMMARIES)

    # Scan for all items — only fetch the two fields we need
    result = tbl.scan(ProjectionExpression='cluster_id, generated_at')
    items  = result.get('Items', [])
    while 'LastEvaluatedKey' in result:
        result = tbl.scan(
            ProjectionExpression='cluster_id, generated_at',
            ExclusiveStartKey=result['LastEvaluatedKey']
        )
        items.extend(result.get('Items', []))

    # Filter to only today's entries
    todays_ids = [
        item['cluster_id'] for item in items
        if item.get('generated_at', '')[:10] == today
    ]

    if not todays_ids:
        print(f'[INFO] No existing summaries found for {today} — clean slate')
        return

    # Batch delete (DynamoDB batch_writer handles 25-item batches automatically)
    with tbl.batch_writer() as batch:
        for cluster_id in todays_ids:
            batch.delete_item(Key={'cluster_id': cluster_id})

    print(f'[INFO] Cleared {len(todays_ids)} summaries for {today}')


def lambda_handler(event, context):
    _load_models()

    from sklearn.cluster import DBSCAN
    from sklearn.metrics import silhouette_score

    # ── Read articles from S3 (triggered by scraper writing pipeline/articles-*.json) ──
    raw = []
    try:
        record     = event['Records'][0]
        bucket     = record['s3']['bucket']['name']
        key        = record['s3']['object']['key']
        print(f'[INFO] Reading articles from s3://{bucket}/{key}')
        resp       = s3.get_object(Bucket=bucket, Key=key)
        data       = json.loads(resp['Body'].read().decode('utf-8'))
        raw        = data.get('articles', [])
        print(f'[INFO] Loaded {len(raw)} articles from S3')
    except Exception as e:
        print(f'[ERROR] Could not read S3 object: {e}')
        return {'status': 'error', 'reason': str(e)}

    if not raw:
        return {'status': 'no_records'}

    # Clear today's existing summaries BEFORE writing new ones.
    # This prevents duplicate clusters from multiple pipeline runs on the same day
    # while preserving all historical data from previous days.
    _clear_todays_summaries()

    articles = raw  # already cleaned by scraper

    # ── Embed ──────────────────────────────────────────────────────────────
    texts      = [a['text'] for a in articles]
    embeddings = _sbert.encode(texts, batch_size=64,
                               normalize_embeddings=True, show_progress_bar=False)

    # ── Cluster ────────────────────────────────────────────────────────────
    labels = DBSCAN(eps=DBSCAN_EPS, min_samples=DBSCAN_MIN_SAMPLES,
                    metric='cosine').fit_predict(embeddings)

    cluster_map = defaultdict(list)
    for idx, label in enumerate(labels):
        cluster_map[label].append(idx)

    # Silhouette (on non-singleton articles only)
    mask = labels != -1
    sil  = 0.0
    if mask.sum() > DBSCAN_MIN_SAMPLES and len(set(labels[mask])) > 1:
        try:
            sil = float(silhouette_score(embeddings[mask], labels[mask], metric='cosine'))
        except Exception:
            pass

    # ── Build topic centroids ──────────────────────────────────────────────
    topic_embs = defaultdict(list)
    for i, a in enumerate(articles):
        topic_embs[a['topic']].append(embeddings[i])
    topic_centroids = {}
    for topic, embs in topic_embs.items():
        c = np.array(embs).mean(axis=0)
        topic_centroids[topic] = c / (np.linalg.norm(c) + 1e-9)

    # Pre-compute per-cluster embeddings BEFORE freeing the main array
    # The loop needs these for centroid and cohesion calculations
    cluster_embs = {
        label: embeddings[idxs]
        for label, idxs in cluster_map.items()
        if label != -1
    }

    # Now safe to free the full embeddings array (~107 MB)
    del embeddings, topic_embs
    gc.collect()
    print('[INFO] Embeddings freed — starting summarisation')

    # ── Score, summarize, quality-gate, store ──────────────────────────────
    tbl_clusters  = dynamodb.Table(TABLE_CLUSTERS)
    tbl_summaries = dynamodb.Table(TABLE_SUMMARIES)

    n_pass = 0
    n_fail = 0
    latencies = []
    cohesion_all = []

    real_labels = [l for l in set(labels) if l != -1]
    summary_items = []
    cluster_items = []

    for label in real_labels:
        idxs  = cluster_map[label]
        arts  = [articles[i] for i in idxs]
        embs  = cluster_embs[label]   # use pre-computed cluster embeddings

        # Centroid
        c = embs.mean(axis=0)
        c = c / (np.linalg.norm(c) + 1e-9)

        # Cohesion
        if len(idxs) >= 2:
            sims = [float(np.dot(embs[i], embs[j]))
                    for i, j in combinations(range(len(embs)), 2)]
            cohesion_all.append(float(np.mean(sims)))

        # Topic — majority vote across all articles in the cluster
        topic    = Counter(a['topic'] for a in arts).most_common(1)[0][0]
        newest   = max(a['published'] for a in arts)
        sc, rel, auth, rec = score_cluster(c, arts, newest, topic, topic_centroids)

        # Skip very low-scoring clusters — saves DistilBART time on noise events
        if sc < 0.45:
            continue

        # Summarize
        t0      = time.time()
        summary = generate_summary(arts)
        lat     = time.time() - t0
        latencies.append(lat)

        # Quality gate
        passed, reason = quality_gate(summary, arts)
        if passed:
            n_pass += 1
        else:
            n_fail += 1

        cluster_id = f'cluster_{label}_{datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")}'

        # Best source — highest authority article, used for "open original" link
        top_art          = sorted(arts, key=lambda a: a.get('authority', 0), reverse=True)[0]
        top_source_url   = top_art.get('article_url', '')
        top_source_title = top_art.get('title', '')
        top_source_name  = top_art.get('source', '')

        summary_items.append({
            'cluster_id':       cluster_id,
            'summary':          summary,
            'score':            str(round(sc, 4)),
            'relevance':        str(round(rel, 4)),
            'authority':        str(round(auth, 4)),
            'recency':          str(round(rec, 4)),
            'topic':            topic,
            'article_count':    len(arts),
            'sources':          list({a['source'] for a in arts}),
            'passed_gate':      passed,
            'gate_reason':      reason,
            'generated_at':     datetime.now(timezone.utc).isoformat(),
            'top_source_url':   top_source_url,
            'top_source_title': top_source_title,
            'top_source_name':  top_source_name,
        })

        cluster_items.append({
            'cluster_id':    cluster_id,
            'score':         str(round(sc, 4)),
            'article_count': len(arts),
            'topic':         topic,
            'cohesion':      str(round(cohesion_all[-1] if cohesion_all else 0, 4)),
        })

    # ── Batch write to DynamoDB (much faster than individual put_item) ─────
    print(f'[INFO] Writing {len(summary_items)} summaries to DynamoDB...')
    with tbl_summaries.batch_writer() as batch:
        for item in summary_items:
            batch.put_item(Item=item)

    with tbl_clusters.batch_writer() as batch:
        for item in cluster_items:
            batch.put_item(Item=item)

    print('[INFO] DynamoDB writes complete')

    # ── Publish CloudWatch metrics ─────────────────────────────────────────
    total_summ = n_pass + n_fail
    qg_rate    = n_pass / max(total_summ, 1)
    mean_coh   = float(np.mean(cohesion_all)) if cohesion_all else 0.0
    mean_lat   = float(np.mean(latencies))    if latencies    else 0.0

    cw.put_metric_data(Namespace='NewsFlow', MetricData=[
        {'MetricName': 'ClustersFormed',         'Value': len(real_labels), 'Unit': 'Count'},
        {'MetricName': 'SummariesGenerated',      'Value': total_summ,       'Unit': 'Count'},
        {'MetricName': 'QualityGatePassRate',     'Value': qg_rate,          'Unit': 'None'},
        {'MetricName': 'SilhouetteScore',         'Value': sil,              'Unit': 'None'},
        {'MetricName': 'MeanCohesion',            'Value': mean_coh,         'Unit': 'None'},
        {'MetricName': 'MeanDistilBARTLatency',   'Value': mean_lat,         'Unit': 'Seconds'},
    ])

    print(f'[OK] {len(articles)} articles → {len(real_labels)} clusters → '
          f'{n_pass} summaries passed | sil={sil:.3f} | qg={qg_rate:.1%}')
    return {'status': 'ok', 'clusters': len(real_labels), 'passed': n_pass, 'failed': n_fail}