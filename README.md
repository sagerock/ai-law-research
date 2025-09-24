# Legal Research Tool - Free Alternative to Casetext

A proof-of-concept legal research tool designed for solo lawyers and small firms who need affordable, powerful legal research capabilities. Built as a free alternative to expensive services like Westlaw and Lexis.

## Features

### Core Capabilities
- **Hybrid Search**: Combines BM25 keyword search with semantic/vector search
- **AI Case Summaries**: Powered by GPT-5-mini for advanced legal analysis
- **Brief Analysis**: Upload briefs to extract and validate citations
- **Real-time Updates**: Webhook integration with CourtListener
- **Full Opinion Text**: Access complete court opinions

## Quick Start

1. Clone the repository
2. Copy `.env.example` to `.env` and add your API keys
3. Start the database: `docker-compose up -d`
4. Install dependencies: `pip install -r requirements.txt`
5. Run backend: `python backend/simple_api.py`
6. Install frontend: `cd frontend && npm install`
7. Run frontend: `npm run dev`
8. Visit http://localhost:3000

## Required API Keys

- **OpenAI API Key**: For AI summaries (~$0.002 per summary)
- **CourtListener Token**: For importing cases (free tier available)

## Cost Comparison

- **This Tool**: <$10/month
- **Westlaw/Lexis**: $100-500+/month
- **Casetext**: $65-250/month

Built with love for solo lawyers who deserve affordable legal research tools.
