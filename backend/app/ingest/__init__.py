"""Live AIS ingestion pipeline.

Modules:
    aisstream_listener — WebSocket consumer (positions + static data)
    state              — in-memory per-vessel rolling state
    event_extractor    — derives AISGap / Encounter / PortCall rows from state
    run                — CLI entrypoint that wires the above together
"""
