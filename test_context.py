import asyncio
import httpx

async def test():
    headers = {'Authorization': 'Bearer dev-key-123'}
    
    print('Query 1: Báo cáo sản lượng FAC01 tháng 1/2026')
    r1 = await httpx.AsyncClient().post('http://localhost:9000/analyze', 
        headers=headers,
        json={'input': 'Báo cáo sản lượng FAC01 tháng 1/2026', 'context': {'session_id': 'ctx02', 'locale': 'vi'}}, 
        timeout=30)
    d1 = r1.json()
    fc1 = d1.get('decision', {}).get('filters', {}).get('factoryCode')
    print(f'Factory: {fc1}\n')
    
    await asyncio.sleep(1)
    
    print('Query 2 (Follow-up): thế còn tháng 11/2025')
    r2 = await httpx.AsyncClient().post('http://localhost:9000/analyze',
        headers=headers, 
        json={'input': 'thế còn tháng 11/2025', 'context': {'session_id': 'ctx02', 'locale': 'vi'}},
        timeout=30)
    d2 = r2.json()
    fc2 = d2.get('decision', {}).get('filters', {}).get('factoryCode')
    from_date = d2.get('decision', {}).get('from')
    print(f'Factory: {fc2}')
    print(f'From: {from_date}')
    
    if fc2 == 'FAC01':
        print('\n✅✅✅ CONTEXT WORKING! Follow-up inherited FAC01!')
    else:
        print('\n❌ Context not working')

asyncio.run(test())
