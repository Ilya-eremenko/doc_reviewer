import os
from pathlib import Path


REPO_ROOT = Path(
    os.environ.get(
        "PRODUCTION_DEPLOY_REPO_ROOT",
        str(Path(__file__).resolve().parents[3]),
    )
)


def test_production_compose_uses_release_tagged_application_images() -> None:
    compose = (REPO_ROOT / "infra/docker-compose.prod.yml").read_text()

    assert "image: ${GATE_API_IMAGE:-infra-api}" in compose
    assert "image: ${GATE_WORKER_IMAGE:-infra-worker}" in compose
    assert "image: ${GATE_WEB_IMAGE:-infra-web}" in compose


def test_production_workflow_deploys_only_verified_main_sha() -> None:
    workflow = (REPO_ROOT / ".github/workflows/deploy-production.yml").read_text()

    assert "push:\n    branches:\n      - main" in workflow
    assert "pull_request:\n    branches:\n      - main" in workflow
    assert "needs: verify" in workflow
    assert "if: github.ref == 'refs/heads/main'" in workflow
    assert "cancel-in-progress: false" in workflow
    assert '"deploy $GITHUB_SHA"' in workflow
    assert "environment:\n      name: production" in workflow


def test_codex_review_workflow_merges_only_clean_verified_head() -> None:
    workflow = (
        REPO_ROOT / ".github/workflows/codex-auto-merge.yml"
    ).read_text()

    assert "pull_request_review:\n    types:\n      - submitted" in workflow
    assert "startsWith(github.event.review.user.login" in workflow
    assert "github.event.review.commit_id == github.event.pull_request.head.sha" in workflow
    assert "/reviews/$REVIEW_ID/comments?per_page=100" in workflow
    assert 'if [ "$comment_count" -ne 0 ]' in workflow
    assert 'grep -Fxq "Verify release"' in workflow
    assert "--required --watch" in workflow
    assert 'if [ "$current_head_sha" != "$REVIEWED_HEAD_SHA" ]' in workflow
    assert '--match-head-commit "$REVIEWED_HEAD_SHA"' in workflow
    assert "--squash" in workflow
    assert "pull_request_target" not in workflow


def test_server_deployer_enforces_traceable_release_safety() -> None:
    deployer = (REPO_ROOT / "deploy/server/gate-challenger-deploy").read_text()

    required_safety_controls = (
        "flock -n",
        "requested SHA is not the current origin/main",
        "pg_dump",
        "alembic upgrade head",
        "python -m app.seeds.skills",
        "health_check",
        "rollback_release",
        "restored the previous active release pointer",
    )

    for control in required_safety_controls:
        assert control in deployer


def test_restricted_ssh_entrypoint_accepts_only_a_commit_sha() -> None:
    entrypoint = (
        REPO_ROOT / "deploy/server/gate-challenger-deploy-entrypoint"
    ).read_text()

    assert "SSH_ORIGINAL_COMMAND" in entrypoint
    assert "^deploy\\ ([0-9a-f]{40})$" in entrypoint
    assert "exec sudo -n /usr/local/sbin/gate-challenger-deploy" in entrypoint
