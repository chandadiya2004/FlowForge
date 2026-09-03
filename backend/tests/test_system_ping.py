from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def test_ping_worker_dispatches_task():
    fake_result = MagicMock()
    fake_result.id = "fake-task-uuid-1234"

    with patch("app.api.system.dispatch_task", return_value=fake_result) as mock_dispatch:
        response = client.post("/system/ping-worker")
        assert response.status_code == 202
        data = response.json()
        assert data["task_id"] == "fake-task-uuid-1234"
        assert data["status"] == "dispatched"
        mock_dispatch.assert_called_once_with("ping")


def test_get_task_result_pending():
    fake_result = MagicMock()
    fake_result.status = "PENDING"
    fake_result.ready.return_value = False

    with patch("app.api.system.get_task_result", return_value=fake_result):
        response = client.get("/system/task-result/fake-task-uuid-1234")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "fake-task-uuid-1234"
        assert data["status"] == "PENDING"
        assert data["result"] is None


def test_get_task_result_success():
    fake_result = MagicMock()
    fake_result.status = "SUCCESS"
    fake_result.ready.return_value = True
    fake_result.successful.return_value = True
    fake_result.result = "pong"

    with patch("app.api.system.get_task_result", return_value=fake_result):
        response = client.get("/system/task-result/fake-task-uuid-1234")
        assert response.status_code == 200
        data = response.json()
        assert data["task_id"] == "fake-task-uuid-1234"
        assert data["status"] == "SUCCESS"
        assert data["result"] == "pong"
