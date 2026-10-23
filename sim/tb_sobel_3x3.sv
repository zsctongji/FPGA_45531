`timescale 1ns / 1ps

module tb_sobel_3x3;
    reg clk = 0;
    always #5 clk = ~clk;
    reg rst_n = 0, in_valid = 0, in_sof = 0;
    reg [7:0] gray = 0;
    wire valid;
    wire [3:0] flags;
    wire [7:0] magnitude, mask;
    integer stim_frame = 0, stim_pos = 0;
    integer count = 0, gaps = 0;
    reg expected_valid;
    reg [7:0] expected_mag;

    sobel_stream #(.WIDTH(3),.HEIGHT(3),.EDGE_THRESHOLD(255)) dut (
        .clk(clk),.rst_n(rst_n),.in_valid(in_valid),.in_sof(in_sof),.in_gray(gray),
        .out_valid(valid),.out_sof(flags[3]),.out_sol(flags[2]),
        .out_eol(flags[1]),.out_eof(flags[0]),.out_magnitude(magnitude),.out_edge(mask)
    );
    always @(posedge clk) begin
        expected_valid = in_valid && stim_pos == 8;
        expected_mag = (stim_frame == 0) ? 8'hff : 8'h00;
        #1;
        if (!rst_n) begin
            if ({valid,flags,magnitude,mask} !== 0) $fatal(1,"3x3 reset mismatch");
        end else begin
            if (valid !== expected_valid || flags !== (expected_valid ? 4'b1111 : 4'b0000))
                $fatal(1,"3x3 boundary/marker mismatch frame=%0d pos=%0d",stim_frame,stim_pos);
            if (expected_valid) begin
                // First frame's lower-right impulse gives |Gx|+|Gy|=510,
                // clipped to 255. Second constant frame gives zero.
                if (magnitude !== expected_mag || mask !== expected_mag)
                    $fatal(1,"3x3 magnitude/threshold equality mismatch");
                count = count + 1;
            end
            if (!in_valid) gaps = gaps + 1;
        end
    end
    integer f,p;
    initial begin
        repeat (3) @(negedge clk);
        rst_n = 1;
        for (f=0;f<2;f=f+1)
            for(p=0;p<9;p=p+1) begin
                if(p%3 == 1) begin
                    @(negedge clk);
                    in_valid=0; in_sof=1; gray=8'hc7;
                end
                @(negedge clk);
                in_valid=1; in_sof=(p==0); stim_frame=f; stim_pos=p;
                gray = (f == 0) ? ((p == 8) ? 8'hff : 8'h00) : 8'd100;
            end
        @(negedge clk);
        in_valid=0; in_sof=1;
        repeat(3) @(negedge clk);
        if(count != 2 || gaps < 6) $fatal(1,"3x3 coverage mismatch");
        $display("PASS tb_sobel_3x3: minimum_size=3x3, consecutive_frames=2, one_pixel_per_output_frame, all_markers, saturation, threshold_255_equality, valid_gaps");
        $finish;
    end
    initial begin
        #10000;
        $fatal(1,"tb_sobel_3x3 timeout");
    end
endmodule
