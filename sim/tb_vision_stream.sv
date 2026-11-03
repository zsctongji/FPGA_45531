`timescale 1ns / 1ps

module tb_vision_stream;
    localparam integer W = 9, H = 7, NFRAMES = 8;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg in_valid = 0;
    reg in_sof = 0, in_sol = 0, in_eol = 0, in_eof = 0;
    reg [7:0] r = 0, g = 0, b = 0;
    wire gv, bv, ev;
    wire [3:0] gf, bf, ef;
    wire [7:0] gray, binary_pixel, magnitude, edge_pixel;
    reg [7:0] frame_r [0:NFRAMES*W*H-1];
    reg [7:0] frame_g [0:NFRAMES*W*H-1];
    reg [7:0] frame_b [0:NFRAMES*W*H-1];
    integer frame_gray [0:NFRAMES*W*H-1];
    integer stim_frame = 0, stim_x = 0, stim_y = 0;
    integer seed = 32'h19720531;

    portable_vision_core #(.WIDTH(W), .HEIGHT(H), .THRESHOLD(128), .EDGE_THRESHOLD(80)) dut (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_sof(in_sof),
        .in_sol(in_sol), .in_eol(in_eol), .in_eof(in_eof),
        .in_r(r), .in_g(g), .in_b(b),
        .gray_valid(gv), .gray_sof(gf[3]), .gray_sol(gf[2]),
        .gray_eol(gf[1]), .gray_eof(gf[0]), .gray_pixel(gray),
        .binary_valid(bv), .binary_sof(bf[3]), .binary_sol(bf[2]),
        .binary_eol(bf[1]), .binary_eof(bf[0]), .binary_pixel(binary_pixel),
        .edge_valid(ev), .edge_sof(ef[3]), .edge_sol(ef[2]),
        .edge_eol(ef[1]), .edge_eof(ef[0]),
        .edge_magnitude(magnitude), .edge_pixel(edge_pixel)
    );

    function automatic integer reference_gray(input integer rr, gg, bb);
        reference_gray = (77 * rr + 150 * gg + 29 * bb + 128) / 256;
    endfunction
    // Full-frame 2D integer convolution, independent of RTL line buffers.
    function automatic integer reference_sobel(input integer f, cy, cx);
        integer dr, dc, value, sx, sy, mag;
        begin
            sx = 0; sy = 0;
            for (dr = -1; dr <= 1; dr = dr + 1)
                for (dc = -1; dc <= 1; dc = dc + 1) begin
                    value = frame_gray[f*W*H + (cy+dr)*W + cx+dc];
                    sx = sx + value * dc * ((dr == 0) ? 2 : 1);
                    sy = sy + value * dr * ((dc == 0) ? 2 : 1);
                end
            if (sx < 0) sx = -sx;
            if (sy < 0) sy = -sy;
            mag = sx + sy;
            reference_sobel = (mag > 255) ? 255 : mag;
        end
    endfunction

    integer cycles = 0, checked_gray = 0, checked_binary = 0;
    integer checked_sobel = 0, edge_sofs = 0, edge_eofs = 0;
    integer edge_sols = 0, edge_eols = 0, gap_cycles = 0;
    integer zeros = 0, saturated = 0, intermediate = 0;
    reg previous_valid = 0;
    reg [3:0] previous_flags = 0;
    integer previous_gray = 0, previous_x = 0, previous_y = 0, previous_frame = 0;
    integer expected_gray, expected_mag;
    reg [3:0] expected_flags, expected_edge_flags;
    reg expected_ev;

    always @(posedge clk) begin
        cycles = cycles + 1;
        expected_gray = reference_gray(r, g, b);
        expected_flags = in_valid ? {in_sof, in_sol, in_eol, in_eof} : 4'b0;
        expected_ev = previous_valid && previous_x >= 2 && previous_y >= 2;
        expected_edge_flags = expected_ev ?
            {(previous_x == 2 && previous_y == 2), (previous_x == 2),
             (previous_x == W-1), (previous_x == W-1 && previous_y == H-1)} : 4'b0;
        if (expected_ev) expected_mag = reference_sobel(previous_frame, previous_y-1, previous_x-1);
        #1;
        if (!rst_n) begin
            if ({gv, gf, gray, bv, bf, binary_pixel, ev, ef, magnitude, edge_pixel} !== 0)
                $fatal(1, "stream reset outputs are not zero at cycle %0d", cycles);
            previous_valid = 0;
            previous_flags = 0;
            previous_gray = 0;
        end else begin
            if (gv !== in_valid || gf !== expected_flags)
                $fatal(1, "stream gray marker/valid mismatch at cycle %0d", cycles);
            if (in_valid) begin
                if (gray !== expected_gray[7:0]) $fatal(1, "stream gray mismatch");
                checked_gray = checked_gray + 1;
            end else gap_cycles = gap_cycles + 1;
            if (bv !== previous_valid || bf !== previous_flags)
                $fatal(1, "stream threshold marker/valid mismatch at cycle %0d", cycles);
            if (previous_valid) begin
                if (binary_pixel !== ((previous_gray >= 128) ? 8'hff : 8'h00))
                    $fatal(1, "stream threshold mismatch");
                checked_binary = checked_binary + 1;
            end
            if (ev !== expected_ev || ef !== expected_edge_flags)
                $fatal(1, "Sobel valid/boundary/marker mismatch at cycle=%0d, f=%0d x=%0d y=%0d got=%b/%b expected=%b/%b", cycles,previous_frame,previous_x,previous_y,ev,ef,expected_ev,expected_edge_flags);
            if (expected_ev) begin
                if (magnitude !== expected_mag[7:0] ||
                    edge_pixel !== ((expected_mag >= 80) ? 8'hff : 8'h00))
                    $fatal(1, "Sobel mismatch frame=%0d center=(%0d,%0d) got=%0d expected=%0d", previous_frame,previous_y-1,previous_x-1,magnitude,expected_mag);
                checked_sobel = checked_sobel + 1;
                if (expected_mag == 0) zeros = zeros + 1;
                else if (expected_mag == 255) saturated = saturated + 1;
                else intermediate = intermediate + 1;
                if (ef[3]) edge_sofs = edge_sofs + 1;
                if (ef[2]) edge_sols = edge_sols + 1;
                if (ef[1]) edge_eols = edge_eols + 1;
                if (ef[0]) edge_eofs = edge_eofs + 1;
            end
            previous_valid = in_valid;
            previous_flags = expected_flags;
            previous_gray = expected_gray;
            previous_x = stim_x;
            previous_y = stim_y;
            previous_frame = stim_frame;
        end
    end

    task automatic idle_cycle;
        begin
            @(negedge clk);
            in_valid = 0;
            {in_sof, in_sol, in_eol, in_eof} = 4'b1111;
            r = $random(seed); g = $random(seed); b = $random(seed);
        end
    endtask
    task automatic send_pixel(input integer f, yy, xx, bubbles);
        integer j, k;
        begin
            for (j = 0; j < bubbles; j = j + 1) idle_cycle();
            @(negedge clk);
            k = f*W*H + yy*W + xx;
            stim_frame = f; stim_x = xx; stim_y = yy;
            r = frame_r[k]; g = frame_g[k]; b = frame_b[k];
            in_valid = 1;
            in_sof = (xx == 0 && yy == 0);
            in_sol = (xx == 0);
            in_eol = (xx == W-1);
            in_eof = (xx == W-1 && yy == H-1);
        end
    endtask

    integer f, yy, xx, k, v, gaps;
    initial begin
        for (f = 0; f < NFRAMES; f = f + 1)
            for (yy = 0; yy < H; yy = yy + 1)
                for (xx = 0; xx < W; xx = xx + 1) begin
                    k = f*W*H + yy*W + xx;
                    case (f)
                        0: begin frame_r[k]=0; frame_g[k]=0; frame_b[k]=0; end
                        1: begin frame_r[k]=255; frame_g[k]=255; frame_b[k]=255; end
                        2: begin v=xx*10+yy*5; frame_r[k]=v; frame_g[k]=v; frame_b[k]=v; end
                        3: begin v=((xx/2+yy/2)%2)*255; frame_r[k]=v; frame_g[k]=v; frame_b[k]=v; end
                        4: begin v=(xx == W/2 && yy == H/2) ? 255 : 0; frame_r[k]=v; frame_g[k]=v; frame_b[k]=v; end
                        5: begin frame_r[k]=xx*28; frame_g[k]=yy*40; frame_b[k]=(xx+yy)*15; end
                        default: begin frame_r[k]=$random(seed); frame_g[k]=$random(seed); frame_b[k]=$random(seed); end
                    endcase
                    frame_gray[k] = reference_gray(frame_r[k],frame_g[k],frame_b[k]);
                end
        repeat (3) @(negedge clk);
        rst_n = 1;
        for (f = 0; f < 4; f = f + 1)
            for (yy = 0; yy < H; yy = yy + 1)
                for (xx = 0; xx < W; xx = xx + 1) send_pixel(f,yy,xx,0);
        // Begin a partial next frame then reset. No interior output yet.
        for (xx = 0; xx < W; xx = xx + 1) send_pixel(4,0,xx,0);
        for (xx = 0; xx < 3; xx = xx + 1) send_pixel(4,1,xx,0);
        @(negedge clk);
        rst_n = 0;
        in_valid = 0;
        repeat (2) @(negedge clk);
        rst_n = 1;
        for (f = 4; f < NFRAMES; f = f + 1)
            for (yy = 0; yy < H; yy = yy + 1)
                for (xx = 0; xx < W; xx = xx + 1) begin
                    gaps = ($random(seed) & 32'h7fffffff) % 4;
                    send_pixel(f,yy,xx,gaps);
                end
        repeat (5) idle_cycle();
        @(negedge clk);
        if (checked_gray != NFRAMES*W*H+12 || checked_binary != NFRAMES*W*H+11 ||
            checked_sobel != NFRAMES*(W-2)*(H-2) || edge_sofs != NFRAMES || edge_eofs != NFRAMES ||
            edge_sols != NFRAMES*(H-2) || edge_eols != NFRAMES*(H-2) ||
            zeros == 0 || saturated == 0 || intermediate == 0 || gap_cycles < 300)
            $fatal(1, "stream coverage mismatch gray=%0d binary=%0d sobel=%0d frames=%0d/%0d lines=%0d/%0d magnitudes=%0d/%0d/%0d gaps=%0d",checked_gray,checked_binary,checked_sobel,edge_sofs,edge_eofs,edge_sols,edge_eols,zeros,intermediate,saturated,gap_cycles);
        $display("PASS tb_vision_stream: gray=%0d, binary=%0d, Sobel=%0d, frames=%0d, lines=%0d, valid_gaps=%0d, zero/intermediate/saturated=%0d/%0d/%0d", checked_gray,checked_binary,checked_sobel,edge_eofs,edge_eols,gap_cycles,zeros,intermediate,saturated);
        $display("PASS stream coverage: continuous_frames, random_valid_gaps, input_border_suppression, regenerated_markers, reset_midframe, stale_line_memory_recovery");
        $finish;
    end
    initial begin
        #1000000;
        $fatal(1, "tb_vision_stream timeout");
    end
endmodule
