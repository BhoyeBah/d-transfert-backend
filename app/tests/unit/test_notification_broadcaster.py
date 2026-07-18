import asyncio
import uuid

from app.core.notification_broadcaster import InMemoryNotificationBroadcaster


async def test_publish_delivers_to_active_subscriber():
    broadcaster = InMemoryNotificationBroadcaster()
    company_id = uuid.uuid4()

    async with broadcaster.subscribe(company_id) as queue:
        broadcaster.publish(company_id, {"message": "hello"})
        payload = await asyncio.wait_for(queue.get(), timeout=1)

    assert payload == {"message": "hello"}


async def test_publish_without_subscribers_does_not_raise():
    broadcaster = InMemoryNotificationBroadcaster()
    broadcaster.publish(uuid.uuid4(), {"message": "no one home"})


async def test_publish_only_reaches_matching_company():
    broadcaster = InMemoryNotificationBroadcaster()
    company_a, company_b = uuid.uuid4(), uuid.uuid4()

    async with broadcaster.subscribe(company_a) as queue_a:
        broadcaster.publish(company_b, {"message": "for B"})
        try:
            await asyncio.wait_for(queue_a.get(), timeout=0.1)
        except TimeoutError:
            pass
        else:
            raise AssertionError("company_a ne devrait recevoir aucun événement destiné à company_b")


async def test_multiple_subscribers_all_receive_the_event():
    broadcaster = InMemoryNotificationBroadcaster()
    company_id = uuid.uuid4()

    async with broadcaster.subscribe(company_id) as queue_1, broadcaster.subscribe(company_id) as queue_2:
        broadcaster.publish(company_id, {"message": "broadcast"})
        assert await asyncio.wait_for(queue_1.get(), timeout=1) == {"message": "broadcast"}
        assert await asyncio.wait_for(queue_2.get(), timeout=1) == {"message": "broadcast"}


async def test_unsubscribing_stops_further_delivery():
    broadcaster = InMemoryNotificationBroadcaster()
    company_id = uuid.uuid4()

    async with broadcaster.subscribe(company_id) as queue:
        pass

    broadcaster.publish(company_id, {"message": "too late"})
    assert queue.empty()
