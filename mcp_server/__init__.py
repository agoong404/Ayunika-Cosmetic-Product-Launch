"""
mcp_server — lapisan MCP di atas `engine/` dan `agents/`.

Isi paket ini hanya pembungkus. Tidak ada aturan review yang ditulis ulang di
sini: `engine/reviewer.py` tetap satu-satunya penilai, dan `engine/governance.py`
tetap satu-satunya gerbang approval.

    tools.py   fungsi biasa (tanpa impor `mcp`) — bisa diuji tanpa protokol
    server.py  pendaftaran 12 tool ke MCPServer
    stdio.py   transport stdio (WorkBuddy menjalankan proses ini)
    http.py    transport streamableHttp + bearer token (Path B, belum dipakai)
"""
