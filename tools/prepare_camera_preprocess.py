"""Create a working camera copy and insert preprocessing before TMDS encoding."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
source = root / "projects/02_camera"
target = root / "projects/04_camera_preprocess"
if not source.is_dir():
    raise FileNotFoundError(source)
if target.exists():
    raise FileExistsError(f"Refusing to overwrite existing project: {target}")

ignored = {"outflow", "work_syn", "work_pnr", "work_pt", "work_sim", "__pycache__"}
shutil.copytree(source, target, ignore=lambda d, n: [x for x in n if x in ignored])
top = target / "rtl/ti60f225_oob_top.v"
data = top.read_bytes()
data, count = re.subn(
    rb"module ti60f225_oob_top #\(",
    b"module ti60f225_oob_top #(\r\n"
    b"    parameter integer DISPLAY_MODE = 1, // 0 RGB, 1 gray, 2 binary\r\n"
    b"    parameter integer DISPLAY_THRESHOLD = 128,\r\n",
    data, count=1,
)
if count != 1:
    raise ValueError("Top-module parameter anchor missing.")
anchor = b"dvi_encoder dvi_encoder_m0"
if data.count(anchor) != 1:
    raise ValueError("Unexpected number of DVI encoders.")
insert = b"""
// Preprocessing follows the vendor gamma/color selection in the HDMI clock domain.
wire [7:0] preprocess_r, preprocess_g, preprocess_b;
wire preprocess_hs, preprocess_vs, preprocess_de;
video_display_preprocess #(.MODE(DISPLAY_MODE), .THRESHOLD(DISPLAY_THRESHOLD))
inst_display_preprocess (
    .clk(hdmi_tx_slow_clk), .rst_n(vid_rst_n),
    .in_r(gamma_sel ? gamma_rdata : hdmi_tx_bdata),
    .in_g(gamma_sel ? gamma_gdata : hdmi_tx_gdata),
    .in_b(gamma_sel ? gamma_bdata : hdmi_tx_rdata),
    .in_hs(gamma_sel ? gamma_hs : hdmi_tx_hs),
    .in_vs(gamma_sel ? gamma_vs : hdmi_tx_vs),
    .in_de(gamma_sel ? gamma_valid : hdmi_tx_de),
    .out_r(preprocess_r), .out_g(preprocess_g), .out_b(preprocess_b),
    .out_hs(preprocess_hs), .out_vs(preprocess_vs), .out_de(preprocess_de)
);

""".replace(b"\n", b"\r\n")
before, after = data.split(anchor)
port_text, tail = after.split(b".video_format", 1)
for name, signal in [("rdata", "r"), ("gdata", "g"), ("bdata", "b"),
                     ("hs", "hs"), ("vs", "vs"), ("de", "de")]:
    pattern = rb"(\.i_" + name.encode() + rb"\s*)\([^)]*\)"
    port_text, count = re.subn(pattern, lambda m: m[1] + b"(preprocess_" + signal.encode() + b")", port_text)
    if count != 1:
        raise ValueError(f"Unexpected encoder port count: {name}")
top.write_bytes(before + insert + anchor + port_text + b".video_format" + tail)

files = ["rgb888_to_gray.v", "gray_threshold.v", "video_display_preprocess.v"]
for name in files:
    shutil.copy2(root / "rtl" / name, target / "rtl" / name)
xml_path = target / "ti60f225_oob.xml"
ns = "http://www.efinixinc.com/enf_proj"
tree = ET.parse(xml_path)
design = tree.getroot().find(f"{{{ns}}}design_info")
# The native reader validates the XSD sequence: design_file precedes top_vhdl_arch.
insert_index = max(i for i, element in enumerate(design) if element.tag == f"{{{ns}}}design_file") + 1
for offset, name in enumerate(files):
    element = ET.Element(f"{{{ns}}}design_file", name=f"rtl/{name}", version="default", library="default")
    element.tail = "\n        "
    design.insert(insert_index + offset, element)
ET.register_namespace("efx", ns)
ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")
tree.write(xml_path, encoding="utf-8", xml_declaration=True)

digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
peri_name = "ti60f225_oob.peri.xml"
record = {
    "source_project": str(source), "working_project": str(target),
    "display_mode": 1, "threshold": 128, "pipeline_latency_registers": 2,
    "vendor_resolution": "1920x1080 (unchanged; not physically measured)",
    "source_top_sha256": digest(source / "rtl/ti60f225_oob_top.v"),
    "modified_top_sha256": digest(top),
    "peripheral_file_identical": digest(source / peri_name) == digest(target / peri_name),
    "peripheral_sha256": digest(target / peri_name),
    "source_files_present": all((target / x.attrib["name"]).is_file() for x in design.findall(f"{{{ns}}}design_file")),
    "board_test_passed": False,
}
(target / "PREPARATION_RECORD.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps(record, indent=2))
