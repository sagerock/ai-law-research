#!/usr/bin/env python3

import asyncio
from backend.brief_analyzer import BriefAnalyzer
import os
from dotenv import load_dotenv

load_dotenv()

async def test():
    analyzer = BriefAnalyzer(
        database_url='postgresql://legal_user:legal_pass@localhost:5432/legal_research',
        openai_api_key=os.getenv('OPENAI_API_KEY')
    )

    with open('test_brief.txt', 'rb') as f:
        content = f.read()

    try:
        # Test with AI enabled
        result = await analyzer.analyze_brief(content, 'test_brief.txt', use_ai=True)
        print(f'✅ Success with AI! Found {result.total_citations} citations')
        print(f'   AI Summary: {result.ai_summary[:100] if result.ai_summary else "None"}...')
        print(f'   Cost: ${result.analysis_cost:.4f}')
    except Exception as e:
        print(f'❌ Error with AI: {e}')
        import traceback
        traceback.print_exc()

asyncio.run(test())