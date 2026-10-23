`timescale 1ns/1ps
module tb_motion_minimum;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,vs=0,de=0;reg[7:0]gray=100;
    wire sv,ss,se,sa,ov,cv,motion,error;wire[7:0]sg;wire[31:0]count;
    integer frames=0;
    video_grid_sampler #(.FRAME_WIDTH(1),.FRAME_HEIGHT(1),.STEP_X(20),.STEP_Y(20)) sampler(
        .clk(clk),.rst_n(rst_n),.in_vs(vs),.in_de(de),.in_gray(gray),.sample_valid(sv),.sample_sof(ss),.sample_eof(se),.sample_abort(sa),.sample_gray(sg));
    frame_motion_stats #(.WIDTH(1),.HEIGHT(1),.MIN_CHANGED(1),.DIFF_THRESHOLD(24)) stats(
        .clk(clk),.rst_n(rst_n),.in_valid(sv),.in_sof(ss),.in_eof(se),.in_abort(sa),.in_gray(sg),
        .out_valid(ov),.comparison_valid(cv),.motion(motion),.frame_error(error),.changed_count(count),
        .absolute_difference_sum(),.bbox_valid(),.min_x(),.min_y(),.max_x(),.max_y());
    always@(posedge clk)begin
        #1;
        if(rst_n && error)$fatal(1,"minimum frame rejected");
        if(rst_n && ov)begin
            if(cv!==(frames!=0) || count!==((frames==1)?32'd1:32'd0) || motion!==(frames==1))$fatal(1,"one-pixel baseline/history");
            frames=frames+1;
        end
    end
    task boundary;
        @(negedge clk);vs=1;repeat(2)@(negedge clk);vs=0;repeat(4)@(negedge clk);
    endtask
    initial begin
        repeat(3)@(negedge clk);rst_n=1;
        for(integer f=0;f<3;f=f+1)begin
            boundary;gray=f==0?100:124;
            @(negedge clk);de=1;@(negedge clk);de=0;repeat(3)@(negedge clk);
        end
        boundary;repeat(3)@(negedge clk);
        if(frames!=3)$fatal(1,"minimum coverage");
        $display("PASS tb_motion_minimum grid=1x1 first_frame_invalid threshold_equal static SOF_EOF_same_sample");$finish;
    end
    initial begin #100000;$fatal(1,"timeout");end
endmodule
