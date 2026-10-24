`timescale 1ns/1ps
module tb_a_capture;
    reg clk=0;always #5 clk=~clk;
    reg rst=0,vs=0,de=0;
    reg [7:0] gray=0;
    reg [31:0] now=0;
    wire sv,ss,se,sa,rv,complete;
    wire [7:0] sp;
    wire [31:0] fid,stamp,rf,rt,frames,errors;
    wire [15:0] w,h;
    integer samples=0,records=0,eofs=0;
    video_a_capture #(.FRAME_WIDTH(8),.FRAME_HEIGHT(6),.STEP_X(2),.STEP_Y(2)) dut(
        .clk(clk),.rst_n(rst),.in_vs(vs),.in_de(de),.in_gray(gray),.now_ms(now),
        .sample_valid(sv),.sample_sof(ss),.sample_eof(se),.sample_abort(sa),.sample_gray(sp),
        .sample_frame_id(fid),.sample_timestamp_ms(stamp),.record_valid(rv),.record_complete(complete),
        .record_frame_id(rf),.record_timestamp_ms(rt),.record_width(w),.record_height(h),.source_frames(frames),.format_errors(errors));
    task tick;begin @(posedge clk);#1;end endtask
    always @(posedge clk) begin
        #2;
        if(sv) begin
            if(fid!=eofs||stamp!=100+eofs)$fatal(1,"sample metadata / delayed EOF association %0d %0d",fid,stamp);
            samples++;
            if(se) begin if(samples!=(eofs+1)*12)$fatal(1,"sample count");eofs++;end
        end
        if(rv) begin
            if(rf!=records||rt!=100+records||w!=8||h!=6||complete!==(records<2))$fatal(1,"capture telemetry");
            records++;
        end
    end
    task boundary;begin @(negedge clk);vs=1;de=0;tick();@(negedge clk);vs=0;tick();end endtask
    task frame(input integer f,input integer short_line);
        begin
            for(integer y=0;y<6;y++) begin
                for(integer x=0;x<(short_line&&y==2?7:8);x++) begin
                    @(negedge clk);de=1;gray=x+y*8;now=100+f;tick();
                end
                @(negedge clk);de=0;tick();tick();
            end
        end
    endtask
    initial begin
        repeat(3)tick();@(negedge clk);rst=1;boundary();frame(0,0);boundary();frame(1,0);boundary();frame(2,1);boundary();
        tick();if(records!=3||eofs!=2||errors!=1)$fatal(1,"record totals");
        $display("PASS tb_a_capture frames=%0d records=%0d good_eof=%0d errors=%0d",frames,records,eofs,errors);$finish;
    end
    initial begin #100000;$fatal(1,"timeout");end
endmodule
