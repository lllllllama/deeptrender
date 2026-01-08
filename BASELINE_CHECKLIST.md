# 🔬 DeepTrender - Baseline Verification Checklist

This document defines the **baseline verification checklist** that must pass after any code changes to ensure the system remains functional and reproducible.

---

## 📋 Pre-Commit Checklist

Run these commands **before committing any changes**:

### ✅ 1. Code Quality

```bash
# Run all tests
make test
# OR
pytest -q

# Expected: All tests pass (52 tests)
```

**Pass Criteria:**
- ✅ All tests pass
- ✅ No import errors
- ✅ No syntax errors

---

### ✅ 2. Database Integrity

```bash
# Check database exists and is accessible
ls -lh data/keywords.db

# Check database schema
sqlite3 data/keywords.db "SELECT name FROM sqlite_master WHERE type='table';"
```

**Pass Criteria:**
- ✅ Database file exists
- ✅ All required tables present:
  - `raw_papers`
  - `papers`
  - `venues`
  - `paper_sources`
  - `paper_keywords`
  - `keywords`
  - `analysis_*` tables (7 tables)
  - `scrape_logs`

---

### ✅ 3. Pipeline Dry-Run

```bash
# Run minimal pipeline to verify all components work
python src/main.py --source arxiv --arxiv-days 1 --limit 5 --extractor yake
```

**Pass Criteria:**
- ✅ No crashes or exceptions
- ✅ Completes all 3 stages:
  1. Ingestion (data collection)
  2. Structuring (normalization)
  3. Analysis (keyword extraction)
- ✅ Generates output files in `output/`

---

### ✅ 4. Web API Health Check

```bash
# Start web server in background
python src/web/app.py &
WEB_PID=$!

# Wait for server to start
sleep 3

# Test health endpoint
curl -s http://localhost:5000/api/health | python -m json.tool

# Test overview endpoint
curl -s http://localhost:5000/api/stats/overview | python -m json.tool

# Kill server
kill $WEB_PID
```

**Pass Criteria:**
- ✅ Server starts without errors
- ✅ `/api/health` returns `{"status": "healthy"}`
- ✅ `/api/stats/overview` returns valid JSON with:
  - `total_papers`
  - `total_keywords`
  - `total_venues`
  - `venues` (list)
  - `years` (list)

---

## 📊 Post-Change Verification

Run these after **major changes** (new features, refactoring, dependency updates):

### ✅ 5. Full Pipeline Test

```bash
# Run full pipeline with real data
python src/main.py --source arxiv --arxiv-days 7 --limit 100
```

**Pass Criteria:**
- ✅ Completes without errors
- ✅ Processes papers from all configured sources
- ✅ Generates visualizations in `output/figures/`
- ✅ Generates report in `output/reports/`

**Expected Outputs:**
```
output/
├── figures/
│   ├── wordcloud_overall.png
│   ├── top_keywords.png
│   └── keyword_trends.png
└── reports/
    └── report.md
```

---

### ✅ 6. Test Coverage

```bash
# Run tests with coverage report
pytest --cov=src --cov-report=html --cov-report=term
```

**Pass Criteria:**
- ✅ Coverage > 70% (target: 80%+)
- ✅ All critical modules covered:
  - `src/agents/` > 75%
  - `src/database/` > 80%
  - `src/extractor/` > 70%
  - `src/analysis/` > 75%

---

### ✅ 7. Dependency Check

```bash
# Verify all dependencies are installed
pip check

# List installed packages
pip list | grep -E "(openreview|yake|keybert|flask|pytest)"
```

**Pass Criteria:**
- ✅ No dependency conflicts
- ✅ All required packages installed:
  - `openreview-py >8.0`
  - `yake >= 0.4.8`
  - `keybert >= 0.8.0`
  - `flask >= 3.0.0`
  - `pytest >= 7.4.0`

---

## 🚨 Critical Paths to Test

These are the **most critical code paths** that must always work:

### 1. Data Ingestion
```bash
python -c "
from agents import IngestionAgent
agent = IngestionAgent()
stats = agent.run(sources=['arxiv'], arxiv_days=1)
print(f'Ingested: {stats}')
"
```

### 2. Keyword Extraction
```bash
python -c "
from extractor.processor import KeywordProcessor
processor = KeywordProcessor(extractor_type='yake')
text = 'Deep learning for natural language processing'
keywords = processor.extract_keywords(text)
print(f'Keywords: {keywords}')
"
```

### 3. Database Operations
```bash
python -c "
from database import get_repository
repo = get_repository()
count = repo.get_paper_count()
print(f'Total papers: {count}')
"
```

### 4. Web API
```bash
python -c "
from web.app import create_app
app = create_app()
with app.test_client() as client:
    response = client.get('/api/health')
    print(f'Status: {response.status_code}')
    print(f'Data: {response.json}')
"
```

---

## 🔄 Continuous Integration

For **GitHub Actions** or CI/CD pipelines:

```yaml
# .github/workflows/test.yml
name: Baseline Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      
      - name: Install dependencies
        run: pip install -r requirements.txt
      
      - name: Run baseline tests
        run: |
          pytest -q
          python src/main.py --source arxiv --arxiv-days 1 --limit 5
```

---

## 📝 Baseline Metrics

Track these metrics over time:

| Metric | Baseline | Target | Current |
|--------|----------|--------|---------|
| **Test Count** | 60+ | ___ |
| **Test Coverage** | 70% | 80%+ | ___ |
| **Pipeline Time** | ~5min | <10min | ___ |
| **Database Size** | ~20MB | <100MB | ___ |
| **API Response Time** | <100ms | <50ms | ___ |

---

## 🛠️ Quick Commands

```bash
# One-command baseline check
make check-baseline

# Full verification suite
make test && make run-test && make web

# Clean and rebuild
make clean-all && make setup
```

---

## 📚 Troubleshooting

### Issue: Tests fail with import errors
**Solution:**
```bash
# Reinstall dependencies
pip install -r requirements.txt --force-reinstall

# Verify Python path
python -c "import sys; print('\n'.join(sys.path))"
```

### Issue: Database locked
**Solution:**
```bash
# Check for zombie processes
ps aux | grep python

# Kill if needed
pkill -f "python src/main.py"

# Backup and recreate
cp data/keywords.db data/keywords.backup.db
rm data/keywords.db
python src/main.py --limit 10
```

### Issue: Web server won't start
**Solution:**
```bash
# Check if port 5000 is in use
lsof -i :5000

# Kill process using port
kill -9 $(lsof -t -i:5000)

# Start on different port
FLASK_RUN_PORT=5001 python src/web/app.py
```

---

## ✅ Sign-Off

After running all checks, verify:

- [ ] All tests pass (`make test`)
- [ ] Pipeline completes (`make run-test` ] Web API responds (`make web`)
- [ ] No errors in logs
- [ ] Database is accessible
- [ ] Output files generated

**Date:** ___________  
**Verified by:** ___________  
**Git commit:** ___________

---

**Last Updated:** 2025-01-07  
**Version:** 1.0.0
