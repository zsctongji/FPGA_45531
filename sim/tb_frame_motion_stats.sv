`timescale 1ns/1ps
module tb_frame_motion_stats;
    localparam W=5, H=3, N=W*H;
    reg clk=0; always #5 clk=~clk;
    reg rst_n=0, valid=0, sof=0, eof=0;
    reg [7:0] gray=0;
    wire ov, cv, motion, error, bbox;
    wire [31:0] count, total;
    wire [15:0] xmin,ymin,xmax,ymax;
    frame_motion_stats #(.WIDTH(W),.HEIGHT(H),.DIFF_THRESHOLD(24),.MIN_CHANGED(3)) dut(
        .clk(clk),.rst_n(rst_n),.in_valid(valid),.in_sof(sof),.in_eof(eof),.in_abort(1'b0),.in_gray(gray),
        .out_valid(ov),.comparison_valid(cv),.motion(motion),.frame_error(error),
        .changed_count(count),.absolute_difference_sum(total),.bbox_valid(bbox),
        .min_x(xmin),.min_y(ymin),.max_x(xmax),.max_y(ymax));
    integer image[0:N-1], previous[0:N-1];
    integer qc[0:255],qs[0:255],qx0[0:255],qy0[0:255],qx1[0:255],qy1[0:255];
    reg qvalid[0:255];
    integer head=0,tail=0,errors=0,seed=32'h12345678,checks=0;
    reg have_previous=0;
    always @(posedge clk) begin
        #1;
        if(rst_n && error) errors=errors+1;
        if(rst_n && ov) begin
            if(head>=tail) $fatal(1,"unexpected complete frame");
            if(cv !== qvalid[head] || count !== qc[head] || total !== qs[head])
                $fatal(1,"frame %0d stats got cv=%0d count=%0d sum=%0d expected %0d/%0d/%0d",head,cv,count,total,qvalid[head],qc[head],qs[head]);
            if(motion !== (qvalid[head] && qc[head]>=3) || bbox !== (qc[head]!=0)) $fatal(1,"motion/bbox flags");
            if({xmin,ymin,xmax,ymax} !== {16'(qx0[head]),16'(qy0[head]),16'(qx1[head]),16'(qy1[head])}) $fatal(1,"bbox mismatch frame %0d",head);
            head=head+1; checks=checks+1;
        end
    end
    task pixel(input integer value,input bit first,input bit last);
        @(negedge clk); valid=1; gray=value; sof=first; eof=last;
    endtask
    task blank(input integer cycles);
        @(negedge clk); valid=0; sof=0; eof=0;
        repeat(cycles-1) @(negedge clk);
    endtask
    task send_frame(input bit gaps);
        integer d,c,s,ax,ay,bx,by;
        begin
            c=0; s=0; ax=W; ay=H; bx=0; by=0;
            for(integer p=0;p<N;p=p+1) begin
                d=image[p]-previous[p]; if(d<0) d=-d;
                if(have_previous) begin
                    s=s+d;
                    if(d>=24) begin
                        c=c+1;
                        if(p%W<ax) ax=p%W; if(p/W<ay) ay=p/W;
                        if(p%W>bx) bx=p%W; if(p/W>by) by=p/W;
                    end
                end
            end
            qc[tail]=c; qs[tail]=s; qvalid[tail]=have_previous;
            qx0[tail]=c?ax:0; qy0[tail]=c?ay:0; qx1[tail]=c?bx:0; qy1[tail]=c?by:0;
            tail=tail+1;
            for(integer p=0;p<N;p=p+1) begin
                if(gaps && p%4==1) blank(2);
                pixel(image[p],p==0,p==N-1); previous[p]=image[p];
            end
            have_previous=1;
        end
    endtask
    initial begin
        for(integer p=0;p<N;p=p+1) begin image[p]=80; previous[p]=0; end
        repeat(3) @(negedge clk); rst_n=1;
        send_frame(0); send_frame(0); // Back-to-back first baseline and static frame.
        image[0]=104; image[6]=56; image[N-1]=255; send_frame(1);
        send_frame(0); // Identical content stops motion.
        image[N-1]=232; send_frame(0); // Difference 23 is below the inclusive threshold.
        image[N-1]=208; send_frame(0); // Difference 24 at the last pixel.
        for(integer f=0;f<64;f=f+1) begin
            for(integer p=0;p<N;p=p+1) image[p]=$random(seed)&255;
            send_frame(f%2);
        end
        blank(3);
        pixel(0,1,0); pixel(0,0,1); // Early EOF: never report a complete frame.
        blank(3); have_previous=0; send_frame(1); send_frame(0);
        blank(3);
        for(integer p=0;p<N;p=p+1) pixel(1,p==0,0); // Missing EOF.
        pixel(1,0,1); blank(3); have_previous=0; send_frame(0);
        blank(3); pixel(5,1,0); pixel(8,0,0); // SOF interrupts a partial frame.
        have_previous=0; send_frame(0); send_frame(0);
        blank(3); pixel(0,1,0);
        @(negedge clk); rst_n=0; valid=0;
        repeat(2) @(negedge clk); rst_n=1; have_previous=0;
        send_frame(1); send_frame(0); blank(5);
        if(head!=tail || errors<4 || checks!=77) $fatal(1,"coverage head=%0d tail=%0d errors=%0d checks=%0d",head,tail,errors,checks);
        $display("PASS tb_frame_motion_stats frames=%0d malformed=%0d random_frames=64 threshold_edges bbox gaps reset back_to_back",checks,errors);
        $finish;
    end
    initial begin #1000000; $fatal(1,"timeout"); end
endmodule
