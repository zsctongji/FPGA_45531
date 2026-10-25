# FPGA A/B/C handoff snapshot

Source: FPGA_2026_T3_P3; snapshot updated 2026-10-24. Existing A-side commits from GitHub are preserved.

- A: projects/02_camera, 04_camera_preprocess, 05_camera_motion; team_work/01_video.
- B: team_work/02_sensors_alarm; no additional completed sensor/network source directory is asserted by this snapshot.
- C: projects/03_tinyml (including embedded_sw); team_work/03_ai_soc; firmware.
- C2: projects/06_soc_c2; vendor AXI adapters, APB control/CDC, RX-only CPU cache backend and native SoC synthesis overlay. See team_work/03_ai_soc/C2_VENDOR_APB_CACHE.md.
- Shared: rtl, sim, team_work/shared, docs, config/hardware.json, tools scripts, logs.
- projects/01_led is the hardware bring-up baseline.
- firmware and fpga_bitstreams contain available paired artifacts and their original instructions. CPU HEX is not an FPGA configuration file.

Tool installations, vendor archives, original vendor project collections, reference PDFs and generated build caches are excluded. Install compatible Efinity, RISC-V GCC and simulation tools separately at the locations expected by the scripts. Some preparation scripts also require the original vendor packages; see the existing source documentation. Original logs retain historical machine paths and test dates; this snapshot does not represent a fresh build or board test.

Third-party source/IP and libraries embedded inside projects retain their existing notices. No new blanket license is applied. Their distribution terms must be checked before public release; this handoff does not establish redistribution permission.

See HANDOFF_MANIFEST.json for copied source paths, sizes and SHA-256 hashes. Existing baseline projects are preserved; team_work contains responsibility/interface documents, not completed integrated hardware.

## C-side PC validation added in this update

- C1 diagnostic firmware and UART acceptance tools: 11_build_c1.cmd; firmware/c1_static_person_detect; no board inference claim.
- C2: 13_test_c2.cmd runs 34 RTL simulations, host driver checks (1,923 assertions / 102 frames), vendor cache-tag flush checks, and RV32 object/instruction checks. Results: logs/c2_selftest.json, logs/c2_riscv_compile.json.
- 15_synth_c2_native.cmd generates and synthesizes a separate native CPU/TinyML/single-DDR overlay. Efinity map passed; video IP, pin assignments, physical mapping, timing/CDC signoff and board cache coherence remain unverified. Vendor warnings are retained in logs/c2_native_warning_review.json.
- C4: 12_test_c4_pc.cmd; desktop model replay and compatibility-copy audit. The original board model is preserved; camera preprocessing policy is still pending A/C validation.

Generated tool installations, build caches, synthesis netlists and private SSH configuration are excluded. Logs/manifests describe the original development run, not a fresh GitHub checkout. Historical absolute paths and Git line-ending conversion can affect recorded hashes; install the required local tools and regenerate/rebuild from this checkout before treating it as a new verification run. The C2 preparation script regenerates its absolute-path integration overlay.

## 2026-10-25 C2/C3/C24 update

Current APB transport is v2.2 (0x00020002); firmware and hardware versions must match.
A mailbox -> C2 source/DDR completion fence, common APB time, checked C3 time API,
C24 firmware and UART acceptance tools are included. Start with
team_work/03_ai_soc/TIME_AND_C24_ACCEPTANCE.md and 18_test_time_c24.cmd.

The source machine recorded 42 RTL runs, 38 parser/CLI tests, vendor formatter checks
and 666 package identity checks PASS; no board/camera execution or physical timing
signoff is asserted. Default firmware disables live MMIO. Generated native map
outputs and tool installations are excluded; historical reports retain original
absolute paths. Rebuild reports on the receiving machine before claiming a local
verification. Primary C24 sources are included; tools/prepare_c24.py recreates its
generated SDK application from the existing vendor baseline.

## Source-pixel capture update

The native top now accepts one-pixel GRAY8/VS/DE and instantiates A's unchanged
capture/sampler. The common timestamp is latched at the first source DE pixel,
then preserved through delayed EOF and DDR descriptors. APB remains v2.2.
See team_work/03_ai_soc/SOURCE_VIDEO_CAPTURE.md and 19_test_video_capture.cmd.
The source machine passed 46 RTL runs, native map and 678 package identity checks;
physical MIPI/HDMI, DDR mapping, PNR and board acceptance remain pending.

## Full-frame video update

The native top internally connects a GRAY8 triple framebuffer writer and raster
scanout to C2's video AXI port. CPU S0, C2 S1 and TinyML S2 share one DDR controller.
See team_work/03_ai_soc/VIDEO_FRAMEBUFFER_HANDOFF.md and 20_test_video_framebuffer.cmd
for byte addresses, stride, first-DE timestamps, final BRESP fences and frame roles.
The source machine passed 49 RTL runs including full-HD read/write/display and
concurrent video/AI/CPU/TinyML fault/recovery tests. CPU/TinyML traffic in functional
tests is synthetic; native map includes real CPU/accelerator logic. Board execution,
physical MIPI/HDMI, legacy two-pixel adaptation, PNR, CDC and bandwidth remain open.
Default live MMIO stays disabled; inherited vendor warnings remain documented.
