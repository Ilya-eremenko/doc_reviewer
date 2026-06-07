from app.seeds.skills import seed_baseline_skills

from test_documents_upload import create_user, login


def test_authenticated_user_can_list_active_skills(client, db_session):
    create_user(db_session, "author", "secret")
    seed_baseline_skills(db_session)
    login(client, "author", "secret")

    response = client.get("/skills")

    assert response.status_code == 200
    names = {skill["name"] for skill in response.json()["skills"]}
    assert "gate2_challenger_main_analysis" in names
    assert "devils_advocate_predefense" in names
    gate2 = next(skill for skill in response.json()["skills"] if skill["name"] == "gate2_challenger_main_analysis")
    assert gate2["source_snapshot"]["source_uri"]
    assert gate2["result_schema_path"] == "contracts/schemas/main-analysis-result.schema.json"
