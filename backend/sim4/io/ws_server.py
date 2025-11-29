import asyncio
import websockets
from ..runtime.snapshots import snapshot_json

class SnapshotServer:
    def __init__(self, world, host="127.0.0.1", port=8765):
        self.world = world
        self.host = host
        self.port = port
        self.connections = set()

    async def handler(self, websocket):
        self.connections.add(websocket)
        try:
            async for _ in websocket:
                pass
        finally:
            self.connections.remove(websocket)

    async def broadcast_loop(self):
        while True:
            snap = snapshot_json(self.world)
            dead = []
            for ws in self.connections:
                try:
                    await ws.send(snap)
                except:
                    dead.append(ws)

            for ws in dead:
                self.connections.remove(ws)

            await asyncio.sleep(0.1)   # send 10 snapshots/sec

    async def run(self):
        async with websockets.serve(self.handler, self.host, self.port):
            await self.broadcast_loop()
