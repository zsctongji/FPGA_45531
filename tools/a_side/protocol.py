"""A1 network contract; synthetic flag is mandatory on PC-generated evidence."""
import struct
import time
import zlib
from collections import Counter, OrderedDict

HEADER = struct.Struct('!4sBBBBIIIIHHIII')
MAGIC = b'T3A1'
CHUNK = 1200
MAX_BODY = 16384
EVENT = struct.Struct('!BBBBhHIIIIHHHH')
SYNTHETIC = 1


def packets(kind, session, event, frame, timestamp, body, flags=0):
    body = bytes(body)
    if kind not in (1, 2) or flags not in (0, 1) or not 0 < len(body) <= MAX_BODY:
        raise ValueError('kind/flags/size')
    if kind == 1 and len(body) != EVENT.size or kind == 2 and len(body) != 9216:
        raise ValueError('body shape')
    count = (len(body) + CHUNK - 1) // CHUNK
    crc = zlib.crc32(body)
    result = []
    for index in range(count):
        part = body[index * CHUNK:(index + 1) * CHUNK]
        head = HEADER.pack(MAGIC, 1, kind, flags, HEADER.size, session, event,
                           frame, timestamp, index, count, len(body), crc, 0)
        result.append(head[:-4] + struct.pack('!I', zlib.crc32(head[:-4] + part)) + part)
    return result


class Reassembler:
    """Bounded, peer/session-isolated, strict shape validation; no partial images."""
    def __init__(self, timeout=2., capacity=32, clock=time.monotonic):
        self.timeout, self.capacity, self.clock = timeout, capacity, clock
        self.pending = OrderedDict()
        self.completed = OrderedDict()
        self.stats = Counter()

    def expire(self):
        now = self.clock()
        for key, value in list(self.pending.items()):
            if now - value['start'] >= self.timeout:
                del self.pending[key]
                self.stats['timeout'] += 1
        for key, when in list(self.completed.items()):
            if now - when >= 10 * self.timeout:
                del self.completed[key]

    def feed(self, packet, peer=('offline', 0)):
        self.expire()
        try:
            if len(packet) < HEADER.size:
                raise ValueError()
            magic, version, kind, flags, size, session, event, frame, ts, index, count, total, crc, part_crc = HEADER.unpack_from(packet)
            part = packet[HEADER.size:]
            if magic != MAGIC or version != 1 or size != HEADER.size or flags not in (0, 1):
                raise ValueError()
            if kind not in (1, 2) or total != (EVENT.size if kind == 1 else 9216):
                raise ValueError()
            if count != (total + CHUNK - 1) // CHUNK or not 0 <= index < count:
                raise ValueError()
            if len(part) != min(CHUNK, total - index * CHUNK) or zlib.crc32(packet[:HEADER.size-4] + part) != part_crc:
                raise ValueError()
        except (ValueError, struct.error):
            self.stats['invalid'] += 1
            return None
        key = (peer, session, kind, event, frame)
        if key in self.completed:
            self.stats['replay'] += 1
            return None
        signature = (flags, ts, count, total, crc)
        if key not in self.pending:
            if len(self.pending) >= self.capacity:
                self.pending.popitem(last=False)
                self.stats['evicted'] += 1
            self.pending[key] = dict(start=self.clock(), signature=signature, pieces={})
        item = self.pending[key]
        if item['signature'] != signature:
            self.stats['conflict'] += 1
            return None
        if index in item['pieces']:
            self.stats['duplicate' if item['pieces'][index] == part else 'conflict'] += 1
            return None
        item['pieces'][index] = part
        if len(item['pieces']) != count:
            return None
        del self.pending[key]
        body = b''.join(item['pieces'][i] for i in range(count))
        if zlib.crc32(body) != crc:
            self.stats['body_crc'] += 1
            return None
        self.completed[key] = self.clock()
        if len(self.completed) > self.capacity * 8:
            self.completed.popitem(last=False)
        self.stats['complete'] += 1
        return dict(kind=kind, session=session, event=event, frame=frame,
                    timestamp_ms=ts, synthetic=bool(flags & 1), crc32=crc,
                    peer=peer, body=body)


def event_body(event_type=1, score=0, valid_mask=0, alarm=False,
               temperature_centi=0, humidity_centi=0, visual_age=0xffffffff,
               thermal_age=0xffffffff, env_age=0xffffffff, infer_ms=0,
               x0=0, y0=0, x1=0, y1=0):
    if not (0 <= event_type <= 3 and 0 <= score <= 255 and 0 <= valid_mask <= 7
            and 0 <= humidity_centi <= 10000 and 0 <= x0 <= x1 < 96 and 0 <= y0 <= y1 < 54):
        raise ValueError('event fields')
    return EVENT.pack(event_type, score, valid_mask, int(alarm), temperature_centi,
                      humidity_centi, visual_age, thermal_age, env_age, infer_ms, x0, y0, x1, y1)


def parse_event(body):
    names = ('event_type', 'score', 'valid_mask', 'alarm', 'temperature_centi',
             'humidity_centi', 'visual_age_ms', 'thermal_age_ms', 'env_age_ms',
             'infer_ms', 'x0', 'y0', 'x1', 'y1')
    values = dict(zip(names, EVENT.unpack(body)))
    if values['event_type'] > 3 or values['valid_mask'] > 7 or values['alarm'] > 1 or values['humidity_centi'] > 10000:
        raise ValueError('event range')
    if not 0 <= values['x0'] <= values['x1'] < 96 or not 0 <= values['y0'] <= values['y1'] < 54:
        raise ValueError('bbox range')
    return values
