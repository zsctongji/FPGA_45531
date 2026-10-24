`timescale 1ns/1ps
module tb_a_pipeline;
    reg clk=0;always #5 clk=~clk;
    reg rst=0,vs=0,de=0,take=0,rel=0,req=0;
    reg [15:0] addr=0;
    reg [7:0] gray=0;
    reg [31:0] now=0;
    wire sv,ss,se,sa,record,complete,ready,active,bank,rv,re;
    wire [7:0] sample,data;
    wire [31:0] fid,stamp,rid,rstamp,checksum,commits,drops,bad;
    integer sample_count=0,record_count=0,expected,checks=0,fd;
    video_a_capture cap(.clk(clk),.rst_n(rst),.in_vs(vs),.in_de(de),.in_gray(gray),.now_ms(now),
        .sample_valid(sv),.sample_sof(ss),.sample_eof(se),.sample_abort(sa),.sample_gray(sample),
        .sample_frame_id(fid),.sample_timestamp_ms(stamp),.record_valid(record),.record_complete(complete),
        .record_frame_id(),.record_timestamp_ms(),.record_width(),.record_height(),.source_frames(),.format_errors());
    ai_frame_mailbox mb(.clk(clk),.rst_n(rst),.sample_valid(sv),.sample_sof(ss),.sample_eof(se),.sample_abort(sa),.sample_gray(sample),
        .source_frame_id(fid),.source_timestamp_ms(stamp),.reader_take(take),.reader_release(rel),.read_req(req),.read_address(addr),
        .frame_ready(ready),.reader_active(active),.reader_buffer(bank),.reader_frame_id(rid),.reader_timestamp_ms(rstamp),.reader_checksum(checksum),
        .read_valid(rv),.read_error(re),.read_data(data),.committed_frames(commits),.dropped_frames(drops),.malformed_frames(bad));
    always @(posedge clk) begin
        #2;if(sv)sample_count++;if(record)begin if(!complete)$fatal(1,"full HD malformed");record_count++;end
    end
    task tick;begin @(posedge clk);#1;end endtask
    task boundary;begin @(negedge clk);de=0;vs=1;tick();@(negedge clk);vs=0;tick();tick();end endtask
    task video_frame(input integer f);
        begin
            for(integer y=0;y<1080;y++) begin
                for(integer x=0;x<1920;x++) begin
                    @(negedge clk);de=1;now=100+f*33;
                    // Strong spatial pattern exposes x/y/channel/stride errors.
                    gray=(x/20+3*(y/20)+f*17)%256;tick();checks++;
                end
                @(negedge clk);de=0;tick();tick();
            end
        end
    endtask
    task read_frame(input integer f);
        integer sumref;
        begin
            @(negedge clk);take=1;tick();@(negedge clk);take=0;tick();
            if(!active||rid!=f||rstamp!=100+f*33)$fatal(1,"source frame metadata");
            sumref=0;
            if(f==0)fd=$fopen("a_pipeline_frame0.gray","wb");
            for(integer i=0;i<9216;i++) begin
                @(negedge clk);req=1;addr=i;tick();
                expected=i<2016||i>=7200?0:((i-2016)%96+3*((i-2016)/96)+f*17)%256;
                if(!rv||re||data!=expected)$fatal(1,"full HD -> AI pixel %0d got=%0d want=%0d",i,data,expected);
                sumref+=expected;
                if(f==0)$fwrite(fd,"%c",data);
            end
            if(f==0)$fclose(fd);
            if(checksum!=sumref)$fatal(1,"full HD checksum");
            @(negedge clk);req=0;rel=1;tick();@(negedge clk);rel=0;tick();
        end
    endtask
    initial begin
        repeat(3)tick();@(negedge clk);rst=1;boundary();video_frame(0);boundary();video_frame(1);boundary();
        read_frame(0);read_frame(1);
        if(commits!=2||drops!=0||bad!=0||sample_count!=10368||record_count!=2)$fatal(1,"pipeline totals");
        $display("PASS tb_a_pipeline input_pixels=%0d samples=%0d cpu_reads=18432 committed=%0d",checks,sample_count,commits);$finish;
    end
    initial begin #50000000;$fatal(1,"timeout");end
endmodule
