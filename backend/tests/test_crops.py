import pytest
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest.mark.asyncio
async def test_get_crops_endpoint():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as client:
        response = await client.get("/api/v1/crops")
        assert response.status_code == 200
        crops = response.json()
        assert len(crops) >= 20

        # Verify sorted by category then name
        sorted_crops = sorted(crops, key=lambda c: (c["category"], c["name"]))
        assert [c["id"] for c in crops] == [c["id"] for c in sorted_crops]

        # Verify all common crops exist
        crop_names = {c["name"] for c in crops}
        expected_names = {
            "Wheat", "Rice", "Cotton", "Soybean", "Sugarcane", "Maize",
            "Bajra", "Jowar", "Groundnut", "Tur/Arhar", "Gram (Chana)",
            "Mustard", "Onion", "Tomato", "Potato", "Turmeric"
        }
        for name in expected_names:
            assert name in crop_names, f"Missing expected crop: {name}"

        # Verify categories, translations and stages
        valid_categories = {"cereal", "pulse", "oilseed", "cash crop", "vegetable", "spice"}
        for crop in crops:
            assert crop["category"] in valid_categories, f"Invalid category for {crop['name']}"
            assert crop["name_hi"], f"Missing Hindi name for {crop['name']}"
            assert crop["name_mr"], f"Missing Marathi name for {crop['name']}"
            assert len(crop["stages"]) >= 4, f"Crop {crop['name']} should have at least 4 stages"

            stage_names_lower = " ".join(s["stage_name"].lower() for s in crop["stages"])
            # Sowing/planting/nursery
            assert any(k in stage_names_lower for k in ["sowing", "nursery", "planting", "emergence", "germination", "seedling"]), f"Missing sowing stage in {crop['name']}"
            # Vegetative
            assert any(k in stage_names_lower for k in ["vegetative", "tillering", "branching", "rosette", "knee high"]), f"Missing vegetative stage in {crop['name']}"
            # Flowering
            assert any(k in stage_names_lower for k in ["flowering", "heading", "tasseling", "pod", "bulb", "tuber", "rhizome", "square", "grand growth"]), f"Missing flowering stage in {crop['name']}"
            # Maturity/harvest
            assert any(k in stage_names_lower for k in ["maturity", "maturation", "harvest", "harvesting", "ripening", "bursting"]), f"Missing maturity/harvest stage in {crop['name']}"
