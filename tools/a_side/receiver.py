"""UDP event/image recorder with a loopback-only read-only status dashboard."""
import argparse
import csv
import datetime
import json
from pathlib import Path
import socket
import struct
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from protocol import Reassembler, parse_event


class Recorder:
    def __init__(self, output):
        self.output = Path(output)
        self.output.mkdir(parents=True, exist_ok=True)
        self.last = {}
        self.last_image = {}
        self.bmp = b''
        self.saved = 0
        self.lock = threading.Lock()

    def save(self, message):
        message = dict(message)
        body = message.pop('body')
        message['received_utc'] = datetime.datetime.now(datetime.timezone.utc).isoformat()
        if message['kind'] == 1:
            message.update(parse_event(body))
        label = 'SYNTHETIC' if message['synthetic'] else 'NETWORK_UNVERIFIED'
        # Unique reception suffix prevents another peer/session overwriting evidence.
        stem = f"{label}_{message['session']:08x}_{message['event']}_{message['frame']}_{time.time_ns()}"
        if message['kind'] == 2:
            image = stem + '.pgm'
            (self.output / image).write_bytes(b'P5\n# ' + label.encode() + b'\n96 96\n255\n' + body)
            message['image'] = image
            # BMP needs no external imaging library and is browser-viewable.
            pixels = b''.join(bytes((g, g, g)) for g in body)
            bmp = b'BM' + struct.pack('<IHHI', 54 + len(pixels), 0, 0, 54)
            bmp += struct.pack('<IiiHHIIiiII', 40, 96, -96, 1, 24, 0, len(pixels), 0, 0, 0, 0) + pixels
            (self.output / (stem + '.bmp')).write_bytes(bmp)
        (self.output / (stem + '.bin')).write_bytes(body)
        with self.lock:
            if message['kind'] == 2:
                self.bmp = bmp
                self.last_image = dict(message)
            with (self.output / 'events.jsonl').open('a', encoding='utf-8') as f:
                f.write(json.dumps(message, ensure_ascii=False) + '\n')
            if message['kind'] == 1:
                target = self.output / 'events.csv'
                exists = target.exists()
                with target.open('a', encoding='utf-8-sig', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=list(message))
                    if not exists:
                        writer.writeheader()
                    writer.writerow(message)
            self.saved += 1
            self.last = message
        return message


def dashboard(recorder, reassembler):
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == '/status':
                with recorder.lock:
                    content = json.dumps(dict(saved=recorder.saved, last=recorder.last, last_image=recorder.last_image,
                                              counters=dict(reassembler.stats)), ensure_ascii=False).encode()
                mime = 'application/json; charset=utf-8'
            elif self.path.split('?')[0] == '/image.bmp':
                with recorder.lock:
                    content = recorder.bmp
                if not content:
                    self.send_error(404)
                    return
                mime = 'image/bmp'
            elif self.path == '/':
                content = '''<!doctype html><meta charset="utf-8"><title>A侧接收状态</title>
                <style>body{font:18px system-ui;max-width:950px;margin:40px auto;background:#f7f6f1}pre{white-space:pre-wrap;background:white;padding:20px}</style>
                <h1>FPGA 事件接收</h1><p>PC 测试数据带 SYNTHETIC 标记。网络收到的数据仍须与板端和现场录像核对。</p>
                <p>下图为最近完整图像；事件与图像须按 session、event、frame 对照。分值为 0～255，并非校准概率。</p><img id="im" width="288" height="288" alt="等待完整图像" style="image-rendering:pixelated"><pre id="s">等待数据</pre>
                <script>async function refresh(){try{const r=await fetch('/status');const d=await r.json();document.getElementById('s').textContent=JSON.stringify(d,null,2);if(d.last_image.image)document.getElementById('im').src='/image.bmp?t='+encodeURIComponent(d.last_image.received_utc)}catch(e){document.getElementById('s').textContent='接收器已停止'}}setInterval(refresh,1000);refresh()</script>'''.encode()
                mime = 'text/html; charset=utf-8'
            else:
                self.send_error(404)
                return
            self.send_response(200)
            self.send_header('Content-Type', mime)
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        def log_message(self, *args):
            pass
    return Handler


def run(bind='127.0.0.1', port=39003, output='received', seconds=0, web_port=39004, peer_ip=None):
    recorder, assembly = Recorder(output), Reassembler()
    server = None
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.bind((bind, port))
        sock.settimeout(.2)
        if web_port:
            server = ThreadingHTTPServer(('127.0.0.1', web_port), dashboard(recorder, assembly))
            threading.Thread(target=server.serve_forever, daemon=True).start()
        print(f'UDP {bind}:{sock.getsockname()[1]} -> {recorder.output.resolve()}', flush=True)
        if web_port:
            print(f'Status: http://127.0.0.1:{web_port}', flush=True)
        deadline = time.monotonic() + seconds if seconds else float('inf')
        try:
            while time.monotonic() < deadline:
                try:
                    data, peer = sock.recvfrom(65535)
                except socket.timeout:
                    assembly.expire()
                    continue
                if peer_ip and peer[0] != peer_ip:
                    assembly.stats['peer_rejected'] += 1
                    continue
                result = assembly.feed(data, peer)
                if result:
                    try:
                        saved = recorder.save(result)
                        print(json.dumps(saved, ensure_ascii=False), flush=True)
                    except (ValueError, struct.error):
                        assembly.stats['invalid_event'] += 1
        except KeyboardInterrupt:
            pass
        finally:
            if server:
                server.shutdown()
                server.server_close()
            (recorder.output / 'receiver_summary.json').write_text(json.dumps(dict(
                counters=dict(assembly.stats), saved=recorder.saved,
                incomplete=len(assembly.pending), bind=bind, port=port,
                board_verified=False), indent=2), encoding='utf-8')
    return recorder, assembly


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--bind', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=39003)
    ap.add_argument('--web-port', type=int, default=39004)
    ap.add_argument('--output', default='received')
    ap.add_argument('--seconds', type=float, default=0)
    ap.add_argument('--peer-ip')
    run(**vars(ap.parse_args()))
