# Hugging Face Dataset Access Setup

The Caselaw Access Project dataset on Hugging Face is "gated" - you need to request access.

## Option 1: Get Hugging Face Access (Recommended - Easiest)

### Step 1: Create Account
1. Go to https://huggingface.co/join
2. Create a free account

### Step 2: Request Dataset Access
1. Visit https://huggingface.co/datasets/free-law/Caselaw_Access_Project
2. Click "Request Access" button
3. Fill out the form (usually instant approval)

### Step 3: Get Access Token
1. Go to https://huggingface.co/settings/tokens
2. Click "New token"
3. Name it "CAP Access" and select "Read" permissions
4. Copy the token

### Step 4: Login with Token
```bash
cd "/Volumes/T7/Scripts/AI Law Researcher/legal-research-tool"
python3 -c "from huggingface_hub import login; login()"
# Paste your token when prompted
```

### Step 5: Run Import
```bash
python3 scripts/import_from_huggingface.py
```

## Option 2: Use Harvard Direct Downloads

If Hugging Face doesn't work, we can download directly from Harvard's servers.

### Download Ohio Bulk Data
```bash
# Ohio data is available at:
# https://case.law/download/

# Download format:
curl "https://case.law/download/state/Ohio/" -o ohio_cases.zip
unzip ohio_cases.zip
```

Then use a custom import script to load from the downloaded JSON files.

## Which Should You Choose?

- **Hugging Face**: Easier, cleaned data, good for development
- **Harvard Direct**: More control, official source, good for production

For now, try Hugging Face first - it should only take a few minutes to set up!
