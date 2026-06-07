import time

from sqlmodel import Session, select

from app.models.click_event import ClickEvent
from app.models.url import Url


def test_worker_processes_click_event(client, worker, click_queue, engine):
    created = client.post("/shorten", json={"long_url": "https://example.com/worker"}).json()
    code = created["short_code"]

    client.get(f"/{code}", follow_redirects=False)
    assert click_queue.queue_depth() >= 1

    event = click_queue.dequeue(timeout=1)
    assert event is not None
    click_queue.enqueue(event)

    worker._process_event(event)

    with Session(engine) as session:
        url = session.exec(select(Url).where(Url.short_code == code)).first()
        assert url.total_clicks == 1
        events = session.exec(select(ClickEvent).where(ClickEvent.short_code == code)).all()
        assert len(events) == 1


def test_analytics_endpoint(client, worker, click_queue):
    created = client.post("/shorten", json={"long_url": "https://example.com/analytics"}).json()
    code = created["short_code"]

    client.get(f"/{code}", follow_redirects=False)
    event = click_queue.dequeue(timeout=1)
    worker._process_event(event)

    time.sleep(0.1)
    response = client.get(f"/urls/{code}/analytics")
    assert response.status_code == 200
    body = response.json()
    assert body["total_clicks"] == 1
    assert len(body["recent_events"]) == 1
