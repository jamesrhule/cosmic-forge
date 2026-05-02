# `streams/`

Reserved for binary-framed timeline streams (ormsgpack) the
visualizer's WebSocket client downloads when offline. Currently
empty — the cosmic-forge-viz baker writes JSON-only snapshots to
the parent directory; the binary stream path lands when the
frontend's WS layer needs it for >1 MB timelines.
