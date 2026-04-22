"""
NewsFlow Consumer Lambda
Models are baked into the Docker image at /opt/models — no S3 download.
"""
import json, os, re, math, time, gc, boto3
import numpy as np
from datetime import datetime, timezone
from collections import defaultdict
from itertools import combinations

TABLE_ARTICLES  = os.environ.get('TABLE_ARTICLES',  'nf-articles')
TABLE_CLUSTERS  = os.environ.get('TABLE_CLUSTERS',  'nf-clusters')
TABLE_SUMMARIES = os.environ.get('TABLE_SUMMARIES', 'nf-summaries')

SBERT_PATH      = '/opt/models/sbert'
DISTILBART_PATH = '/opt/models/distilbart'

dynamodb = boto3.resource('dynamodb')
cw       = boto3.client('cloudwatch')

DBSCAN_EPS         = 0.35
DBSCAN_MIN_SAMPLES = 2
MAX_SRC_PER_CLUSTER= 3

HALF_LIVES = {
    'World Politics': 6, 'Sports': 6,
    'Technology': 12,    'Business': 12,
    'Health': 24,        'Environment': 24,
    'Science': 48,       'Entertainment': 12,
}

REFUSAL_PHRASES = ['i cannot', "i can't", 'as an ai', "i'm sorry", 'i am unable']

_sbert = None
_tok   = None
_bart  = None


def _load_models():
    global _sbert, _tok, _bart
    if _sbert is not None:
        return

    os.environ['TRANSFORMERS_CACHE'] = '/tmp/hf_cache'
    os.makedirs('/tmp/hf_cache', exist_ok=True)

    from sentence_transformers import SentenceTransformer
    from transformers import AutoTokenizer, AutoModelForSeq2SeqLM

    print('[INFO] Loading SBERT from image...')
    _sbert = SentenceTransformer(SBERT_PATH)

    print('[INFO] Loading DistilBART from image...')
    _tok  = AutoTokenizer.from_pretrained(DISTILBART_PATH)
    _bart = AutoModelForSeq2SeqLM.from_pretrained(DISTILBART_PATH)
    print('[INFO] Models loaded')


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
    arts   = sorted(articles, key=lambda a: a.get('authority', 0.5), reverse=True)[:MAX_SRC_PER_CLUSTER]
    prompt = ' '.join(f"{a['title']}. {a['summary'][:200]}" for a in arts)
    inputs = _tok(prompt, return_tensors='pt', max_length=512, truncation=True)
    out    = _bart.generate(
        **inputs, max_new_tokens=120, min_length=40,
        num_beams=4, early_stopping=True,
        length_penalty=2.0, no_repeat_ngram_size=3
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

def lambda_handler(event, context):
    _load_models()

    from sklearn.cluster import DBSCAN
    from sklearn.metrics import silhouette_score

    # Collect articles from SQS batch
    raw = []
    for record in event.get('Records', []):
        try:
            raw.append(json.loads(record['body']))
        except Exception:
            pass

    if not raw:
        return {'status': 'no_records'}

    articles = raw  # already cleaned by scraper

    # ── Embed ──────────────────────────────────────────────────────────────
    texts      = [a['text'] for a in articles]
    embeddings = _sbert.encode(texts, batch_size=32,
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

    # ── Score, summarize, quality-gate, store ──────────────────────────────
    tbl_clusters  = dynamodb.Table(TABLE_CLUSTERS)
    tbl_summaries = dynamodb.Table(TABLE_SUMMARIES)

    n_pass = 0
    n_fail = 0
    latencies = []
    cohesion_all = []

    real_labels = [l for l in set(labels) if l != -1]

    for label in real_labels:
        idxs  = cluster_map[label]
        arts  = [articles[i] for i in idxs]
        embs  = embeddings[idxs]

        # Centroid
        c = embs.mean(axis=0)
        c = c / (np.linalg.norm(c) + 1e-9)

        # Cohesion
        if len(idxs) >= 2:
            sims = [float(np.dot(embs[i], embs[j]))
                    for i, j in combinations(range(len(embs)), 2)]
            cohesion_all.append(float(np.mean(sims)))

        # Score
        topic    = arts[0]['topic']
        newest   = max(a['published'] for a in arts)
        sc, rel, auth, rec = score_cluster(c, arts, newest, topic, topic_centroids)

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

        tbl_summaries.put_item(Item={
            'cluster_id':    cluster_id,
            'summary':       summary,
            'score':         str(round(sc, 4)),
            'relevance':     str(round(rel, 4)),
            'authority':     str(round(auth, 4)),
            'recency':       str(round(rec, 4)),
            'topic':         topic,
            'article_count': len(arts),
            'sources':       list({a['source'] for a in arts}),
            'passed_gate':   passed,
            'gate_reason':   reason,
            'generated_at':  datetime.now(timezone.utc).isoformat(),
        })

        tbl_clusters.put_item(Item={
            'cluster_id':    cluster_id,
            'score':         str(round(sc, 4)),
            'article_count': len(arts),
            'topic':         topic,
            'cohesion':      str(round(cohesion_all[-1] if cohesion_all else 0, 4)),
        })

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
