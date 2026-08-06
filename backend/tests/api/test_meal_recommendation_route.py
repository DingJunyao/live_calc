import inspect

from app.api.meals import (
    get_daily_recommendations,
    refresh_recommendation,
    trigger_recommendation_generation,
)


def test_recommendation_routes_are_sync_for_threadpool_offload():
    """Heavy recipe scoring must not run directly on the async event loop."""
    assert not inspect.iscoroutinefunction(get_daily_recommendations)
    assert not inspect.iscoroutinefunction(trigger_recommendation_generation)
    assert not inspect.iscoroutinefunction(refresh_recommendation)
