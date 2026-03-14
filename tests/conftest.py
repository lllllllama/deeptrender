"""Test fixtures."""

import pytest
import tempfile
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from scraper.models import create_legacy_paper
from database.repository import DatabaseRepository


@pytest.fixture
def sample_paper():
    return create_legacy_paper(
        id="test_paper_001",
        title="Deep Learning for Natural Language Processing",
        abstract=(
            "This paper presents a comprehensive study of deep learning methods for "
            "NLP tasks including sentiment analysis, machine translation, and question answering."
        ),
        authors=["Alice Smith", "Bob Johnson"],
        venue="ICLR",
        year=2024,
        url="https://openreview.net/forum?id=test_paper_001",
        keywords=["deep learning", "natural language processing", "transformer"],
        extracted_keywords=[],
        pdf_url="https://openreview.net/pdf?id=test_paper_001",
    )


@pytest.fixture
def sample_papers():
    return [
        create_legacy_paper(
            id="paper_001",
            title="Attention Is All You Need",
            abstract="We propose a new architecture called Transformer based solely on attention mechanisms.",
            authors=["Author A"],
            venue="NeurIPS",
            year=2023,
            url="https://example.com/1",
            keywords=["transformer", "attention"],
        ),
        create_legacy_paper(
            id="paper_002",
            title="BERT: Pre-training of Deep Bidirectional Transformers",
            abstract="We introduce BERT, a language representation model.",
            authors=["Author B"],
            venue="ICLR",
            year=2023,
            url="https://example.com/2",
            keywords=["bert", "pre-training", "transformer"],
        ),
        create_legacy_paper(
            id="paper_003",
            title="GPT-4 Technical Report",
            abstract="We report the development of GPT-4, a large multimodal model.",
            authors=["Author C"],
            venue="ICLR",
            year=2024,
            url="https://example.com/3",
            keywords=["gpt-4", "large language model", "multimodal"],
        ),
    ]


@pytest.fixture
def temp_db_path():
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        yield Path(f.name)


@pytest.fixture
def repo(temp_db_path):
    return DatabaseRepository(db_path=temp_db_path)


@pytest.fixture
def repo_with_data(repo, sample_papers):
    for paper in sample_papers:
        paper.extracted_keywords = ["machine learning", "neural network"]
        repo.save_paper(paper)
    return repo


@pytest.fixture
def flask_app(temp_db_path):
    from web.app import create_app
    from database import unified as repo_module

    repo_module._repository = None
    repo_module._raw_repository = None
    repo_module._structured_repository = None
    repo_module._analysis_repository = None
    repo_module.get_repository(db_path=temp_db_path)

    app = create_app()
    app.config["TESTING"] = True
    return app


@pytest.fixture
def test_client(flask_app):
    return flask_app.test_client()
