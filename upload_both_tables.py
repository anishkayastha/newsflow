"""
Uploads nf_summaries.json and nf_clusters.json to DynamoDB.
Run: python3 upload_both_tables.py
"""
import json, boto3

REGION   = 'ap-southeast-1'
dynamodb = boto3.resource('dynamodb', region_name=REGION)

def upload(table_name, json_file):
    with open(json_file) as f:
        items = json.load(f)
    print(f'Uploading {len(items)} items to {table_name}...')
    with dynamodb.Table(table_name).batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)
    print(f'✓ {table_name} — {len(items)} items written')
    return len(items)

n1 = upload('nf-summaries', 'nf_summaries.json')
n2 = upload('nf-clusters',  'nf_clusters.json')

print(f'\n✓ Complete — {n1} summaries, {n2} clusters')
print('\nVerify:')
print('  aws dynamodb scan --table-name nf-summaries --region ap-southeast-1 --select COUNT --query Count')
print('  aws dynamodb scan --table-name nf-clusters  --region ap-southeast-1 --select COUNT --query Count')
