`timescale 1ns/1ps
module tb_motion_1080p;
    reg clk=0;always #5 clk=~clk;
    reg rst_n=0,vs=0,de=0;reg[7:0]gray=40;
    wire sv,ss,se,sa,ov,cv,motion,error,bbox;
    wire[7:0]sg;wire[31:0]count,total;
    wire[15:0]xmin,ymin,xmax,ymax;
    integer frames=0,samples=0,pixels=0;
    video_grid_sampler sampler(.clk(clk),.rst_n(rst_n),.in_vs(vs),.in_de(de),.in_gray(gray),
        .sample_valid(sv),.sample_sof(ss),.sample_eof(se),.sample_abort(sa),.sample_gray(sg));
    frame_motion_stats stats(.clk(clk),.rst_n(rst_n),.in_valid(sv),.in_sof(ss),.in_eof(se),.in_abort(sa),.in_gray(sg),
        .out_valid(ov),.comparison_valid(cv),.motion(motion),.frame_error(error),.changed_count(count),
        .absolute_difference_sum(total),.bbox_valid(bbox),.min_x(xmin),.min_y(ymin),.max_x(xmax),.max_y(ymax));
    always@(posedge clk)begin
        #1;
        if(rst_n)begin
            if(de)pixels=pixels+1;
            if(sv)samples=samples+1;
            if(error)$fatal(1,"full HD frame rejected");
            if(ov)begin
                if(frames==0)begin
                    if(cv || motion || count!=0 || total!=0 || bbox)$fatal(1,"first full HD frame is baseline only");
                end else if(frames==1)begin
                    if(!cv || !motion || count!=32 || total!=768 || !bbox || {xmin,ymin,xmax,ymax}!==64'h00000000005f0035)
                        $fatal(1,"full HD motion stats count=%0d sum=%0d bbox=%0d/%0d/%0d/%0d",count,total,xmin,ymin,xmax,ymax);
                end else $fatal(1,"unexpected extra frame");
                frames=frames+1;
            end
        end
    end
    task boundary;
        @(negedge clk);vs=1;repeat(2)@(negedge clk);vs=0;repeat(4)@(negedge clk);
    endtask
    initial begin
        repeat(3)@(negedge clk);rst_n=1;
        for(integer f=0;f<2;f=f+1)begin
            boundary;
            for(integer y=0;y<1080;y=y+1)begin
                for(integer x=0;x<1920;x=x+1)begin
                    @(negedge clk);de=1;gray=40;
                    if(f==1)begin
                        // Exactly 32 changed grid samples; threshold 24 and count 32 are inclusive.
                        if(x%20==0 && ((y==0 && x<320) || (y==1060 && x>=1600)))gray=64;
                        // Very bright non-grid pixels must not pollute the sampled image.
                        if(x%20!=0 || y%20!=0)gray=255;
                    end
                end
                @(negedge clk);de=0;repeat(3)@(negedge clk);
            end
            if(frames!=f)$fatal(1,"frame committed before next VS validated its height");
        end
        boundary;repeat(5)@(negedge clk);
        if(frames!=2 || samples!=10368 || pixels!=4147200)$fatal(1,"full HD coverage %0d/%0d/%0d",frames,samples,pixels);
        $display("PASS tb_motion_1080p frames=2 input_pixels=%0d grid_samples=%0d grid=96x54 changed=32 diff_sum=768 bbox=0/0/95/53 ignored_non_grid_pixels",pixels,samples);
        $finish;
    end
    initial begin #100000000;$fatal(1,"timeout");end
endmodule
