"""Create an independent grayscale camera + frame-difference red-border project."""
from pathlib import Path
import hashlib
import json
import re
import shutil
import xml.etree.ElementTree as ET

root = Path(__file__).resolve().parents[1]
source = root / "projects/04_camera_preprocess"
target = root / "projects/05_camera_motion"
if not source.is_dir():
    raise FileNotFoundError(source)
if target.exists():
    raise FileExistsError(f"Refusing to overwrite {target}")
ignored = {"outflow", "work_syn", "work_pnr", "work_pt", "work_sim", "__pycache__"}
shutil.copytree(source, target, ignore=lambda d, names: [n for n in names if n in ignored])
top = target / "rtl/ti60f225_oob_top.v"
data = top.read_bytes()
data, n = re.subn(rb"    parameter integer DISPLAY_MODE = 1, // 0 RGB, 1 gray, 2 binary\r?\n", b"", data)
assert n == 1
assert data.count(b".MODE(DISPLAY_MODE)") == 1
data = data.replace(b".MODE(DISPLAY_MODE)", b".MODE(1)")
anchor = b"dvi_encoder dvi_encoder_m0"
assert data.count(anchor) == 1
insert = b"""
// Independent motion-only bring-up path. AI/thermal/environment are not connected here.
wire [7:0] motion_r, motion_g, motion_b;
wire motion_hs, motion_vs, motion_de;
video_motion_display #(
    .FRAME_WIDTH(HACT), .FRAME_HEIGHT(VACT), .STEP_X(20), .STEP_Y(20),
    .DIFF_THRESHOLD(24), .MIN_CHANGED(32), .HOLD_FRAMES(15), .BORDER(4)
) inst_motion_display (
    .clk(hdmi_tx_slow_clk), .rst_n(vid_rst_n),
    .in_hs(preprocess_hs), .in_vs(preprocess_vs), .in_de(preprocess_de), .in_gray(preprocess_r),
    .out_hs(motion_hs), .out_vs(motion_vs), .out_de(motion_de),
    .out_r(motion_r), .out_g(motion_g), .out_b(motion_b),
    .stats_valid(), .comparison_valid(), .motion_detected(), .frame_error(),
    .changed_count(), .motion_alarm()
);

""".replace(b"\n", b"\r\n")
before, after = data.split(anchor)
port_text, tail = after.split(b".video_format", 1)
for suffix in ("r", "g", "b", "hs", "vs", "de"):
    assert port_text.count(b"(preprocess_" + suffix.encode() + b")") == 1
    port_text = port_text.replace(b"(preprocess_" + suffix.encode() + b")", b"(motion_" + suffix.encode() + b")")
top.write_bytes(before + insert + anchor + port_text + b".video_format" + tail)
files = ["frame_motion_stats.v", "video_grid_sampler.v", "video_motion_display.v"]
for name in files:
    shutil.copy2(root / "rtl" / name, target / "rtl" / name)
ns = "http://www.efinixinc.com/enf_proj"
xml = target / "ti60f225_oob.xml"
tree = ET.parse(xml)
design = tree.getroot().find(f"{{{ns}}}design_info")
index = max(i for i, child in enumerate(design) if child.tag == f"{{{ns}}}design_file") + 1
for offset, name in enumerate(files):
    element = ET.Element(f"{{{ns}}}design_file", name=f"rtl/{name}", version="default", library="default")
    element.tail = "\n        "
    design.insert(index + offset, element)
ET.register_namespace("efx", ns)
ET.register_namespace("xsi", "http://www.w3.org/2001/XMLSchema-instance")
tree.write(xml, encoding="utf-8", xml_declaration=True)
digest = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
peri = "ti60f225_oob.peri.xml"
record = {
    "source_project": str(source), "working_project": str(target),
    "display_mode": "grayscale plus motion-only red border",
    "video_dimensions": [1920, 1080], "grid_dimensions": [96, 54],
    "difference_threshold": 24, "minimum_changed_samples": 32,
    "hold_frames": 15, "border_pixels": 4,
    "additional_display_latency_registers": 1,
    "source_top_sha256": digest(source / "rtl/ti60f225_oob_top.v"),
    "modified_top_sha256": digest(top),
    "source_files_present": all((target / e.attrib["name"]).is_file() for e in design.findall(f"{{{ns}}}design_file")),
    "peripheral_file_identical": digest(source / peri) == digest(target / peri),
    "peripheral_sha256": digest(target / peri),
    "live_ai_connected": False, "thermal_environment_connected": False,
    "board_test_passed": False,
}
assert record["source_files_present"] and record["peripheral_file_identical"]
(target / "PREPARATION_RECORD.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
print(json.dumps(record, indent=2))
