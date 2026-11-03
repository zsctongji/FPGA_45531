"""Explicitly synthetic localhost exercise, never a board-camera measurement."""
import argparse
import socket
from protocol import packets, event_body, SYNTHETIC


def send(host='127.0.0.1', port=39003):
    image = bytes(0 if y < 21 or y >= 75 else (x * 2 + y * 3) % 256
                  for y in range(96) for x in range(96))
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        for kind, body in [(1, event_body(score=192, valid_mask=7, alarm=True,
                             temperature_centi=2534, humidity_centi=5678,visual_age=20,thermal_age=30,env_age=100,infer_ms=8)), (2, image)]:
            for part in reversed(packets(kind, 0xA2026102, 1, 30, 1000, body, SYNTHETIC)):
                s.sendto(part, (host, port))
    return image


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--host', default='127.0.0.1')
    p.add_argument('--port', type=int, default=39003)
    send(**vars(p.parse_args()))
    print('SYNTHETIC event + 96x96 image sent (reverse fragment order).')
