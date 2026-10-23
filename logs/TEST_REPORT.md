# 模块真实测试记录

更新日期：2026-10-19。全部十二项自检已从 D 盘通过项目内 Icarus 实际运行。机器可读记录为 `selftest.json`，含 RTL 和测试台 SHA256；`selftest_events.json` 明确标为该次完整运行的五项子集，早期单独运行记录保存在 history。原六项曾在 Vivado XSim 2018.3 通过，记录保留在 selftest_xsim.json。

| 测试台 | 实际结果 |
|---|---|
| tb_pixel_ops | PASS tb_pixel_ops: gray=3077, binary=3076, thresholds=0/127/128/255, valid_gaps=2334, reset_and_markers=checked |
| tb_vision_stream | PASS tb_vision_stream: gray=516, binary=515, Sobel=280, frames=8, lines=40, valid_gaps=386, zero/intermediate/saturated=97/73/110<br>PASS stream coverage: continuous_frames, random_valid_gaps, input_border_suppression, regenerated_markers, reset_midframe, stale_line_memory_recovery |
| tb_sobel_3x3 | PASS tb_sobel_3x3: minimum_size=3x3, consecutive_frames=2, one_pixel_per_output_frame, all_markers, saturation, threshold_255_equality, valid_gaps |
| tb_sobel_720p | PASS tb_sobel_720p: size=1280x720, frames=2, gray=1843200, binary=1843200, Sobel=1835208, lines=1436, gradient_pixels=3992, valid_gaps=119<br>PASS 720p functional coverage: vertical_step, horizontal_step, consecutive_frames, cropped_border, frame_and_line_markers; no hardware_fps_claim |
| tb_sensor_smooth | PASS tb_sensor_smooth checks=27 plus consecutive cases |
| tb_sensor_frame_align | PASS tb_sensor_frame_align checks=2026 accepted=518 rejected=502 resets=17 seeded_random_cycles=2000 |
| tb_video_display_preprocess | PASS tb_video_display_preprocess cycles=1507 active=975 blanks=532 resets=2 modes=RGB/gray/binary control_latency=2 |
| tb_frame_motion_stats | PASS tb_frame_motion_stats frames=77 malformed=4 random_frames=64 threshold_edges bbox gaps reset back_to_back |
| tb_multimodal_alarm | PASS tb_multimodal_alarm checks=45 events=7 weighted_score freshness future missing duplicate order rollover confirm hold ack disarm |
| tb_video_motion_display | PASS tb_video_motion_display cycles=903 complete_frames=9 format_errors=12 red_pixels=103 sampled_grid=4x3 invalid_width/extra_row/missing_row marker_alignment hold_frames=2 |
| tb_motion_minimum | PASS tb_motion_minimum grid=1x1 first_frame_invalid threshold_equal static SOF_EOF_same_sample |
| tb_motion_1080p | PASS tb_motion_1080p frames=2 input_pixels=4147200 grid_samples=10368 grid=96x54 changed=32 diff_sum=768 bbox=0/0/95/53 ignored_non_grid_pixels |

另有 `tb_key_detect` 按键自检，已通过短按、抖动、复位、释放及两次完整按键检查；由 `08_test_led_key.cmd` 单独运行。

五个独立 FPGA 工程均实际通过 Efinity 完整流程，记录在 efinity_*_compile.json；第五个运动红框工程最终 setup/hold 为 0.534/0.026 ns。资源和最终报告在 current_status.md 及 verified_artifacts.json。CPU 静态人体检测和引导 ROM 也已实际构建。

功能仿真和独立工程编译不能证明实体摄像头帧率、板上 AI、完整三路融合、传感器温度准确度或物理报警通过。厂家约束存在未匹配端口告警，最终时序检查仅覆盖工具成功应用的约束，仍待实物核验。

运行脚本在启动时使旧结果失效，并检查进程退出码、FAIL/FATAL 和测试台 PASS 标记；工具缺失或测试失败会记录 FAIL。
