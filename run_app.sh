#!/bin/bash

echo "╔══════════════════════════════════════════════╗"
echo "║        Legal Research Tool is Running!        ║"
echo "╚══════════════════════════════════════════════╝"
echo ""
echo "✅ Services Status:"
echo ""

# Check API
if curl -s http://localhost:8000 > /dev/null; then
    echo "📡 API Server: http://localhost:8000 ✓"
    echo "   API Docs: http://localhost:8000/docs"
else
    echo "❌ API Server not running"
    echo "   Run: python3 backend/simple_api.py"
fi

echo ""

# Check Frontend
if curl -s -I http://localhost:3000 > /dev/null; then
    echo "🎨 Frontend: http://localhost:3000 ✓"
else
    echo "❌ Frontend not running"
    echo "   Run: cd frontend && npm run dev"
fi

echo ""
echo "📚 Database contains:"
python3 -c "
import asyncpg
import asyncio
async def check():
    conn = await asyncpg.connect('postgresql://legal_user:legal_pass@localhost:5432/legal_research')
    cases = await conn.fetchval('SELECT COUNT(*) FROM cases')
    courts = await conn.fetchval('SELECT COUNT(*) FROM courts')
    print(f'   • {cases} cases')
    print(f'   • {courts} courts')
    await conn.close()
asyncio.run(check())
" 2>/dev/null || echo "   Database not accessible"

echo ""
echo "🚀 Open http://localhost:3000 in your browser to start searching!"
echo ""
echo "Try searching for:"
echo "   • personal jurisdiction"
echo "   • constitutional law"
echo "   • summary judgment"
echo ""