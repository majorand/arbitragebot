"""
Provider registry and aggregation service for the 5-layer canonical model.
"""

from typing import Dict, List, Any
from .layer_mappers import ESPNLayerMapper, KalshiLayerMapper, PolymarketLayerMapper
from .layer_aggregator import LayerAggregator, AggregatedInstrumentView

class ProviderRegistry:
    """Registry of available provider mappers."""

    _mappers = {
        "espn": ESPNLayerMapper(),
        "kalshi": KalshiLayerMapper(),
        "polymarket": PolymarketLayerMapper(),
    }

    @classmethod
    def get_mapper(cls, provider_name: str):
        """Get the mapper instance for a provider."""
        return cls._mappers.get(provider_name.lower())

    @classmethod
    def list_providers(cls) -> List[str]:
        """List all registered providers."""
        return list(cls._mappers.keys())

def aggregate_all_providers(provider_data: Dict[str, List[Dict[str, Any]]]) -> Dict[str, AggregatedInstrumentView]:
    """
    Fetch all provider data and aggregate into 5-layer canonical views.

    Args:
        provider_data: Dict mapping provider name to list of raw API objects.

    Returns:
        Dict mapping canonical keys to AggregatedInstrumentView objects.
    """
    aggregator = LayerAggregator()

    for provider_name, api_objects in provider_data.items():
        mapper = ProviderRegistry.get_mapper(provider_name)
        if not mapper:
            continue

        for obj in api_objects:
            try:
                instrument, outcome, expr, context, listing = mapper.map_to_layers(obj)

                # Register all layers
                aggregator.register_instrument(instrument)
                aggregator.register_outcome(outcome)
                aggregator.register_market_expression(expr)
                aggregator.register_context(context)
                aggregator.register_listing(listing)
            except Exception as e:
                # Log error and continue with next object
                print(f"Error mapping {provider_name} object: {e}")
                continue

    return aggregator.finalize()
