"""Audit the pinned CPU/APB/cache integration facts, without executing the CPU."""
from pathlib import Path
import hashlib,json,re
ROOT=Path(__file__).resolve().parents[1]

def main():
    files={
      'soc':'projects/03_tinyml/ip/sapphire_soc/sapphire_soc.v',
      'header':'projects/03_tinyml/embedded_sw/sapphire_soc_tinyml/bsp/efinix/EfxSapphireSoc/include/soc.h',
      'vendor_cache_api':'projects/03_tinyml/embedded_sw/sapphire_soc_tinyml/software/standalone/driver/vexriscv.h',
      'original_top':'projects/03_tinyml/src/tinyml_soc_top.v',
      'overlay':'projects/06_soc_c2/integration/c2_tinyml_soc_top.v',
      'backend':'team_work/03_ai_soc/c2/c2_sapphire.c',
      'driver_header':'team_work/03_ai_soc/c2/c2_driver.h',
      'apb':'projects/06_soc_c2/rtl/c2_apb_control.sv',
    }
    text={k:(ROOT/v).read_text(encoding='utf-8-sig') for k,v in files.items()}
    checks=[]
    def require(value,label):
        if not value:raise ValueError(label)
        checks.append(label)
    require('output [15:0] io_apbSlave_0_PADDR' in text['soc'],'Vendor APB address is 16 bits')
    require('IO_APB_SLAVE_0_INPUT 0xf8100000' in text['header'],'BSP APB0 aperture is 0xf8100000')
    require('SYSTEM_CORES_0_BYTES_PER_LINE 64' in text['header'],'Pinned D-cache line size is 64 bytes')
    require('data_cache_invalidate_all() asm(".word(0x500F)")' in text['vendor_cache_api'],'Vendor SDK documents the whole-cache custom instruction')
    require("== 32'h0000500f" in text['soc'],'Generated CPU decodes the custom cache instruction')
    require('io_cpu_flush_ready' in text['soc'] and 'dataCache_1_io_cpu_flush_isStall' in text['soc'],
            'CPU instruction stalls until cache flush ready')
    require("DBusCachedPlugin_mmuBus_rsp_physicalAddress & (~ 32'h00ffffff)) == 32'hf8000000" in text['soc'],
            'APB aperture belongs to the generated CPU IO/cache-bypass range')
    require('reg [22:0] ways_0_tags [0:31]' in text['soc'] and
            'tagsWriteCmd_payload_data_address,{tagsWriteCmd_payload_data_error,tagsWriteCmd_payload_data_valid}' in text['soc'],
            'Actual cache tag format contains address/error/valid; tested flusher clears valid bits')
    require('"memory"' in text['backend'] and '.word 0x0000500f' in text['backend'],
            'C backend uses volatile assembly and compiler memory clobber')
    require('wire [15:0] apb_paddr;' in text['overlay'] and 'wire [31:0] apb_pwdata,apb_prdata;' in text['overlay'],
            'Overlay declares APB address/data widths explicitly')
    require(len(re.findall(r'ddr3_top\s*#',text['overlay']))==1,'Overlay contains one DDR controller')
    require('ddr3_top #(.AXI_ID_WIDTH(8))' in text['overlay'],'DDR ID width explicitly matches vendor beta output width')
    require('.s_bid(axi_inter_s0_bid)' in text['overlay'] and '.s_rid(axi_inter_s0_rid)' in text['overlay'],
            'CPU response IDs restored by serializer')
    require(bool(re.search(r'\.io_ddrA_b_payload_resp\s*\(axi_inter_s0_bresp\)',text['overlay'])),
            'CPU write errors are connected rather than discarded')
    require('.m_awvalid(axi_inter_s1_awvalid)' in text['overlay'],'S1 has an actual producer in the separate overlay')
    require('c2_a_video_source #(' in text['overlay'] and '.pixel_vs(c2_pixel_vs)' in text['overlay'] and
            '.shared_now_ms(c2_shared_video_ms)' in text['overlay'],
            'Native top connects source pixels to pinned A capture and shared video time')
    require('c2_sample_valid' not in text['overlay'] and 'c2_sample_timestamp_ms' not in text['overlay'],
            'No external grid/timestamp override bypasses source capture')
    require('c2_video_pipeline #(' in text['overlay'] and '.awvalid(c2_video_awvalid)' in text['overlay'],
            'Native full-frame writer and scan reader connect to the C2 video AXI port')
    require('c3_apb_peripheral c3_peripheral(' in text['overlay'] and
            "wire c3_page=apb_paddr[15:8]==8'h10" in text['overlay'] and
            '.shared_ms(c3_shared_ms),.shared_valid(c3_shared_valid)' in text['overlay'],
            'Native C3 page decoded separately and wired to the same C2 APB clock epoch')
    require('.scl_drive_low(c3_sensor_scl_drive_low)' in text['overlay'] and
            '.sda_drive_low(c3_sensor_sda_drive_low)' in text['overlay'],
            'Native C3 pad interface exports open-drain OE rather than driven high data')
    require('input wire  c2_video_awvalid' not in text['overlay'] and
            '.display_rgb(c2_display_rgb)' in text['overlay'],
            'Video master is internal and display RGB/raster is exposed at the A boundary')
    for name,offset in re.findall(r'#define C2_REG_(\w+) (0x[0-9a-f]+)u',text['driver_header']):
        require(f"16'h{int(offset,16):04x}" in text['apb'],f'APB offset matches C header: {name}')
    manifest=json.loads((ROOT/'projects/06_soc_c2/integration/INTEGRATION_MANIFEST.json').read_text())
    require(manifest['video_input_contract']=='GRAY8_1PPC_VS_HIGH_DE_v1' and
            manifest['timestamp_latch'].startswith('first source DE'), 'Native input/timestamp contract recorded')
    require(manifest['framebuffer']['bank_pitch']*3<=0x1000000 and
            not manifest['framebuffer']['physical_map_verified'], 'Three GRAY8 banks fit provisional video aperture')
    require(hashlib.sha256((ROOT/files['original_top']).read_bytes()).hexdigest()==manifest['baseline_top_sha256'],
            'Original TinyML top identity unchanged after overlay generation')
    record={'status':'PASS','checks':checks,'board_verified':False,'CPU_instruction_execution_simulated':False,
            'cache_scope':'RX-only DMA image slots; global invalidate on pinned core; no generic clean implementation',
            'files':{k:{'path':v,'sha256':hashlib.sha256((ROOT/v).read_bytes()).hexdigest()} for k,v in files.items()}}
    (ROOT/'logs/c2_vendor_audit.json').write_text(json.dumps(record,indent=2)+'\n',encoding='utf-8')
    print(f'PASS C2 vendor/APB/cache audit: {len(checks)} checks; physical mapping and board cache test pending.')

if __name__=='__main__':main()
