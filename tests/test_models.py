"""Paper model tests."""

from datetime import datetime
from scraper.models import Paper, create_legacy_paper


class TestPaper:

    def test_paper_creation(self, sample_paper):
        assert sample_paper.id == "test_paper_001"
        assert sample_paper.title == "Deep Learning for Natural Language Processing"
        assert sample_paper.venue == "ICLR"
        assert sample_paper.year == 2024
        assert len(sample_paper.authors) == 2
        assert len(sample_paper.keywords) == 3

    def test_paper_to_dict(self, sample_paper):
        data = sample_paper.to_dict()

        assert isinstance(data, dict)
        assert data["id"] == "test_paper_001"
        assert data["title"] == "Deep Learning for Natural Language Processing"
        assert data["venue"] == "ICLR"
        assert data["year"] == 2024
        assert data["authors"] == ["Alice Smith", "Bob Johnson"]
        assert data["keywords"] == ["deep learning", "natural language processing", "transformer"]
        assert "created_at" in data

    def test_paper_from_dict(self):
        data = {
            "id": "from_dict_001",
            "title": "Test Paper Title",
            "abstract": "Test abstract",
            "authors": ["Test Author"],
            "venue": "NeurIPS",
            "year": 2023,
            "url": "https://example.com",
            "keywords": ["keyword1", "keyword2"],
            "extracted_keywords": ["extracted1"],
            "pdf_url": "https://example.com/pdf",
        }

        paper = Paper.from_dict(data)

        assert paper.id == "from_dict_001"
        assert paper.title == "Test Paper Title"
        assert paper.venue == "NeurIPS"
        assert paper.year == 2023
        assert paper.keywords == ["keyword1", "keyword2"]
        assert paper.extracted_keywords == ["extracted1"]

    def test_paper_from_dict_with_datetime_string(self):
        data = {
            "id": "datetime_test",
            "title": "Test",
            "venue": "ICML",
            "year": 2024,
            "created_at": "2024-01-15T10:30:00",
        }

        paper = Paper.from_dict(data)

        assert paper.id == "datetime_test"
        assert isinstance(paper.created_at, datetime)
        assert paper.created_at.year == 2024
        assert paper.created_at.month == 1
        assert paper.created_at.day == 15

    def test_paper_text_for_extraction(self, sample_paper):
        text = sample_paper.text_for_extraction

        assert isinstance(text, str)
        assert "Deep Learning for Natural Language Processing" in text
        assert "deep learning methods for NLP" in text
        assert ". " in text

    def test_paper_all_keywords(self):
        paper = create_legacy_paper(
            id="kw_test",
            title="Test",
            abstract="Test abstract",
            authors=[],
            venue="ICLR",
            year=2024,
            url="",
            keywords=["keyword1", "keyword2"],
            extracted_keywords=["keyword2", "keyword3"],
        )

        all_kw = paper.all_keywords

        assert isinstance(all_kw, list)
        assert len(all_kw) == 3
        assert "keyword1" in all_kw
        assert "keyword2" in all_kw
        assert "keyword3" in all_kw

    def test_paper_default_values(self):
        paper = create_legacy_paper(
            id="default_test",
            title="Test",
            abstract="",
            authors=[],
            venue="ICLR",
            year=2024,
            url="",
        )

        assert paper.keywords == []
        assert paper.extracted_keywords == []
        assert paper.pdf_url is None
        assert isinstance(paper.created_at, datetime)

    def test_paper_round_trip(self, sample_paper):
        data = sample_paper.to_dict()
        restored = Paper.from_dict(data)

        assert restored.id == sample_paper.id
        assert restored.title == sample_paper.title
        assert restored.abstract == sample_paper.abstract
        assert restored.venue == sample_paper.venue
        assert restored.year == sample_paper.year
        assert restored.keywords == sample_paper.keywords
