import requests

INFOPARK_ID = '50071072-df8c-4c75-985d-2f93977734ff'
KDHP_ID = '499b2e77-2b44-40ba-9e4c-61cef20919b2'
BASE = 'http://localhost:8000/api'

def approve(aid, name):
    try:
        s = requests.get(f'{BASE}/status/{aid}').json()
        if s.get('status') == 'PENDING_RM_REVIEW':
            print(f'Approving {name}...')
            payload = {'approved_rm_items': s.get('pending_review_data', {}).get('rm_items', [])}
            res = requests.post(f'{BASE}/analyze/continue/{aid}', json=payload)
            print(f'{name} response:', res.status_code)
        else:
            print(f'{name} status is {s.get("status")}')
    except Exception as e:
        print(f'{name} error:', e)

approve(INFOPARK_ID, "Infopark")
approve(KDHP_ID, "KDHP")
