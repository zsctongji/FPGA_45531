`timescale 1ns / 1ps

module tb_pixel_ops;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg in_valid = 0;
    reg in_sof = 0, in_sol = 0, in_eol = 0, in_eof = 0;
    reg [7:0] r = 0, g = 0, b = 0;
    wire gv;
    wire [3:0] gf;
    wire [7:0] gray;
    wire [3:0] tv;
    wire [3:0] tf0, tf127, tf128, tf255;
    wire [7:0] mask0, mask127, mask128, mask255;

    rgb888_to_gray dut_gray (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid),
        .in_sof(in_sof), .in_sol(in_sol), .in_eol(in_eol), .in_eof(in_eof),
        .in_r(r), .in_g(g), .in_b(b), .out_valid(gv),
        .out_sof(gf[3]), .out_sol(gf[2]), .out_eol(gf[1]), .out_eof(gf[0]),
        .out_gray(gray)
    );
    gray_threshold #(.THRESHOLD(0)) dut_t0 (
        .clk(clk), .rst_n(rst_n), .in_valid(gv),
        .in_sof(gf[3]), .in_sol(gf[2]), .in_eol(gf[1]), .in_eof(gf[0]),
        .in_gray(gray), .out_valid(tv[0]), .out_sof(tf0[3]),
        .out_sol(tf0[2]), .out_eol(tf0[1]), .out_eof(tf0[0]), .out_mask(mask0)
    );
    gray_threshold #(.THRESHOLD(127)) dut_t127 (
        .clk(clk), .rst_n(rst_n), .in_valid(gv),
        .in_sof(gf[3]), .in_sol(gf[2]), .in_eol(gf[1]), .in_eof(gf[0]),
        .in_gray(gray), .out_valid(tv[1]), .out_sof(tf127[3]),
        .out_sol(tf127[2]), .out_eol(tf127[1]), .out_eof(tf127[0]), .out_mask(mask127)
    );
    gray_threshold #(.THRESHOLD(128)) dut_t128 (
        .clk(clk), .rst_n(rst_n), .in_valid(gv),
        .in_sof(gf[3]), .in_sol(gf[2]), .in_eol(gf[1]), .in_eof(gf[0]),
        .in_gray(gray), .out_valid(tv[2]), .out_sof(tf128[3]),
        .out_sol(tf128[2]), .out_eol(tf128[1]), .out_eof(tf128[0]), .out_mask(mask128)
    );
    gray_threshold #(.THRESHOLD(255)) dut_t255 (
        .clk(clk), .rst_n(rst_n), .in_valid(gv),
        .in_sof(gf[3]), .in_sol(gf[2]), .in_eol(gf[1]), .in_eof(gf[0]),
        .in_gray(gray), .out_valid(tv[3]), .out_sof(tf255[3]),
        .out_sol(tf255[2]), .out_eol(tf255[1]), .out_eof(tf255[0]), .out_mask(mask255)
    );

    // Integer multiplication/division reference is independent of RTL shifts.
    function automatic integer reference_gray(input integer rr, gg, bb);
        reference_gray = (77 * rr + 150 * gg + 29 * bb + 128) / 256;
    endfunction

    integer cycles = 0, checked_gray = 0, checked_binary = 0;
    integer gap_cycles = 0;
    integer seed = 32'h51f03a29;
    reg previous_valid = 0;
    reg [3:0] previous_flags = 0;
    integer previous_gray = 0;
    integer expected_now;
    reg [3:0] flags_now;

    always @(posedge clk) begin
        cycles = cycles + 1;
        expected_now = reference_gray(r, g, b);
        flags_now = in_valid ? {in_sof, in_sol, in_eol, in_eof} : 4'b0;
        #1;
        if (!rst_n) begin
            if ({gv, gf, gray, tv, tf0, tf127, tf128, tf255,
                 mask0, mask127, mask128, mask255} !== 0)
                $fatal(1, "pixel reset outputs are not zero at cycle %0d", cycles);
            previous_valid = 0;
            previous_flags = 0;
            previous_gray = 0;
        end else begin
            if (gv !== in_valid || gf !== flags_now)
                $fatal(1, "gray valid/marker mismatch at cycle %0d", cycles);
            if (in_valid) begin
                if (gray !== expected_now[7:0])
                    $fatal(1, "gray mismatch RGB=%0d,%0d,%0d got=%0d expected=%0d", r,g,b,gray,expected_now);
                checked_gray = checked_gray + 1;
            end else gap_cycles = gap_cycles + 1;
            if (tv !== {4{previous_valid}} || tf0 !== previous_flags ||
                tf127 !== previous_flags || tf128 !== previous_flags || tf255 !== previous_flags)
                $fatal(1, "threshold valid/marker mismatch at cycle %0d", cycles);
            if (previous_valid) begin
                if (mask0 !== 8'hff ||
                    mask127 !== ((previous_gray >= 127) ? 8'hff : 8'h00) ||
                    mask128 !== ((previous_gray >= 128) ? 8'hff : 8'h00) ||
                    mask255 !== ((previous_gray >= 255) ? 8'hff : 8'h00))
                    $fatal(1, "threshold data mismatch for gray=%0d", previous_gray);
                checked_binary = checked_binary + 1;
            end
            previous_valid = in_valid;
            previous_flags = flags_now;
            previous_gray = expected_now;
        end
    end

    task automatic idle_cycle;
        begin
            @(negedge clk);
            in_valid = 0;
            // Deliberately illegal markers/data in invalid cycles must be ignored.
            {in_sof, in_sol, in_eol, in_eof} = 4'b1111;
            r = $random(seed); g = $random(seed); b = $random(seed);
        end
    endtask

    task automatic send_rgb(input integer rr, gg, bb, input integer bubbles);
        integer j;
        begin
            for (j = 0; j < bubbles; j = j + 1) idle_cycle();
            @(negedge clk);
            in_valid = 1;
            {in_sof, in_sol, in_eol, in_eof} = $random(seed);
            r = rr; g = gg; b = bb;
        end
    endtask

    integer v, i, rr, gg, bb, gaps;
    initial begin
        repeat (3) @(negedge clk);
        rst_n = 1;
        for (v = 0; v < 256; v = v + 1) send_rgb(v, v, v, v % 3);
        for (v = 0; v < 256; v = v + 1) begin
            send_rgb(v, 0, 0, 0);
            send_rgb(0, v, 0, 0);
            send_rgb(0, 0, v, 0);
        end
        for (i = 0; i < 2048; i = i + 1) begin
            rr = $random(seed) & 255;
            gg = $random(seed) & 255;
            bb = $random(seed) & 255;
            gaps = ($random(seed) & 32'h7fffffff) % 3;
            send_rgb(rr, gg, bb, gaps);
        end
        repeat (3) idle_cycle();
        // Reset while a valid pixel is pending in the threshold pipeline.
        send_rgb(255, 255, 255, 0);
        @(negedge clk);
        rst_n = 0;
        in_valid = 1;
        repeat (2) @(negedge clk);
        rst_n = 1;
        in_valid = 0;
        send_rgb(0, 0, 0, 0);
        send_rgb(127, 127, 127, 1);
        send_rgb(128, 128, 128, 0);
        send_rgb(255, 255, 255, 0);
        repeat (4) idle_cycle();
        @(negedge clk);
        if (checked_gray != 3077 || checked_binary != 3076 || gap_cycles < 2000)
            $fatal(1, "pixel coverage count mismatch gray=%0d binary=%0d gaps=%0d", checked_gray, checked_binary, gap_cycles);
        $display("PASS tb_pixel_ops: gray=%0d, binary=%0d, thresholds=0/127/128/255, valid_gaps=%0d, reset_and_markers=checked", checked_gray, checked_binary, gap_cycles);
        $finish;
    end
    initial begin
        #1000000;
        $fatal(1, "tb_pixel_ops timeout");
    end
endmodule
