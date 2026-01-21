import asyncio
import httpx

async def test():
    headers = {'Authorization': 'Bearer dev-key-123'}
    
    print('=== Query with debug=True ===')
    r1 = await httpx.AsyncClient().post('http://localhost:9000/analyze', 
        headers=headers,
        json={'input': 'Báo cáo sản lượng FAC01 tháng 1/2026', 'context': {'session_id': 'ctx_keys', 'locale': 'vi', 'debug': True}}, 
        timeout=30)
    d1 = r1.json()
    
    print('\nResponse keys:', list(d1.keys()))
    print('\nHas _semantic_plan?', '_semantic_plan' in d1)
    print('Has _execution_plan?', '_execution_plan' in d1)
    
    if 'debug' in d1:
        print('\nDebug keys:', list(d1['debug'].keys()))

asyncio.run(test())
