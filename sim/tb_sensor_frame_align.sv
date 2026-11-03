`timescale 1ns / 1ps

module tb_sensor_frame_align;
    localparam [31:0] TEST_MAX_AGE_MS = 32'd100;
    reg clk = 1'b0;
    always #5 clk = ~clk;
    reg rst_n = 1'b0;
    reg sample_valid = 1'b0;
    reg [31:0] sample_timestamp_ms = 32'd0;
    reg [15:0] sample_temp = 16'd0;
    reg [15:0] sample_humidity = 16'd0;
    reg frame_valid = 1'b0;
    reg [31:0] frame_timestamp_ms = 32'd0;
    wire pair_valid, stale;
    wire [31:0] pair_frame_timestamp_ms, pair_sample_timestamp_ms, pair_age_ms;
    wire [15:0] pair_temp, pair_humidity;

    sensor_frame_align #(.MAX_AGE_MS(TEST_MAX_AGE_MS)) dut (
        .clk(clk), .rst_n(rst_n),
        .sample_valid(sample_valid), .sample_timestamp_ms(sample_timestamp_ms),
        .sample_temp(sample_temp), .sample_humidity(sample_humidity),
        .frame_valid(frame_valid), .frame_timestamp_ms(frame_timestamp_ms),
        .pair_valid(pair_valid), .stale(stale),
        .pair_frame_timestamp_ms(pair_frame_timestamp_ms),
        .pair_sample_timestamp_ms(pair_sample_timestamp_ms), .pair_age_ms(pair_age_ms),
        .pair_temp(pair_temp), .pair_humidity(pair_humidity)
    );

    bit model_seen = 0;
    reg [31:0] model_timestamp = 0;
    reg [15:0] model_temp = 0;
    reg [15:0] model_humidity = 0;
    bit expected_valid = 0, expected_stale = 0;
    reg [31:0] expected_frame = 0, expected_sample = 0, expected_age = 0;
    reg [15:0] expected_temp = 0, expected_humidity = 0;
    integer checks = 0;
    integer accepted = 0;
    integer rejected = 0;
    integer resets = 0;
    integer seed = 32'h5310_2026;
    integer i;
    reg [31:0] random_sample_ts, random_frame_ts;
    reg [31:0] random_choice;
    reg [15:0] random_temp, random_humidity;

    task automatic cycle (
        input bit reset_active,
        input bit sv,
        input reg [31:0] st,
        input reg [15:0] temp,
        input reg [15:0] humidity,
        input bit fv,
        input reg [31:0] ft,
        input string label
    );
        reg [63:0] reference_delta;
        begin
            @(negedge clk);
            rst_n = !reset_active;
            sample_valid = sv;
            sample_timestamp_ms = st;
            sample_temp = temp;
            sample_humidity = humidity;
            frame_valid = fv;
            frame_timestamp_ms = ft;
            if (reset_active) begin
                model_seen = 0;
                model_timestamp = 0;
                model_temp = 0;
                model_humidity = 0;
                expected_valid = 0;
                expected_stale = 0;
                expected_frame = 0;
                expected_sample = 0;
                expected_age = 0;
                expected_temp = 0;
                expected_humidity = 0;
                resets = resets + 1;
            end else begin
                expected_valid = 0;
                expected_stale = 0;
                if (sv) begin
                    model_seen = 1;
                    model_timestamp = st;
                    model_temp = temp;
                    model_humidity = humidity;
                end
                if (fv) begin
                    expected_frame = ft;
                    if (model_seen) begin
                        // Mathematical reference uses 64-bit arithmetic and modulo 2^32.
                        reference_delta = (64'd4294967296 + {32'd0, ft} -
                                           {32'd0, model_timestamp}) % 64'd4294967296;
                        expected_sample = model_timestamp;
                        expected_age = reference_delta[31:0];
                        expected_temp = model_temp;
                        expected_humidity = model_humidity;
                        expected_valid = reference_delta < 64'd2147483648 &&
                                         reference_delta <= TEST_MAX_AGE_MS;
                    end else begin
                        expected_sample = 0;
                        expected_age = 0;
                        expected_temp = 0;
                        expected_humidity = 0;
                    end
                    expected_stale = !expected_valid;
                    if (expected_valid) accepted = accepted + 1;
                    else rejected = rejected + 1;
                end
            end
            @(posedge clk);
            #1;
            checks = checks + 1;
            if (pair_valid !== expected_valid || stale !== expected_stale ||
                pair_frame_timestamp_ms !== expected_frame ||
                pair_sample_timestamp_ms !== expected_sample ||
                pair_age_ms !== expected_age || pair_temp !== expected_temp ||
                pair_humidity !== expected_humidity) begin
                $display("FAIL label=%s check=%0d rst_n=%b sample_valid=%b frame_valid=%b", label, checks, rst_n, sv, fv);
                $display("expected valid=%b stale=%b frame=%h sample=%h age=%h temp=%h humidity=%h",
                         expected_valid, expected_stale, expected_frame, expected_sample,
                         expected_age, expected_temp, expected_humidity);
                $display("actual   valid=%b stale=%b frame=%h sample=%h age=%h temp=%h humidity=%h",
                         pair_valid, stale, pair_frame_timestamp_ms, pair_sample_timestamp_ms,
                         pair_age_ms, pair_temp, pair_humidity);
                $fatal(1, "sensor_frame_align mismatch");
            end
        end
    endtask

    task automatic check_async_reset;
        begin
            @(negedge clk);
            #2;
            rst_n = 0;
            #1; // Check before the next rising edge: reset is asynchronous.
            checks = checks + 1;
            resets = resets + 1;
            if (pair_valid !== 1'b0 || stale !== 1'b0 ||
                pair_frame_timestamp_ms !== 32'd0 ||
                pair_sample_timestamp_ms !== 32'd0 || pair_age_ms !== 32'd0 ||
                pair_temp !== 16'd0 || pair_humidity !== 16'd0)
                $fatal(1, "asynchronous reset did not clear outputs before clock edge");
            model_seen = 0;
            model_timestamp = 0;
            model_temp = 0;
            model_humidity = 0;
            expected_valid = 0;
            expected_stale = 0;
            expected_frame = 0;
            expected_sample = 0;
            expected_age = 0;
            expected_temp = 0;
            expected_humidity = 0;
        end
    endtask

    initial begin
        cycle(1, 0, 0, 0, 0, 0, 0, "initial_reset");
        cycle(0, 0, 0, 0, 0, 1, 0, "zero_timestamp_without_observed_sample");
        cycle(0, 0, 0, 0, 0, 1, 500, "nonzero_timestamp_without_observed_sample");
        cycle(0, 1, 1000, 2500, 6000, 0, 0, "sample_only");
        cycle(0, 0, 0, 0, 0, 1, 1000, "age_zero");
        cycle(0, 0, 0, 0, 0, 1, 1099, "one_before_max_age");
        cycle(0, 0, 0, 0, 0, 1, 1100, "exact_max_age");
        cycle(0, 0, 0, 0, 0, 1, 1101, "one_after_max_age");
        cycle(0, 0, 0, 0, 0, 1, 999, "future_sample_one_ms");
        cycle(0, 0, 0, 0, 0, 0, 0, "idle_clears_pulses_keeps_snapshot");
        cycle(0, 1, 2000, 2600, 6100, 1, 2003, "same_cycle_new_sample_priority");
        cycle(0, 1, 2010, 2700, 6200, 1, 2009, "same_cycle_future_sample_rejected_no_fallback");
        cycle(0, 1, 32'hfffffff0, 2800, 6300, 1, 32'h00000014, "rollover_age_36");
        cycle(0, 0, 0, 0, 0, 1, 32'h00000054, "rollover_exact_age_100");
        cycle(0, 0, 0, 0, 0, 1, 32'h00000055, "rollover_age_101");
        cycle(0, 1, 32'h00000014, 2900, 6400, 1, 32'hfffffff0, "future_across_rollover");
        cycle(0, 1, 32'h00000000, 3000, 6500, 1, 32'h80000000, "half_range_ambiguous_rejected");
        cycle(0, 0, 0, 0, 0, 1, 32'h7fffffff, "old_half_range_minus_one_rejected_by_max_age");
        cycle(0, 1, 32'hffffffff, 3100, 6600, 1, 32'h00000000, "rollover_age_one");
        cycle(1, 1, 9000, 4000, 7000, 1, 9000, "reset_wins_over_valid_inputs");
        cycle(0, 0, 0, 0, 0, 1, 0, "reset_discards_previous_sample");
        cycle(0, 1, 0, 0, 0, 1, 0, "observed_zero_sample_is_valid");
        cycle(0, 1, 80000, 3200, 6700, 1, 80001, "nonzero_snapshot_before_async_reset");
        check_async_reset();
        cycle(0, 0, 0, 0, 0, 1, 0, "async_reset_discards_previous_sample");

        for (i = 0; i < 2000; i = i + 1) begin
            random_choice = $random(seed);
            random_sample_ts = $random(seed);
            random_temp = $random(seed);
            random_humidity = $random(seed);
            if (!random_choice[0]) random_sample_ts = model_timestamp;
            case (random_choice[4:2])
                0: random_frame_ts = random_sample_ts;
                1: random_frame_ts = random_sample_ts + 32'd99;
                2: random_frame_ts = random_sample_ts + 32'd100;
                3: random_frame_ts = random_sample_ts + 32'd101;
                4: random_frame_ts = random_sample_ts - 32'd1;
                5: random_frame_ts = random_sample_ts + 32'h80000000;
                6: random_frame_ts = $random(seed);
                7: random_frame_ts = random_sample_ts + 32'd1;
            endcase
            cycle((i % 137) == 136, random_choice[0], random_sample_ts,
                  random_temp, random_humidity, random_choice[1], random_frame_ts, "seeded_random");
        end
        cycle(0, 0, 0, 0, 0, 0, 0, "final_idle");
        if (accepted == 0 || rejected == 0 || resets < 3)
            $fatal(1, "coverage counters unexpectedly empty");
        $display("PASS tb_sensor_frame_align checks=%0d accepted=%0d rejected=%0d resets=%0d seeded_random_cycles=2000",
                 checks, accepted, rejected, resets);
        $finish;
    end

    initial begin
        #100000;
        $fatal(1, "watchdog timeout");
    end
endmodule
