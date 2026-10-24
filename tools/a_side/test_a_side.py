import csv
import io
import json
from pathlib import Path
import random
import socket
import struct
import tempfile
import threading
import time
import unittest
import urllib.request
import zlib
from protocol import packets, Reassembler, event_body, parse_event, HEADER, EVENT
from receiver import Recorder, dashboard
from http.server import ThreadingHTTPServer
from measure_video import analyse
from check_capture import check


class ProtocolTests(unittest.TestCase):
    def setUp(self):
        self.image = bytes(i % 256 for i in range(9216))
        self.parts = packets(2, 7, 8, 9, 0xfffffff0, self.image, 1)

    def test_reference_sizes(self):
        self.assertEqual((HEADER.size, EVENT.size, len(self.parts)), (40, 32, 8))
        self.assertEqual(len(self.parts[-1]), 856)

    def test_reordered_duplicates_crc(self):
        a = Reassembler()
        self.assertIsNone(a.feed(self.parts[3]));self.assertIsNone(a.feed(self.parts[3]))
        out = None
        for part in reversed(self.parts):
            out = a.feed(part) or out
        self.assertEqual(out['body'], self.image)
        self.assertTrue(out['synthetic'])
        self.assertEqual(a.stats['duplicate'], 2)
        a.feed(self.parts[0]);self.assertEqual(a.stats['replay'], 1)

    def test_random_permutations(self):
        rng = random.Random(20261022)
        for _ in range(60):
            p = self.parts[:];rng.shuffle(p);a=Reassembler()
            results=[r for item in p if (r:=a.feed(item))]
            self.assertEqual(len(results),1);self.assertEqual(results[0]['body'],self.image)

    def test_partial_timeout_capacity(self):
        now=[0.];a=Reassembler(clock=lambda:now[0],capacity=2)
        a.feed(self.parts[0]);now[0]=2.;a.expire()
        self.assertEqual(a.stats['timeout'],1)
        for event in range(10):a.feed(packets(2,7,event,9,0,self.image)[0])
        self.assertEqual(len(a.pending),2);self.assertEqual(a.stats['evicted'],8)

    def test_peer_and_session_isolation(self):
        a=Reassembler()
        for i,part in enumerate(self.parts):self.assertIsNone(a.feed(part,('127.0.0.1',100+i%2)))
        self.assertEqual(len(a.pending),2)
        for part in packets(2,8,8,9,0,self.image):out=a.feed(part)
        self.assertEqual(out['session'],8)

    def test_malformed_and_corruption(self):
        a=Reassembler()
        bad=[b'',b'x'*10,self.parts[0]+b'X',self.parts[0][:-1],b'xxxx'+self.parts[0][4:]]
        for offset in (4,5,6,7,24,26,28,32,36,60):
            p=bytearray(self.parts[0]);p[offset]^=0x80;bad.append(bytes(p))
        for p in bad:self.assertIsNone(a.feed(p))
        self.assertEqual(a.stats['invalid'],len(bad))

    def test_whole_crc_and_header_conflict(self):
        a=Reassembler()
        for packet in self.parts:
            p=bytearray(packet);p[32]^=1;p[36:40]=struct.pack('!I',zlib.crc32(p[:36]+p[40:]));a.feed(p)
        self.assertEqual(a.stats['body_crc'],1)
        a.feed(self.parts[0]);a.feed(packets(2,7,8,9,999,self.image,1)[1])
        self.assertEqual(a.stats['conflict'],1)

    def test_event_boundaries(self):
        e=parse_event(event_body(score=255,valid_mask=7,temperature_centi=-32768,humidity_centi=10000,x1=95,y1=53))
        self.assertEqual(e['temperature_centi'],-32768)
        for kwargs in [dict(score=256),dict(humidity_centi=10001),dict(x1=96),dict(y1=54),dict(valid_mask=8)]:
            with self.assertRaises(ValueError):event_body(**kwargs)
        p=bytearray(event_body());p[0]=255
        with self.assertRaises(ValueError):parse_event(p)

    def test_fuzz_no_unbounded_pending(self):
        a=Reassembler(capacity=4);rng=random.Random(42)
        for _ in range(2000):a.feed(rng.randbytes(rng.randrange(0,1300)))
        self.assertFalse(a.pending);self.assertEqual(a.stats['invalid'],2000)

    def test_loopback_udp_record_and_dashboard(self):
        with tempfile.TemporaryDirectory() as folder, socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as rx, socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as tx:
            rx.bind(('127.0.0.1',0));rx.settimeout(2)
            a=Reassembler();r=Recorder(folder)
            event=packets(1,7,8,9,0,event_body(score=192),1)
            for part in event+list(reversed(self.parts)):tx.sendto(part,rx.getsockname())
            for _ in range(9):
                payload,peer=rx.recvfrom(2048);result=a.feed(payload,peer)
                if result:r.save(result)
            self.assertEqual(r.saved,2)
            pgm=next(Path(folder).glob('*.pgm')).read_bytes()
            self.assertTrue(pgm.startswith(b'P5\n# SYNTHETIC'))
            self.assertEqual(pgm[-9216:],self.image)
            rows=list(csv.DictReader(io.StringIO((Path(folder)/'events.csv').read_text(encoding='utf-8-sig'))))
            self.assertEqual(rows[0]['score'],'192')
            server=ThreadingHTTPServer(('127.0.0.1',0),dashboard(r,a))
            thread=threading.Thread(target=server.serve_forever);thread.start()
            try:
                url=f'http://127.0.0.1:{server.server_port}'
                with urllib.request.urlopen(url+'/status',timeout=2) as f:status=json.load(f)
                self.assertEqual(status['saved'],2)
                with urllib.request.urlopen(url,timeout=2) as f:self.assertIn(b'SYNTHETIC',f.read())
                with urllib.request.urlopen(url+'/image.bmp',timeout=2) as f:self.assertEqual(f.read()[:2],b'BM')
                self.assertTrue(status['last_image']['synthetic'])
            finally:server.shutdown();server.server_close();thread.join()


class MetricsTests(unittest.TestCase):
    def rows(self):
        return [dict(frame_id=str(i),timestamp_ms=str(i*33),width='1920',height='1080',complete='1',clock_source='camera_input',evidence='synthetic') for i in range(31)]

    def test_synthetic_gate(self):
        with self.assertRaises(ValueError):analyse(self.rows())
        r=analyse(self.rows(),True)
        self.assertAlmostEqual(r['observed_record_fps'],1000/33)
        self.assertFalse(r['continuous_720p30_candidate'])

    def test_gap_not_camera_loss(self):
        rows=self.rows();rows.pop(5)
        self.assertEqual(analyse(rows,True)['unobserved_frame_ids'],1)

    def test_rollover_and_bad_order(self):
        rows=self.rows()[:2];rows[0]['frame_id']='4294967295';rows[1]['frame_id']='0'
        rows[0]['timestamp_ms']='4294967280';rows[1]['timestamp_ms']='17'
        self.assertAlmostEqual(analyse(rows,True)['seconds'],.033)
        rows[1]['frame_id']=rows[0]['frame_id']
        with self.assertRaises(ValueError):analyse(rows,True)

    def test_dump_padding_and_checksum(self):
        image=bytes(2016)+bytes([64])*5184+bytes(2016)
        meta=dict(checksum=sum(image),frame_id=1,timestamp_ms=33,evidence='synthetic')
        self.assertEqual(check(image,meta)['status'],'PASS')
        with self.assertRaises(ValueError):check(b'X'+image[1:],meta)
        with self.assertRaises(ValueError):check(image[:-1],meta)
        meta['checksum']+=1
        with self.assertRaises(ValueError):check(image,meta)

    def test_refresh_wrong_source(self):
        rows=self.rows();rows[0]['clock_source']='hdmi_output'
        with self.assertRaises(ValueError):analyse(rows,True)


if __name__=='__main__':unittest.main(verbosity=2)
