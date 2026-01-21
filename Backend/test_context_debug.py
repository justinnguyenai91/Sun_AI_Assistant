import asyncio
import httpx

async def test():
    headers = {'Authorization': 'Bearer dev-key-123'}
    
    print('=== Query 1: Save context ===')
    r1 = await httpx.AsyncClient().post('http://localhost:9000/analyze', 
        headers=headers,
        json={'input': 'Báo cáo sản lượng FAC01 tháng 1/2026', 'context': {'session_id': 'ctx_debug', 'locale': 'vi', 'debug': True}}, 
        timeout=30)
    d1 = r1.json()
    print('Decision filters:', d1.get('decision', {}).get('filters'))
    print('Execution plan entity:', d1.get('debug', {}).get('execution_plan', {}).get('entity'))
    
    await asyncio.sleep(2)
    
    # Check if context was saved
    print('\n=== Check saved context in DB ===')
    import sys
    sys.path.insert(0, '/app')
    from app.planner.context_manager import context_manager
    saved = await context_manager.get_context('ctx_debug')
    print('Saved context:', saved)
    
    print('\n=== Query 2: Use saved context ===')
    r2 = await httpx.AsyncClient().post('http://localhost:9000/analyze',
        headers=headers, 
        json={'input': 'thế còn tháng 11/2025', 'context': {'session_id': 'ctx_debug', 'locale': 'vi'}},
        timeout=30)
    d2 = r2.json()
    print('Decision filters:', d2.get('decision', {}).get('filters'))

asyncio.run(test())
