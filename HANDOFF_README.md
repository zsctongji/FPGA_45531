# FPGA A/B/C handoff snapshot

Source: FPGA_2026_T3_P3; snapshot prepared 2026-10-23.

- A: projects/02_camera, 04_camera_preprocess, 05_camera_motion; team_work/01_video.
- B: team_work/02_sensors_alarm; no additional completed sensor/network source directory is asserted by this snapshot.
- C: projects/03_tinyml (including embedded_sw); team_work/03_ai_soc; firmware.
- Shared: rtl, sim, team_work/shared, docs, config/hardware.json, tools scripts, logs.
- projects/01_led is the hardware bring-up baseline.
- firmware and fpga_bitstreams contain available paired artifacts and their original instructions. CPU HEX is not an FPGA configuration file.

Tool installations, vendor archives, original vendor project collections, reference PDFs and generated build caches are excluded. Install compatible Efinity, RISC-V GCC and simulation tools separately at the locations expected by the scripts. Some preparation scripts also require the original vendor packages; see the existing source documentation. Original logs retain historical machine paths and test dates; this snapshot does not represent a fresh build or board test.

Third-party source/IP and libraries embedded inside projects retain their existing notices. No new blanket license is applied. Their distribution terms must be checked before public release; this handoff does not establish redistribution permission.

See HANDOFF_MANIFEST.json for copied source paths, sizes and SHA-256 hashes. Existing baseline projects are preserved; team_work contains responsibility/interface documents, not completed integrated hardware.
