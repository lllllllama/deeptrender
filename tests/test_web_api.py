"""Web API integration tests."""

import json


class TestHealthEndpoint:

    def test_health_check(self, test_client):
        response = test_client.get("/api/health")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert data["status"] == "healthy"
        assert data["service"] == "deeptrender"


class TestOverviewEndpoint:

    def test_overview(self, test_client):
        response = test_client.get("/api/stats/overview")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "total_papers" in data
        assert "total_keywords" in data
        assert "total_venues" in data
        assert "venues" in data
        assert "years" in data
        assert isinstance(data["venues"], list)
        assert isinstance(data["years"], list)

    def test_overview_empty_dataset_contract(self, test_client):
        response = test_client.get("/api/stats/overview")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "year_range" in data
        assert "total_papers" in data
        assert "total_keywords" in data
        assert data["total_papers"] >= 0


class TestKeywordsEndpoints:

    def test_top_keywords(self, test_client):
        response = test_client.get("/api/keywords/top")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_top_keywords_with_limit(self, test_client):
        response = test_client.get("/api/keywords/top?limit=10")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        assert len(data) <= 10

    def test_top_keywords_with_venue(self, test_client):
        response = test_client.get("/api/keywords/top?venue=ICLR")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_keyword_trends(self, test_client):
        response = test_client.get("/api/keywords/trends")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_keyword_trends_with_keywords(self, test_client):
        response = test_client.get("/api/keywords/trends?keyword=transformer&keyword=bert")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_wordcloud(self, test_client):
        response = test_client.get("/api/keywords/wordcloud")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)
        for item in data:
            if item:
                assert "name" in item
                assert "value" in item

    def test_emerging_keywords(self, test_client):
        response = test_client.get("/api/keywords/emerging")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)


class TestVenuesEndpoints:

    def test_venues_list(self, test_client):
        response = test_client.get("/api/stats/venues")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert isinstance(data, list)

    def test_venue_detail(self, test_client):
        response = test_client.get("/api/stats/venue/ICLR")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "venue" in data
        assert data["venue"] == "ICLR"


class TestComparisonEndpoint:

    def test_comparison(self, test_client):
        response = test_client.get("/api/keywords/comparison")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "year" in data
        assert "venues" in data


class TestStatusEndpoint:

    def test_status(self, test_client):
        response = test_client.get("/api/status")
        assert response.status_code == 200

        data = json.loads(response.data)
        assert "database" in data
        assert "data" in data
        assert "server_time" in data


class TestStaticFiles:

    def test_index_page(self, test_client):
        response = test_client.get("/")
        assert response.status_code == 200
