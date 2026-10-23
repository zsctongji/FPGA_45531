`timescale 1ns / 1ps

// Functional pixel/marker test at 1280x720. No hardware frame-rate claim.
module tb_sobel_720p;
    localparam integer W = 1280, H = 720;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0;
    reg in_valid = 0, in_sof = 0, in_sol = 0, in_eol = 0, in_eof = 0;
    reg [7:0] level = 0;
    wire gv, bv, ev;
    wire [3:0] gf, bf, ef;
    wire [7:0] gray, binary_pixel, magnitude, edge_pixel;
    integer stim_frame = 0, stim_x = 0, stim_y = 0;
    reg previous_valid = 0;
    reg [3:0] previous_flags = 0;
    reg [7:0] previous_level = 0;
    integer previous_x = 0, previous_y = 0, previous_frame = 0;
    integer checked_gray = 0, checked_binary = 0, checked_edges = 0;
    integer edge_sofs = 0, edge_eofs = 0, edge_sols = 0, edge_eols = 0;
    integer gradient_pixels = 0, gap_cycles = 0;
    reg expected_ev, expected_gradient;
    reg [3:0] expected_flags, expected_ef;
    reg [7:0] expected_mag;

    portable_vision_core #(.WIDTH(W), .HEIGHT(H), .THRESHOLD(128), .EDGE_THRESHOLD(80)) dut (
        .clk(clk), .rst_n(rst_n), .in_valid(in_valid), .in_sof(in_sof),
        .in_sol(in_sol), .in_eol(in_eol), .in_eof(in_eof),
        .in_r(level), .in_g(level), .in_b(level),
        .gray_valid(gv), .gray_sof(gf[3]), .gray_sol(gf[2]),
        .gray_eol(gf[1]), .gray_eof(gf[0]), .gray_pixel(gray),
        .binary_valid(bv), .binary_sof(bf[3]), .binary_sol(bf[2]),
        .binary_eol(bf[1]), .binary_eof(bf[0]), .binary_pixel(binary_pixel),
        .edge_valid(ev), .edge_sof(ef[3]), .edge_sol(ef[2]),
        .edge_eol(ef[1]), .edge_eof(ef[0]),
        .edge_magnitude(magnitude), .edge_pixel(edge_pixel)
    );

    always @(posedge clk) begin
        expected_flags = in_valid ? {in_sof,in_sol,in_eol,in_eof} : 4'b0;
        expected_ev = previous_valid && previous_x >= 2 && previous_y >= 2;
        expected_ef = expected_ev ?
            {(previous_x == 2 && previous_y == 2), (previous_x == 2),
             (previous_x == W-1), (previous_x == W-1 && previous_y == H-1)} : 4'b0;
        // Analytic reference: a 0/255 step has nonzero clipped Sobel only
        // at the two centers immediately adjacent to the step boundary.
        expected_gradient = (previous_frame == 0) ?
            (previous_x == W/2 || previous_x == W/2+1) :
            (previous_y == H/2 || previous_y == H/2+1);
        expected_mag = expected_gradient ? 8'hff : 8'h00;
        #1;
        if (!rst_n) begin
            if ({gv,gf,gray,bv,bf,binary_pixel,ev,ef,magnitude,edge_pixel} !== 0)
                $fatal(1,"720p reset mismatch");
            previous_valid = 0;
            previous_flags = 0;
        end else begin
            if (gv !== in_valid || gf !== expected_flags || (in_valid && gray !== level))
                $fatal(1,"720p grayscale valid/data/marker mismatch f=%0d y=%0d x=%0d",stim_frame,stim_y,stim_x);
            if (in_valid) checked_gray = checked_gray + 1;
            else gap_cycles = gap_cycles + 1;
            if (bv !== previous_valid || bf !== previous_flags ||
                (previous_valid && binary_pixel !== previous_level))
                $fatal(1,"720p threshold valid/data/marker mismatch");
            if (previous_valid) checked_binary = checked_binary + 1;
            if (ev !== expected_ev || ef !== expected_ef)
                $fatal(1,"720p Sobel valid/marker mismatch f=%0d y=%0d x=%0d",previous_frame,previous_y,previous_x);
            if (expected_ev) begin
                if (magnitude !== expected_mag || edge_pixel !== expected_mag)
                    $fatal(1,"720p Sobel gradient mismatch f=%0d y=%0d x=%0d got=%0d expected=%0d",previous_frame,previous_y,previous_x,magnitude,expected_mag);
                checked_edges = checked_edges + 1;
                if (expected_gradient) gradient_pixels = gradient_pixels + 1;
                if (ef[3]) edge_sofs = edge_sofs + 1;
                if (ef[2]) edge_sols = edge_sols + 1;
                if (ef[1]) edge_eols = edge_eols + 1;
                if (ef[0]) edge_eofs = edge_eofs + 1;
            end
            previous_valid = in_valid;
            previous_flags = expected_flags;
            previous_level = level;
            previous_x = stim_x;
            previous_y = stim_y;
            previous_frame = stim_frame;
        end
    end

    task automatic idle_cycle;
        begin
            @(negedge clk);
            in_valid = 0;
            {in_sof,in_sol,in_eol,in_eof} = 4'b1111;
            level = 8'h5a;
        end
    endtask

    integer f, yy, xx, idx;
    initial begin
        repeat(3) @(negedge clk);
        rst_n = 1;
        for (f = 0; f < 2; f = f + 1)
            for (yy = 0; yy < H; yy = yy + 1)
                for (xx = 0; xx < W; xx = xx + 1) begin
                    idx = f*W*H + yy*W + xx;
                    if (idx % 16381 == 123) idle_cycle();
                    @(negedge clk);
                    in_valid = 1;
                    in_sof = (xx == 0 && yy == 0);
                    in_sol = (xx == 0);
                    in_eol = (xx == W-1);
                    in_eof = (xx == W-1 && yy == H-1);
                    level = ((f == 0) ? (xx >= W/2) : (yy >= H/2)) ? 8'hff : 8'h00;
                    stim_frame = f; stim_y = yy; stim_x = xx;
                end
        repeat (5) idle_cycle();
        @(negedge clk);
        if (checked_gray != 2*W*H || checked_binary != 2*W*H ||
            checked_edges != 2*(W-2)*(H-2) || edge_sofs != 2 || edge_eofs != 2 ||
            edge_sols != 2*(H-2) || edge_eols != 2*(H-2) ||
            gradient_pixels != 2*(H-2)+2*(W-2) || gap_cycles < 100)
            $fatal(1,"720p coverage mismatch gray=%0d binary=%0d edge=%0d frames=%0d/%0d lines=%0d/%0d gradients=%0d gaps=%0d",checked_gray,checked_binary,checked_edges,edge_sofs,edge_eofs,edge_sols,edge_eols,gradient_pixels,gap_cycles);
        $display("PASS tb_sobel_720p: size=1280x720, frames=2, gray=%0d, binary=%0d, Sobel=%0d, lines=%0d, gradient_pixels=%0d, valid_gaps=%0d",checked_gray,checked_binary,checked_edges,edge_eols,gradient_pixels,gap_cycles);
        $display("PASS 720p functional coverage: vertical_step, horizontal_step, consecutive_frames, cropped_border, frame_and_line_markers; no hardware_fps_claim");
        $finish;
    end
    initial begin
        #30000000;
        $fatal(1,"tb_sobel_720p timeout");
    end
endmodule
