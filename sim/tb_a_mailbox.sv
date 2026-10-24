`timescale 1ns/1ps
module tb_a_mailbox;
    reg clk=0;always #5 clk=~clk;
    reg rst=0,v=0,s=0,e=0,a=0,take=0,rel=0,req=0;
    reg [7:0] p=0;
    reg [31:0] id=0,ts=0;
    reg [15:0] addr=0;
    wire ready,active,bank,rv,re;
    wire [7:0] data;
    wire [31:0] rid,rts,sum,commits,drops,bad;
    integer checks=0;
    ai_frame_mailbox dut(.clk(clk),.rst_n(rst),.sample_valid(v),.sample_sof(s),.sample_eof(e),.sample_abort(a),.sample_gray(p),
        .source_frame_id(id),.source_timestamp_ms(ts),.reader_take(take),.reader_release(rel),.read_req(req),.read_address(addr),
        .frame_ready(ready),.reader_active(active),.reader_buffer(bank),.reader_frame_id(rid),.reader_timestamp_ms(rts),.reader_checksum(sum),
        .read_valid(rv),.read_error(re),.read_data(data),.committed_frames(commits),.dropped_frames(drops),.malformed_frames(bad));
    task tick;begin @(posedge clk);#1;checks++;end endtask
    task idle;begin @(negedge clk);v=0;s=0;e=0;a=0;tick();end endtask
    task frame(input integer f,input integer n,input integer abort_it);
        begin
            for(integer i=0;i<n;i++) begin
                @(negedge clk);id=f;ts=1000+f;v=1;s=i==0;e=i==n-1;p=(i+f)%256;tick();
            end
            idle();if(abort_it) begin @(negedge clk);a=1;tick();idle();end
        end
    endtask
    task acquire(input integer f);
        integer expected;
        begin
            @(negedge clk);take=1;tick();
            if(!active||rid!=f||rts!=1000+f)$fatal(1,"lease metadata");
            @(negedge clk);take=0;
            expected=0;for(integer k=0;k<5184;k++) expected+=(k+f)%256;
            if(sum!=expected)$fatal(1,"checksum got %0d want %0d",sum,expected);
        end
    endtask
    task read_image(input integer f);
        integer expected;
        begin
            for(integer i=0;i<9216;i++) begin
                @(negedge clk);req=1;addr=i;tick();
                expected=i<2016||i>=7200?0:(i-2016+f)%256;
                if(!rv||re||data!=expected)$fatal(1,"image byte %0d got %0d expected %0d",i,data,expected);
            end
            @(negedge clk);addr=9216;tick();if(!rv||!re)$fatal(1,"bounds");
            @(negedge clk);req=0;tick();if(rv)$fatal(1,"read valid pulse");
        end
    endtask
    task release_it;begin @(negedge clk);rel=1;tick();@(negedge clk);rel=0;tick();end endtask
    initial begin
        repeat(3)tick();@(negedge clk);rst=1;tick();
        frame(1,5184,0);acquire(1);
        frame(2,5184,0);frame(3,5184,0); // reader owns bank0; bank1 READY, drop new.
        if(commits!=2||drops!=1)$fatal(1,"busy policy");
        read_image(1);release_it();acquire(2);read_image(2);release_it();
        frame(4,20,0);if(ready||bad!=1)$fatal(1,"early EOF published");
        @(negedge clk);v=1;s=1;p=50;tick();
        @(negedge clk);v=0;s=0;a=1;tick();idle();if(bad!=2||ready)$fatal(1,"abort");
        frame(5,5184,0);frame(6,5184,0);acquire(5);release_it();acquire(6);release_it();
        // Missing EOF, excessive pixels, and new SOF recovery.
        for(integer i=0;i<5185;i++) begin @(negedge clk);v=1;s=i==0;e=0;p=9;tick();end
        idle();if(ready||bad!=3)$fatal(1,"missing EOF");
        @(negedge clk);v=1;s=1;e=0;p=1;tick();
        frame(7,5184,0);if(bad!=4)$fatal(1,"unexpected SOF");acquire(7);release_it();
        @(negedge clk);req=1;addr=2016;tick();if(!re)$fatal(1,"unowned read");
        $display("PASS tb_a_mailbox checks=%0d commits=%0d drops=%0d malformed=%0d",checks,commits,drops,bad);$finish;
    end
    initial begin #3000000;$fatal(1,"timeout");end
endmodule
