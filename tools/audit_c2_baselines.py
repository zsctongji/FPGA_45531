"""Recheck the exact baseline facts used by the C2 integration proposal."""
from pathlib import Path
from datetime import datetime, timezone
import hashlib
import json
import re

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'projects/06_soc_c2'


def main():
    files = {
        'tinyml_top': 'projects/03_tinyml/src/tinyml_soc_top.v',
        'ddr_parameters': 'projects/03_tinyml/src/ddr3_controller/ddr3_parameter.vh',
        'vendor_interconnect': 'projects/03_tinyml/src/axi/axi_interconnect_beta/axi_interconnect_beta.sv',
        'video_top': 'projects/05_camera_motion/rtl/ti60f225_oob_top.v',
        'linker': 'projects/03_tinyml/embedded_sw/sapphire_soc_tinyml/bsp/efinix/EfxSapphireSoc/linker/default.ld',
        'soc_header': 'projects/03_tinyml/embedded_sw/sapphire_soc_tinyml/bsp/efinix/EfxSapphireSoc/include/soc.h',
        'software_abi': 'team_work/shared/include/cooperation_v1.h',
    }
    texts = {key: (ROOT / name).read_text(encoding='utf-8-sig') for key, name in files.items()}
    checks = []

    def require(test, label):
        if not test:
            raise ValueError('C2 baseline changed, review assumptions: ' + label)
        checks.append(label)

    def parameter(name):
        return int(re.search(r'`define\s+' + name + r'\s+(\d+)', texts['ddr_parameters']).group(1))

    require(bool(re.search(r'ddr3_top\s+u_ddr3_top', texts['tinyml_top'])), 'TinyML single DDR instance identified')
    require(bool(re.search(r'\.S_COUNT\s*\(3\s*\)', texts['tinyml_top'])), 'Vendor interconnect has three source slots')
    # In this baseline S1 request signals occur only in declaration and concatenation.
    for name in ['axi_inter_s1_awvalid', 'axi_inter_s1_arvalid', 'axi_inter_s1_awaddr']:
        require(len(re.findall(r'\b' + name + r'\b', texts['tinyml_top'])) == 2,
                name + ' has no top-level producer connection')
    require(bool(re.search(r'ram\s*\(wxai!r\)\s*:\s*ORIGIN\s*=\s*0x00001000,\s*LENGTH\s*=\s*128M', texts['linker'])),
            'CPU linker starts 0x1000 and spans 128 MiB')
    for name, value in [('I_VID_WIDTH', '32'), ('O_VID_WIDTH', '16'), ('BURST_LEN', '127'),
                        ('FB_NUM', '3'), ('MAX_VID_WIDTH', '960'), ('MAX_VID_HIGHT', '1080')]:
        require(bool(re.search(r'\.' + name + r'\s*\(\s*' + value + r'\s*\)', texts['video_top'])),
                'Video frame-buffer parameter ' + name + '=' + value)
    require(bool(re.search(r"\.START_ADDR\s*\(\s*32'h00000\s*\)", texts['video_top'])), 'Video default DDR base is zero (CPU overlap risk)')
    require(parameter('AXI_DATA_WIDTH') == 128, 'DDR AXI is 128 bits')
    for name, value in [('COOP_ABI_VERSION', '0x00010000'), ('COOP_IMAGE_W', '96'),
                        ('COOP_IMAGE_H', '96'), ('COOP_IMAGE0_OFFSET', '0x1000'),
                        ('COOP_IMAGE1_OFFSET', '0x4000'), ('COOP_FORMAT_GRAY8', '1')]:
        require(bool(re.search(r'#define\s+' + name + r'\s+' + value + r'u\b', texts['software_abi'])),
                'RTL ABI constant matches ' + name)
    fields = re.search(r'typedef struct\s*\{([^}]+)\}\s*coop_frame_t;', texts['software_abi']).group(1)
    names = re.sub(r'\buint32_t\b', '', fields)
    require(re.findall(r'\b[a-z][a-z0-9_]*\b', names) ==
            ['abi_version', 'frame_id', 'timestamp_ms', 'buffer_id', 'data_offset', 'data_bytes',
             'format', 'stride', 'checksum_fnv1a', 'valid_flags', 'motion_count', 'bbox_x0',
             'bbox_y0', 'bbox_x1', 'bbox_y1', 'reserved'], 'All sixteen ABI words match RTL bit positions')
    geometry = {key: parameter(key) for key in ['ROW_WIDTH', 'COL_WIDTH', 'BANK_WIDTH', 'RANKS', 'DQ_WIDTH', 'AXI_ID_WIDTH', 'CK_RATIO', 'ASYN_AXI_CLK']}
    capacity = (1 << (geometry['ROW_WIDTH'] + geometry['COL_WIDTH'] + geometry['BANK_WIDTH'])) * geometry['RANKS'] * geometry['DQ_WIDTH'] // 8
    require(capacity == 256 * 1024 * 1024, 'Reference DDR geometry computes to 256 MiB; physical device unconfirmed')
    audit = {
        'status': 'PASS', 'generated': datetime.now(timezone.utc).isoformat(),
        'checks': checks, 'geometry': geometry, 'reference_capacity_bytes': capacity,
        'physical_capacity_verified': False, 'address_translation_verified': False,
        'files': {key: {'path': name, 'sha256': hashlib.sha256((ROOT / name).read_bytes()).hexdigest()}
                  for key, name in files.items()},
        'risks': ['S1 is reserved but not a connected video/DMA path',
                  'Video START_ADDR=0 overlaps CPU allocation; relocation and translation proof required',
                  'Top-level interconnect IDs are 8 bits while DDR parameter AXI_ID_WIDTH is 4; adapter review required',
                  'APB control-page wiring and cache policy remain unimplemented',
                  'Portable arbiter is ID-less and globally serialized; vendor CPU/TinyML compatibility unproven'],
    }
    regions = [
        {'name': 'cpu_linker', 'start': 0x1000, 'size': 128 * 1024 * 1024},
        {'name': 'video_candidate', 'start': 0x08010000, 'size': 16 * 1024 * 1024},
        {'name': 'shared_candidate', 'start': 0x09010000, 'size': 64 * 1024},
    ]
    for previous, current in zip(regions, regions[1:]):
        require(previous['start'] + previous['size'] <= current['start'], 'Candidate regions do not overlap')
    require(regions[-1]['start'] + regions[-1]['size'] <= capacity, 'Candidate regions fit reference geometry')
    (PROJECT / 'BASELINE_AUDIT.json').write_text(json.dumps(audit, indent=2) + '\n', encoding='utf-8')
    for region in regions:
        region['end_exclusive'] = region['start'] + region['size']
        region['start_hex'] = hex(region['start'])
        region['end_exclusive_hex'] = hex(region['end_exclusive'])
    plan = {
        'status': 'PROPOSAL_ONLY', 'enabled_in_firmware_or_baselines': False,
        'address_domain': 'candidate common linear byte map; CPU-to-DDR translation NOT established',
        'reference_capacity_bytes': capacity, 'physical_capacity_verified': False,
        'regions': regions, 'legacy_A_RAW_reference_bytes': 960 * 1080 * 4 * 3,
        'video_reference_bytes': 2076672*3,
        'integrated_video': {'format':'GRAY8','width':1920,'height':1080,'stride':1920,
                             'frame_bytes':2073600,'bank_pitch':2076672,'banks':3,
                             'relative_bank_bases':[0,2076672,4153344],
                             'display_format':'RGB888, gray replicated to R/G/B',
                             'selection':'oldest READY on display VS; else repeat DISPLAY',
                             'drop_policy':'no FREE bank: drain and drop whole new source frame',
                             'completion':'A next-VS verdict and all AXI write responses OKAY'},
        'image_offsets': [0x1000, 0x4000], 'image_bytes': 9216,
        'simulation_shared_base': 0,
        'required_before_enable': ['physical DDR capacity', 'CPU/DDRx address translation and alias test',
                                   'video frame-buffer address-unit and stride audit',
                                   'CPU cache maintenance or verified uncached region',
                                   'APB control service and DMA release/acquire barriers'],
    }
    (PROJECT / 'memory_plan.json').write_text(json.dumps(plan, indent=2) + '\n', encoding='utf-8')
    print(f'PASS C2 baseline audit: {len(checks)} checks; memory plan remains disabled/provisional')


if __name__ == '__main__':
    main()
