`timescale 1ns / 1ps
module tb_video_display_preprocess;
    reg clk=0;
    always #5 clk=~clk;
    reg rst_n=0, hs=0, vs=0, de=0;
    reg [7:0] r=0, g=0, b=0;
    wire [2:0] oh, ov, od;
    wire [23:0] rgb[0:2];
    genvar mode;
    generate for(mode=0;mode<3;mode=mode+1) begin : dut
        video_display_preprocess #(.MODE(mode),.THRESHOLD(128)) u (
            .clk(clk), .rst_n(rst_n), .in_hs(hs), .in_vs(vs), .in_de(de),
            .in_r(r), .in_g(g), .in_b(b),
            .out_hs(oh[mode]), .out_vs(ov[mode]), .out_de(od[mode]),
            .out_r(rgb[mode][23:16]), .out_g(rgb[mode][15:8]), .out_b(rgb[mode][7:0])
        );
    end endgenerate
    integer checks=0, active=0, blanks=0, resets=0;
    integer seed=32'h38f219ab;
    integer gray;
    reg prev_h=0, prev_v=0, prev_d=0;
    reg [23:0] prev_rgb=0;
    reg [7:0] prev_gray=0;
    reg [7:0] exp_mask;
    always @(posedge clk) begin
        if(!rst_n) begin
            prev_h=0; prev_v=0; prev_d=0; prev_rgb=0; prev_gray=0;
            #1;
            if({oh,ov,od} !== 9'b0) $fatal(1,"reset controls");
            for(integer m=0;m<3;m=m+1)
                if(rgb[m] !== 24'b0) $fatal(1,"reset pixels mode %0d",m);
        end else begin
            #1;
            for(integer m=0;m<3;m=m+1) begin
                if({oh[m],ov[m],od[m]} !== {prev_h,prev_v,prev_d})
                    $fatal(1,"control alignment mode %0d",m);
            end
            if(prev_d) begin
                exp_mask=(prev_gray>=128)?255:0;
                if(rgb[0] !== prev_rgb) $fatal(1,"RGB alignment/order");
                if(rgb[1] !== {prev_gray,prev_gray,prev_gray}) $fatal(1,"gray mismatch");
                if(rgb[2] !== {exp_mask,exp_mask,exp_mask}) $fatal(1,"binary mismatch");
                active=active+1;
            end else blanks=blanks+1;
            gray=(77*r+150*g+29*b+128)/256;
            prev_gray=gray[7:0]; prev_rgb={r,g,b};
            prev_h=hs; prev_v=vs; prev_d=de;
            checks=checks+1;
        end
    end
    initial begin
        repeat(3) @(negedge clk);
        rst_n=1;
        // Primaries expose swapped red/blue or one-cycle control mistakes.
        de=1; r=255; g=0; b=0;
        @(negedge clk); r=0; g=255;
        @(negedge clk); g=0; b=255;
        @(negedge clk); r=255; g=255;
        for(integer n=0;n<1500;n=n+1) begin
            @(negedge clk);
            if(n==251 || n==877) begin
                rst_n=0; resets=resets+1;
                #1;
                if({oh,ov,od} !== 9'b0) $fatal(1,"async reset controls");
                @(negedge clk); rst_n=1;
            end
            de=(n%17<11);
            hs=(n%17>=13); vs=(n%119>=102);
            r=$random(seed); g=$random(seed); b=$random(seed);
        end
        @(negedge clk); de=0; hs=0; vs=0;
        repeat(3) @(negedge clk);
        $display("PASS tb_video_display_preprocess cycles=%0d active=%0d blanks=%0d resets=%0d modes=RGB/gray/binary control_latency=2",checks,active,blanks,resets);
        $finish;
    end
endmodule
