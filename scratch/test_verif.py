import sys, json
sys.path.insert(0, r'C:/Users/HP/OneDrive/Desktop/V 6')
from app import app
with app.test_client() as c:
    r = c.get('/api/verification-db')
    print('Status', r.status_code)
    try:
        data = json.loads(r.data)
        print('Success', data.get('success'))
        print('Count', data.get('count'))
    except Exception as e:
        print('Error parsing JSON', e)

